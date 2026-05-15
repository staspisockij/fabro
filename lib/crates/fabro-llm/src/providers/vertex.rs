use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use fabro_model::Catalog;
use fabro_static::EnvVars;
#[cfg(test)]
use fabro_util::error::collect_chain;
use google_cloud_auth::credentials::{AccessTokenCredentials, Builder as GoogleCredentialsBuilder};

use crate::error::{Error, error_from_grpc_status, error_from_status_code};
use crate::provider::{ProviderAdapter, StreamEventStream, validate_tool_choice};
use crate::providers::anthropic;
use crate::providers::common::{parse_error_body, parse_retry_after};
use crate::providers::http_api::HttpApi;
use crate::types::{AdapterTimeout, Request, Response};

const CLOUD_PLATFORM_SCOPE: &str = "https://www.googleapis.com/auth/cloud-platform";

#[async_trait]
pub trait VertexTokenProvider: std::fmt::Debug + Send + Sync {
    async fn access_token(&self) -> Result<String, Error>;
}

#[derive(Debug, Default)]
pub struct GoogleCloudAuthTokenProvider {
    credentials: Mutex<Option<AccessTokenCredentials>>,
}

impl GoogleCloudAuthTokenProvider {
    fn credentials(&self) -> Result<AccessTokenCredentials, Error> {
        let mut guard = self
            .credentials
            .lock()
            .map_err(|err| Error::Configuration {
                message: format!("failed to lock Google ADC token provider: {err}"),
                source:  None,
            })?;
        if let Some(credentials) = guard.as_ref() {
            return Ok(credentials.clone());
        }

        let credentials = GoogleCredentialsBuilder::default()
            .with_scopes([CLOUD_PLATFORM_SCOPE])
            .build_access_token_credentials()
            .map_err(|err| Error::configuration_error("failed to initialize Google ADC", err))?;
        *guard = Some(credentials.clone());
        Ok(credentials)
    }
}

#[async_trait]
impl VertexTokenProvider for GoogleCloudAuthTokenProvider {
    async fn access_token(&self) -> Result<String, Error> {
        let credentials = self.credentials()?;
        credentials
            .access_token()
            .await
            .map(|token| token.token)
            .map_err(|err| {
                Error::configuration_error("failed to fetch Google ADC access token", err)
            })
    }
}

pub struct Adapter {
    http:           HttpApi,
    provider_name:  String,
    catalog:        Option<Arc<Catalog>>,
    token_provider: Arc<dyn VertexTokenProvider>,
    project_id:     Option<String>,
    region:         Option<String>,
}

impl Adapter {
    #[must_use]
    pub fn new() -> Self {
        Self {
            http:           HttpApi::new_optional(None, default_base_url_for_region("global")),
            provider_name:  "vertex".to_string(),
            catalog:        None,
            token_provider: Arc::new(GoogleCloudAuthTokenProvider::default()),
            project_id:     None,
            region:         None,
        }
    }

    #[must_use]
    pub fn with_name(mut self, name: impl Into<String>) -> Self {
        self.provider_name = name.into();
        self
    }

    #[must_use]
    pub fn with_base_url(mut self, base_url: impl Into<String>) -> Self {
        self.http.base_url = base_url.into();
        self
    }

    #[must_use]
    pub fn with_default_headers(self, headers: std::collections::HashMap<String, String>) -> Self {
        Self {
            http: self.http.with_default_headers(headers),
            ..self
        }
    }

    #[must_use]
    pub fn with_catalog(mut self, catalog: Arc<Catalog>) -> Self {
        self.catalog = Some(catalog);
        self
    }

    #[must_use]
    pub fn with_timeout(mut self, timeout: AdapterTimeout) -> Self {
        self.http = self.http.with_timeout(timeout);
        self
    }

    #[must_use]
    pub fn with_token_provider(mut self, token_provider: Arc<dyn VertexTokenProvider>) -> Self {
        self.token_provider = token_provider;
        self
    }

    #[must_use]
    pub fn with_project_id(mut self, project_id: impl Into<String>) -> Self {
        self.project_id = Some(project_id.into());
        self
    }

    #[must_use]
    pub fn with_region(mut self, region: impl Into<String>) -> Self {
        self.region = Some(region.into());
        self
    }

    fn region(&self) -> String {
        self.region
            .clone()
            .or_else(env_region)
            .unwrap_or_else(|| "global".to_string())
    }

    fn base_url(&self) -> String {
        if self.http.base_url.is_empty() {
            default_base_url_for_region(&self.region())
        } else {
            self.http.base_url.clone()
        }
    }

