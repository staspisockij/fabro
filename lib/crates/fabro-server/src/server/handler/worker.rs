use std::collections::BTreeSet;
use std::sync::Arc;

use fabro_model::catalog::{CredentialRef, HeaderValueRef, LlmCatalogSettings};
use fabro_model::{Catalog, ProviderId};
use fabro_static::EnvVars;
use fabro_types::settings::InterpString;
use fabro_types::settings::run::{EnvironmentProvider, McpTransport, RunNamespace};
use fabro_types::settings::server::{GithubIntegrationSettings, GithubIntegrationStrategy};
use fabro_types::{
    ServerSettings, WorkerBootstrapGithubIntegration, WorkerBootstrapResponse,
    WorkerBootstrapSecret,
};
use fabro_vault::Vault;
use fabro_workflow::operations;
use serde::Serialize;
use toml::ser;

use super::super::{
    ApiError, AppState, IntoResponse, Json, RequireWorkerRunScoped, Response, Router, State,
    StatusCode, get, header,
};

pub(super) fn routes() -> Router<Arc<AppState>> {
    Router::new().route(
        "/runs/{id}/worker/bootstrap",
        get(retrieve_worker_bootstrap),
    )
}

async fn retrieve_worker_bootstrap(
    RequireWorkerRunScoped(id): RequireWorkerRunScoped,
    State(state): State<Arc<AppState>>,
) -> Response {
    let cached = match state.store_ref().get_cached_run(&id).await {
        Ok(Some(cached)) => cached,
        Ok(None) => return ApiError::not_found("Run not found.").into_response(),
        Err(err) => {
            return ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, err.to_string())
                .into_response();
        }
    };

    let server_settings = state.server_settings();
    let github = github_bootstrap_metadata(&server_settings.server.integrations.github);
    let config_toml = match worker_bootstrap_config_toml(state.llm_catalog_settings().as_ref()) {
        Ok(config_toml) => config_toml,
        Err(err) => {
            return ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, err.to_string())
                .into_response();
        }
    };

    let run_spec = &cached.projection.spec;
    let catalog = state.catalog();
    // Workers only receive vault-delivered secrets, so scope provider discovery
    // to the vault rather than the server's process environment.
    let configured = state.configured_llm_provider_ids().await;
    let reachable_providers = operations::reachable_provider_ids(
        catalog.as_ref(),
        &configured,
        &run_spec.settings.run,
        run_spec.graph(),
    );
    let vault = state.vault.read().await;
    let selector = WorkerBootstrapSecretSelector {
        repo_origin_url:     run_spec.repo_origin_url(),
        run_settings:        &run_spec.settings.run,
        catalog:             catalog.as_ref(),
        reachable_providers: &reachable_providers,
        server_settings:     server_settings.as_ref(),
        server_vault:        &vault,
    };
    let secrets = selector
        .required_secret_names()
        .into_iter()
        .filter_map(|name| secret_response_for_name(&vault, &name))
        .collect();

    (
        [(header::CACHE_CONTROL, "no-store")],
        Json(WorkerBootstrapResponse {
            config_toml,
            secrets,
            github,
        }),
    )
        .into_response()
}

#[derive(Serialize)]
struct WorkerBootstrapConfig<'a> {
    #[serde(rename = "_version")]
    version: u8,
    llm:     &'a LlmCatalogSettings,
}

fn worker_bootstrap_config_toml(llm: &LlmCatalogSettings) -> Result<String, ser::Error> {
    toml::to_string(&WorkerBootstrapConfig { version: 1, llm })
}

fn github_bootstrap_metadata(
    settings: &GithubIntegrationSettings,
) -> WorkerBootstrapGithubIntegration {
    WorkerBootstrapGithubIntegration {
        enabled:  settings.enabled,
        strategy: settings.strategy,
        app_id:   settings.app_id.as_ref().map(InterpString::as_source),
        slug:     settings.slug.as_ref().map(InterpString::as_source),
    }
}

fn secret_response_for_name(vault: &Vault, name: &str) -> Option<WorkerBootstrapSecret> {
    let entry = vault.get_entry(name)?;
    Some(WorkerBootstrapSecret {
        name:        name.to_string(),
        value:       entry.value.clone(),
        secret_type: entry.secret_type,
        description: entry.description.clone(),
    })
}

struct WorkerBootstrapSecretSelector<'a> {
    repo_origin_url:     Option<&'a str>,
    run_settings:        &'a RunNamespace,
    catalog:             &'a Catalog,
    reachable_providers: &'a BTreeSet<ProviderId>,
    server_settings:     &'a ServerSettings,
    server_vault:        &'a Vault,
}

