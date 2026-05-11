#[allow(
    clippy::absolute_paths,
    clippy::all,
    clippy::derivable_impls,
    clippy::disallowed_methods,
    clippy::disallowed_types,
    clippy::needless_lifetimes,
    clippy::unwrap_used,
    unreachable_pub,
    unused_imports,
    reason = "Generated OpenAPI client code intentionally preserves codegen output."
)]
mod generated {
    include!(concat!(env!("OUT_DIR"), "/codegen.rs"));
}
pub mod types {
    use std::collections::HashMap;

    pub use fabro_model::{Model, ModelCosts, ModelFeatures, ModelLimits, ModelTestMode, Provider};
    pub use fabro_types::settings::server::{
        GithubIntegrationSettings, GithubIntegrationStrategy, IntegrationWebhooksSettings,
        IpAllowEntry, LogDestination, ObjectStoreSettings, ServerApiSettings,
        ServerArtifactsSettings, ServerAuthGithubSettings, ServerAuthMethod, ServerAuthSettings,
        ServerIntegrationsSettings, ServerIpAllowlistOverrideSettings, ServerIpAllowlistSettings,
        ServerListenSettings, ServerLoggingSettings, ServerSchedulerSettings,
        ServerSlateDbSettings, ServerStorageSettings, ServerWebSettings, SlackIntegrationSettings,
        WebhookStrategy,
    };
    pub use fabro_types::settings::{FeaturesNamespace, ServerNamespace};
    pub use fabro_types::status::{
        BlockedReason, FailureReason, RunControlAction, RunStatus, SuccessReason,
    };
    pub use fabro_types::{
        AuthMethod, BilledTokenCounts, CommandTermination, DiffStats, DiffSummary, DirtyStatus,
        EventEnvelope, GitContext, IdpIdentity, InterviewOption, InterviewQuestionRecord,
        PendingInterviewRecord, PreRunPushOutcome, Principal, PullRequest, PullRequestDetails,
        QuestionType, RepositoryRef, Run, RunClientProvenance, RunEvent, RunProjection,
        RunProvenance, RunSandbox, RunSandboxRuntime, RunServerProvenance, SandboxDetails,
        SandboxProvider, SandboxResources, SandboxService, SandboxServiceListResponse,
        SandboxState, SandboxTimestamps, SecretMetadata, SecretType, ServerSettings,
        StageCompletion, StageHandler, StageOutcome, StageProjection, StageState, SystemActorKind,
        UserPrincipal, WorkflowSettings,
    };
    use serde::{Deserialize, Serialize};

    pub use crate::generated::types::*;

    pub type RunSummary = fabro_types::Run;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct RunStatusResponse {
        pub id:              String,
        pub title:           String,
        pub status:          fabro_types::RunStatus,
        pub error:           Option<RunError>,
        pub queue_position:  Option<u32>,
        pub pending_control: Option<fabro_types::RunControlAction>,
        pub created_at:      chrono::DateTime<chrono::Utc>,
        pub web_url:         Option<String>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct RunPullRequest {
        pub number:    i64,
        pub html_url:  Option<String>,
        pub additions: Option<i64>,
        pub deletions: Option<i64>,
        pub comments:  Option<i64>,
        pub checks:    Vec<CheckRun>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct RunListItem {
        pub run_id:           String,
        pub workflow_name:    Option<String>,
        pub workflow_slug:    Option<String>,
        pub goal:             String,
        pub repository:       fabro_types::RepositoryRef,
        pub title:            String,
        pub status:           fabro_types::RunStatus,
        pub labels:           HashMap<String, String>,
        pub source_directory: Option<String>,
        pub repo_origin_url:  Option<String>,
        pub start_time:       Option<chrono::DateTime<chrono::Utc>>,
        pub pending_control:  Option<fabro_types::RunControlAction>,
        pub duration_ms:      Option<i64>,
        pub elapsed_secs:     Option<f64>,
        pub total_usd_micros: Option<i64>,
        pub column:           BoardColumn,
        pub pull_request:     Option<RunPullRequest>,
        pub sandbox:          Option<fabro_types::RunSandbox>,
        pub question:         Option<RunQuestion>,
        pub created_at:       chrono::DateTime<chrono::Utc>,
        pub last_event_at:    Option<chrono::DateTime<chrono::Utc>>,
    }
}
pub use generated::Client as ApiClient;