    fn project_id(&self) -> Result<String, Error> {
        self.project_id
            .clone()
            .or_else(env_project_id)
            .or_else(adc_project_id)
            .ok_or_else(|| Error::Configuration {
                message: "Vertex provider requires a Google Cloud project ID; set ANTHROPIC_VERTEX_PROJECT_ID or GOOGLE_CLOUD_PROJECT".to_string(),
                source: None,
            })
    }

    fn endpoint_url(&self, model: &str, stream: bool) -> Result<String, Error> {
        let method = if stream {
            "streamRawPredict"
        } else {
            "rawPredict"
        };
        let base_url = self.base_url();
        let project = self.project_id()?;
        let region = self.region();
        Ok(format!(
            "{}/projects/{}/locations/{}/publishers/anthropic/models/{}:{}",
            base_url.trim_end_matches('/'),
            project,
            region,
            model,
            method,
        ))
    }

    async fn request_builder(
        &self,
        request: &Request,
        stream: bool,
    ) -> Result<fabro_http::RequestBuilder, Error> {
        let (model, body) =
            anthropic::build_vertex_request_body(self.catalog.as_deref(), request, stream).await;
        let url = self.endpoint_url(&model, stream)?;
        let token = self.token_provider.access_token().await?;
        let mut builder = self.http.client.post(url);
        for (key, value) in &self.http.default_headers {
            builder = builder.header(key, value);
        }
        builder = builder.bearer_auth(token).json(&body);
        if let Some(timeout) = self.http.request_timeout {
            builder = builder.timeout(timeout);
        }
        Ok(builder)
    }
}

impl Default for Adapter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ProviderAdapter for Adapter {
    fn name(&self) -> &str {
        &self.provider_name
    }

    async fn initialize(&self) -> Result<(), Error> {
        self.project_id()?;
        self.token_provider.access_token().await.map(|_| ())
    }

    async fn complete(&self, request: &Request) -> Result<Response, Error> {
        if let Some(tc) = &request.tool_choice {
            validate_tool_choice(self, tc)?;
        }
        let request_builder = self.request_builder(request, false).await?;
        let (body, headers) =
            send_and_read_response_with_google_errors(request_builder, &self.provider_name).await?;
        anthropic::parse_response_body(&body, &headers, request, &self.provider_name)
    }

    async fn stream(&self, request: &Request) -> Result<StreamEventStream, Error> {
        if let Some(tc) = &request.tool_choice {
            validate_tool_choice(self, tc)?;
        }
        let response = self
            .request_builder(request, true)
            .await?
            .send()
            .await
            .map_err(|err| Error::network(err.to_string(), err))?;
        let status = response.status();
        if !status.is_success() {
            return Err(google_error_from_response(response, &self.provider_name).await);
        }
        Ok(anthropic::stream_events_from_response(
            response,
            request,
            self.provider_name.clone(),
            self.http.stream_read_timeout,
        ))
    }

    fn supports_tool_choice(&self, mode: &str) -> bool {
        matches!(mode, "auto" | "none" | "required" | "named")
    }
}

async fn send_and_read_response_with_google_errors(
    request: fabro_http::RequestBuilder,
    provider: &str,
) -> Result<(String, fabro_http::HeaderMap), Error> {
    let response = request
        .send()
        .await
        .map_err(|err| Error::network(err.to_string(), err))?;
    let status = response.status();
    if !status.is_success() {
        return Err(google_error_from_response(response, provider).await);
    }
    let headers = response.headers().clone();
    let body = response
        .text()
        .await
        .map_err(|err| Error::network(err.to_string(), err))?;
    Ok((body, headers))
}

async fn google_error_from_response(response: fabro_http::Response, provider: &str) -> Error {
    let status = response.status();
    let retry_after = parse_retry_after(response.headers());
    let body = match response.text().await {
        Ok(body) => body,
        Err(err) => return Error::network(err.to_string(), err),
    };
    let (message, code, raw) = parse_error_body(&body, "status");
    if let Some(code) = code.as_deref() {
        return error_from_grpc_status(
            code,
            google_error_message(code, &message),
            provider.to_string(),
            Some(code.to_string()),
            raw,
            retry_after,
        );
    }
    error_from_status_code(
        status.as_u16(),
        message,
        provider.to_string(),
        None,
        raw,
        retry_after,
    )
}

fn google_error_message(code: &str, message: &str) -> String {
    match code {
        "PERMISSION_DENIED" => format!(
            "{message}; verify Vertex AI permissions, publisher model access, and Marketplace enablement"
        ),
        "NOT_FOUND" => format!("{message}; verify the Vertex model ID and location"),
        "RESOURCE_EXHAUSTED" => {
            format!("{message}; Vertex quota or regional capacity was exhausted")
        }
        "INVALID_ARGUMENT" => format!("{message}; verify the Vertex region and request body"),
        _ => message.to_string(),
    }
}