impl WorkerBootstrapSecretSelector<'_> {
    fn required_secret_names(&self) -> BTreeSet<String> {
        let mut names = BTreeSet::new();
        self.collect_llm_provider_secrets(&mut names);
        self.collect_mcp_header_secrets(&mut names);
        self.collect_github_secrets(&mut names);
        self.collect_sandbox_provider_secrets(&mut names);
        names.retain(|name| !fabro_static::is_bootstrap_secret(name));
        names
    }

    fn collect_llm_provider_secrets(&self, names: &mut BTreeSet<String>) {
        for provider_id in self.reachable_providers {
            let Some(provider) = self.catalog.provider(provider_id) else {
                continue;
            };
            if let Some(auth) = &provider.auth {
                for credential in &auth.credentials {
                    if let CredentialRef::Vault(name) = credential {
                        names.insert(name.clone());
                    }
                }
            }
            for header in provider.extra_headers.values() {
                if let HeaderValueRef::Vault(name) = header {
                    names.insert(name.clone());
                }
            }
        }
    }

    fn collect_mcp_header_secrets(&self, names: &mut BTreeSet<String>) {
        for mcp in self.run_settings.agent.mcps.values() {
            let McpTransport::Http { headers, .. } = &mcp.transport else {
                continue;
            };
            for value in headers.values() {
                let interpolated = InterpString::parse(value);
                for name in interpolated.env_var_names() {
                    if self.server_vault.get_entry(name).is_some() {
                        names.insert(name.to_string());
                    }
                }
            }
        }
    }

    fn collect_github_secrets(&self, names: &mut BTreeSet<String>) {
        if !self.github_credentials_needed() {
            return;
        }
        match self.server_settings.server.integrations.github.strategy {
            GithubIntegrationStrategy::Token => {
                names.insert(EnvVars::GITHUB_TOKEN.to_string());
            }
            GithubIntegrationStrategy::App => {
                names.insert(EnvVars::GITHUB_APP_PRIVATE_KEY.to_string());
            }
        }
    }

    fn github_credentials_needed(&self) -> bool {
        if self.run_settings.integrations.github.is_token_requested() {
            return true;
        }

        self.run_settings
            .github_credentials_useful_for_clone(self.repo_origin_url)
            || self
                .run_settings
                .github_credentials_useful_for_pull_request()
    }

    fn collect_sandbox_provider_secrets(&self, names: &mut BTreeSet<String>) {
        if self.run_settings.environment.provider == EnvironmentProvider::Daytona {
            names.insert(EnvVars::DAYTONA_API_KEY.to_string());
        }
    }
}

#[cfg(test)]
mod tests {
    use fabro_types::SecretType;
    use fabro_types::settings::run::RunNamespace;
    use ulid::Ulid;

    use super::*;

    #[test]
    fn worker_bootstrap_selector_includes_daytona_secret_only_for_daytona_runs() {
        let vault_path =
            std::env::temp_dir().join(format!("fabro-worker-bootstrap-{}.json", Ulid::new()));
        let mut vault = Vault::load(vault_path).expect("test vault should load");
        vault
            .set(
                EnvVars::DAYTONA_API_KEY,
                "dtn-test",
                SecretType::Token,
                None,
            )
            .expect("test vault entry should persist");
        let catalog = Catalog::from_builtin().expect("test catalog should build");
        let reachable_providers = BTreeSet::new();
        let server_settings = fabro_config::ServerSettingsBuilder::from_toml(
            r#"
_version = 1

[server.auth]
methods = ["dev-token"]
"#,
        )
        .expect("server settings should resolve");

        let local_settings = RunNamespace::default();
        let local_selector = WorkerBootstrapSecretSelector {
            repo_origin_url:     None,
            run_settings:        &local_settings,
            catalog:             &catalog,
            reachable_providers: &reachable_providers,
            server_settings:     &server_settings,
            server_vault:        &vault,
        };
        assert!(
            !local_selector
                .required_secret_names()
                .contains(EnvVars::DAYTONA_API_KEY)
        );

        let mut daytona_settings = RunNamespace::default();
        daytona_settings.environment.provider = EnvironmentProvider::Daytona;
        let daytona_selector = WorkerBootstrapSecretSelector {
            repo_origin_url:     None,
            run_settings:        &daytona_settings,
            catalog:             &catalog,
            reachable_providers: &reachable_providers,
            server_settings:     &server_settings,
            server_vault:        &vault,
        };
        assert!(
            daytona_selector
                .required_secret_names()
                .contains(EnvVars::DAYTONA_API_KEY)
        );
    }
}