fn default_base_url_for_region(region: &str) -> String {
    match region {
        "global" => "https://aiplatform.googleapis.com/v1".to_string(),
        "us" => "https://aiplatform.us.rep.googleapis.com/v1".to_string(),
        "eu" => "https://aiplatform.eu.rep.googleapis.com/v1".to_string(),
        other => format!("https://{other}-aiplatform.googleapis.com/v1"),
    }
}

#[expect(
    clippy::disallowed_methods,
    reason = "Vertex adapter resolves provider configuration from documented process env vars."
)]
fn env_region() -> Option<String> {
    std::env::var(EnvVars::CLOUD_ML_REGION).ok()
}

#[expect(
    clippy::disallowed_methods,
    reason = "Vertex adapter resolves provider configuration from documented process env vars."
)]
fn env_project_id() -> Option<String> {
    [
        EnvVars::ANTHROPIC_VERTEX_PROJECT_ID,
        EnvVars::GOOGLE_CLOUD_PROJECT,
        EnvVars::GCLOUD_PROJECT,
        EnvVars::GCP_PROJECT,
    ]
    .into_iter()
    .find_map(|name| std::env::var(name).ok())
}

#[expect(
    clippy::disallowed_methods,
    reason = "ADC project fallback reads only standard Google ADC locations."
)]
fn adc_project_id() -> Option<String> {
    let path = std::env::var(EnvVars::GOOGLE_APPLICATION_CREDENTIALS)
        .ok()
        .map(std::path::PathBuf::from)
        .or_else(well_known_adc_path)?;
    let contents = std::fs::read_to_string(path).ok()?;
    let json: serde_json::Value = serde_json::from_str(&contents).ok()?;
    json.get("project_id")
        .or_else(|| json.get("quota_project_id"))
        .and_then(serde_json::Value::as_str)
        .map(str::to_string)
}

#[expect(
    clippy::disallowed_methods,
    reason = "ADC project fallback reads only standard Google ADC locations."
)]
fn well_known_adc_path() -> Option<std::path::PathBuf> {
    if cfg!(windows) {
        std::env::var("APPDATA")
            .ok()
            .map(std::path::PathBuf::from)
            .map(|path| path.join("gcloud/application_default_credentials.json"))
    } else {
        std::env::var(EnvVars::HOME)
            .ok()
            .map(std::path::PathBuf::from)
            .map(|path| path.join(".config/gcloud/application_default_credentials.json"))
    }
}

#[cfg(test)]
fn configuration_message_with_chain(err: &Error) -> String {
    match err {
        Error::Configuration { source, message } => source.as_ref().map_or_else(
            || message.clone(),
            |source| {
                collect_chain(source.as_ref()).into_iter().fold(
                    message.clone(),
                    |mut message, cause| {
                        message.push_str(": ");
                        message.push_str(&cause);
                        message
                    },
                )
            },
        ),
        _ => err.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use futures::StreamExt;
    use http::StatusCode;
    use httpmock::Method::POST;
    use httpmock::MockServer;

    use super::*;
    use crate::error::ProviderErrorKind;
    use crate::types::{ContentPart, Message, Role, StreamEvent};

    #[derive(Debug)]
    struct FakeTokenProvider {
        token: Result<String, Error>,
    }

    #[async_trait]
    impl VertexTokenProvider for FakeTokenProvider {
        async fn access_token(&self) -> Result<String, Error> {
            self.token.clone()
        }
    }

    fn fake_token_provider(token: &str) -> Arc<dyn VertexTokenProvider> {
        Arc::new(FakeTokenProvider {
            token: Ok(token.to_string()),
        })
    }

    fn test_request(model: &str) -> Request {
        Request {
            model:            model.to_string(),
            messages:         vec![Message {
                role:         Role::User,
                content:      vec![ContentPart::text("hello")],
                name:         None,
                tool_call_id: None,
            }],
            provider:         None,
            tools:            None,
            tool_choice:      None,
            response_format:  None,
            temperature:      None,
            top_p:            None,
            max_tokens:       Some(128),
            stop_sequences:   None,
            reasoning_effort: None,
            speed:            None,
            metadata:         None,
            provider_options: None,
        }
    }

    fn adapter(server: &MockServer) -> Adapter {
        Adapter::new()
            .with_base_url(server.url(""))
            .with_project_id("test-project")
            .with_region("us-central1")
            .with_token_provider(fake_token_provider("test-token"))
    }

    #[tokio::test]
    async fn complete_posts_raw_predict_with_vertex_body_and_bearer_token() {
        let server = MockServer::start_async().await;
        let mock = server
            .mock_async(|when, then| {
                when.method(POST)
                    .path("/projects/test-project/locations/us-central1/publishers/anthropic/models/claude-sonnet-4-6:rawPredict")
                    .header("authorization", "Bearer test-token")
                    .is_true(|request| {
                        let body: serde_json::Value =
                            serde_json::from_slice(request.body_ref()).unwrap();
                        body["anthropic_version"] == "vertex-2023-10-16"
                            && !body.as_object().unwrap().contains_key("model")
                    });
                then.status(StatusCode::OK.as_u16()).json_body(serde_json::json!({
                    "id": "msg_1",
                    "model": "claude-sonnet-4-6",
                    "content": [{"type": "text", "text": "hi"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 2, "output_tokens": 3}
                }));
            })
            .await;
        let response = adapter(&server)
            .complete(&test_request("claude-sonnet-4-6"))
            .await
            .unwrap();

        assert_eq!(response.provider, "vertex");
        assert_eq!(response.model, "claude-sonnet-4-6");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn stream_posts_stream_raw_predict_and_reuses_anthropic_sse_parser() {
        let server = MockServer::start_async().await;
        server
            .mock_async(|when, then| {
                when.method(POST)
                    .path("/projects/test-project/locations/us-central1/publishers/anthropic/models/claude-sonnet-4-6:streamRawPredict")
                    .header("authorization", "Bearer test-token");
                then.status(StatusCode::OK.as_u16())
                    .header("content-type", "text/event-stream")
                    .body(
                        "event: message_start\n\
                         data: {\"message\":{\"id\":\"msg_1\",\"model\":\"claude-sonnet-4-6\",\"usage\":{\"input_tokens\":2}}}\n\n\
                         event: content_block_start\n\
                         data: {\"index\":0,\"content_block\":{\"type\":\"text\",\"text\":\"\"}}\n\n\
                         event: content_block_delta\n\
                         data: {\"index\":0,\"delta\":{\"type\":\"text_delta\",\"text\":\"hi\"}}\n\n\
                         event: content_block_stop\n\
                         data: {\"index\":0}\n\n\
                         event: message_delta\n\
                         data: {\"delta\":{\"stop_reason\":\"end_turn\"},\"usage\":{\"output_tokens\":3}}\n\n\
                         event: message_stop\n\
                         data: {}\n\n",
                    );
            })
            .await;

        let mut stream = adapter(&server)
            .stream(&test_request("claude-sonnet-4-6"))
            .await
            .unwrap();
        let mut provider = None;
        while let Some(event) = stream.next().await {
            if let StreamEvent::Finish { response, .. } = event.unwrap() {
                provider = Some(response.provider);
            }
        }

        assert_eq!(provider.as_deref(), Some("vertex"));
    }

    #[tokio::test]
    async fn google_errors_preserve_status_code_and_google_status() {
        let server = MockServer::start_async().await;
        server
            .mock_async(|when, then| {
                when.method(POST);
                then.status(StatusCode::FORBIDDEN.as_u16())
                    .json_body(serde_json::json!({
                        "error": {
                            "code": 403,
                            "message": "model is not enabled",
                            "status": "PERMISSION_DENIED"
                        }
                    }));
            })
            .await;

        let err = adapter(&server)
            .complete(&test_request("claude-sonnet-4-6"))
            .await
            .unwrap_err();

        assert_eq!(err.provider_kind(), Some(ProviderErrorKind::AccessDenied));
        assert_eq!(err.status_code(), None);
        assert!(err.to_string().contains("Marketplace enablement"));
    }

    #[tokio::test]
    async fn adc_failure_is_reported_as_configuration_error() {
        let adapter = Adapter::new()
            .with_project_id("test-project")
            .with_token_provider(Arc::new(FakeTokenProvider {
                token: Err(Error::Configuration {
                    message: "failed to fetch Google ADC access token".to_string(),
                    source:  None,
                }),
            }));

        let err = adapter.initialize().await.unwrap_err();

        assert!(configuration_message_with_chain(&err).contains("Google ADC"));
    }

    #[test]
    fn default_base_url_matches_vertex_region_defaults() {
        assert_eq!(
            default_base_url_for_region("global"),
            "https://aiplatform.googleapis.com/v1"
        );
        assert_eq!(
            default_base_url_for_region("us"),
            "https://aiplatform.us.rep.googleapis.com/v1"
        );
        assert_eq!(
            default_base_url_for_region("eu"),
            "https://aiplatform.eu.rep.googleapis.com/v1"
        );
        assert_eq!(
            default_base_url_for_region("us-central1"),
            "https://us-central1-aiplatform.googleapis.com/v1"
        );
    }
}
