use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::de::Error;
use serde::{Deserialize, Deserializer, Serialize};

use crate::{
    DiffSummary, InterviewQuestionRecord, Principal, PullRequest, RepositoryProvider,
    RepositoryRef, RunControlAction, RunId, RunSandbox, RunStatus, SuccessReason,
};

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Run {
    pub id:               RunId,
    pub title:            String,
    pub goal:             String,
    pub workflow:         WorkflowRef,
    #[serde(default)]
    pub automation:       Option<AutomationRef>,
    #[serde(default)]
    pub repository:       Option<RepositoryRef>,
    #[serde(default)]
    pub created_by:       Option<Principal>,
    pub origin:           RunOrigin,
    pub labels:           HashMap<String, String>,
    pub lifecycle:        RunLifecycle,
    #[serde(default)]
    pub sandbox:          Option<RunSandbox>,
    pub models:           Vec<RunModel>,
    #[serde(default)]
    pub source_directory: Option<String>,
    pub timestamps:       RunTimestamps,
    #[serde(default)]
    pub billing:          Option<RunBillingSummary>,
    #[serde(default)]
    pub diff:             Option<DiffSummary>,
    #[serde(default)]
    pub pull_request:     Option<PullRequest>,
    #[serde(default)]
    pub current_question: Option<InterviewQuestionRecord>,
    #[serde(default)]
    pub superseded_by:    Option<RunId>,
    pub links:            RunLinks,
    #[serde(skip, default = "RunId::new")]
    pub run_id:           RunId,
    #[serde(skip)]
    pub workflow_name:    Option<String>,
    #[serde(skip)]
    pub workflow_slug:    Option<String>,
    #[serde(skip)]
    pub repo_origin_url:  Option<String>,
    #[serde(skip)]
    pub start_time:       Option<DateTime<Utc>>,
    #[serde(skip, default = "Utc::now")]
    pub created_at:       DateTime<Utc>,
    #[serde(skip)]
    pub last_event_at:    Option<DateTime<Utc>>,
    #[serde(skip, default = "default_run_status")]
    pub status:           RunStatus,
    #[serde(skip)]
    pub pending_control:  Option<RunControlAction>,
    #[serde(skip)]
    pub duration_ms:      Option<u64>,
    #[serde(skip)]
    pub elapsed_secs:     Option<f64>,
    #[serde(skip)]
    pub total_usd_micros: Option<i64>,
    #[serde(skip)]
    pub diff_summary:     Option<DiffSummary>,
}

#[derive(Debug, Deserialize)]
struct RunWire {
    #[serde(default)]
    id:               Option<RunId>,
    #[serde(default)]
    run_id:           Option<RunId>,
    #[serde(default)]
    title:            Option<String>,
    #[serde(default)]
    goal:             Option<String>,
    #[serde(default)]
    workflow:         Option<WorkflowRef>,
    #[serde(default)]
    workflow_name:    Option<String>,
    #[serde(default)]
    workflow_slug:    Option<String>,
    #[serde(default)]
    automation:       Option<AutomationRef>,
    #[serde(default)]
    repository:       Option<RepositoryRefWire>,
    #[serde(default)]
    repo_origin_url:  Option<String>,
    #[serde(default)]
    created_by:       Option<Principal>,
    #[serde(default)]
    origin:           Option<RunOrigin>,
    #[serde(default)]
    labels:           HashMap<String, String>,
    #[serde(default)]
    lifecycle:        Option<RunLifecycle>,
    #[serde(default)]
    status:           Option<serde_json::Value>,
    #[serde(default)]
    pending_control:  Option<RunControlAction>,
    #[serde(default)]
    archived_at:      Option<DateTime<Utc>>,
    #[serde(default)]
    sandbox:          Option<RunSandbox>,
    #[serde(default)]
    models:           Vec<RunModel>,
    #[serde(default)]
    source_directory: Option<String>,
    #[serde(default)]
    timestamps:       Option<RunTimestamps>,
    #[serde(default)]
    start_time:       Option<DateTime<Utc>>,
    #[serde(default)]
    created_at:       Option<DateTime<Utc>>,
    #[serde(default)]
    last_event_at:    Option<DateTime<Utc>>,
    #[serde(default)]
    duration_ms:      Option<u64>,
    #[serde(default)]
    elapsed_secs:     Option<f64>,
    #[serde(default)]
    billing:          Option<RunBillingSummary>,
    #[serde(default)]
    total_usd_micros: Option<i64>,
    #[serde(default)]
    diff:             Option<DiffSummary>,
    #[serde(default)]
    diff_summary:     Option<DiffSummary>,
    #[serde(default)]
    pull_request:     Option<PullRequest>,
    #[serde(default)]
    current_question: Option<InterviewQuestionRecord>,
    #[serde(default)]
    superseded_by:    Option<RunId>,
    #[serde(default)]
    links:            Option<RunLinks>,
}

#[derive(Debug, Deserialize)]
struct RepositoryRefWire {
    name:       String,
    #[serde(default)]
    origin_url: Option<String>,
    #[serde(default)]
    provider:   Option<RepositoryProvider>,
}

impl From<RepositoryRefWire> for RepositoryRef {
    fn from(value: RepositoryRefWire) -> Self {
        Self {
            name:       value.name,
            provider:   value
                .provider
                .unwrap_or_else(|| repository_provider(value.origin_url.as_deref())),
            origin_url: value.origin_url,
        }
    }
}

fn legacy_status(
    value: Option<serde_json::Value>,
) -> Result<(Option<RunStatus>, bool), serde_json::Error> {
    let Some(value) = value else {
        return Ok((None, false));
    };
    if value.get("kind").and_then(serde_json::Value::as_str) == Some("archived") {
        let status = match value.get("prior") {
            Some(prior) => serde_json::from_value(prior.clone())?,
            None => RunStatus::Succeeded {
                reason: SuccessReason::Completed,
            },
        };
        return Ok((Some(status), true));
    }
    serde_json::from_value(value).map(|status| (Some(status), false))
}

impl<'de> Deserialize<'de> for Run {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let wire = RunWire::deserialize(deserializer)?;
        let id = wire
            .id
            .or(wire.run_id)
            .ok_or_else(|| D::Error::missing_field("id"))?;
        let goal = wire.goal.unwrap_or_else(|| {
            wire.title
                .clone()
                .unwrap_or_else(|| "Untitled run".to_string())
        });
        let workflow = wire.workflow.unwrap_or_else(|| WorkflowRef {
            slug: wire.workflow_slug,
            name: wire.workflow_name.unwrap_or_else(|| "unnamed".to_string()),
        });
        let repository = wire.repository.map(Into::into).or_else(|| {
            Some(repository_ref(
                wire.repo_origin_url.as_deref(),
                wire.source_directory.as_deref(),
            ))
        });
        let repo_origin_url = repository
            .as_ref()
            .and_then(|repository: &RepositoryRef| repository.origin_url.clone())
            .or(wire.repo_origin_url);
        let (legacy_status, legacy_archived) =
            legacy_status(wire.status).map_err(D::Error::custom)?;
        let lifecycle = wire.lifecycle.unwrap_or_else(|| RunLifecycle {
            status:          legacy_status.unwrap_or_else(default_run_status),
            pending_control: wire.pending_control,
            queue_position:  None,
            error:           None,
            archived:        wire.archived_at.is_some() || legacy_archived,
            archived_at:     wire.archived_at,
        });
        let timestamps = wire.timestamps.unwrap_or_else(|| {
            let created_at = wire.created_at.unwrap_or_else(|| id.created_at());
            RunTimestamps {
                created_at,
                started_at: wire.start_time,
                last_event_at: wire.last_event_at,
                completed_at: None,
                duration_ms: wire.duration_ms,
                elapsed_secs: wire.elapsed_secs.or_else(|| elapsed_secs(wire.duration_ms)),
            }
        });
        let total_usd_micros = wire
            .billing
            .as_ref()
            .and_then(|billing| billing.total_usd_micros)
            .or(wire.total_usd_micros);
        let diff = wire.diff.or(wire.diff_summary);
        let title = wire.title.unwrap_or_else(|| crate::infer_run_title(&goal));
        let workflow_name = Some(workflow.name.clone());
        let workflow_slug = workflow.slug.clone();

        Ok(Self {
            id,
            title,
            goal,
            workflow,
            automation: wire.automation,
            repository,
            created_by: wire.created_by,
            origin: wire.origin.unwrap_or_default(),
            labels: wire.labels,
            status: lifecycle.status,
            pending_control: lifecycle.pending_control,
            lifecycle,
            sandbox: wire.sandbox,
            models: wire.models,
            source_directory: wire.source_directory,
            start_time: timestamps.started_at,
            created_at: timestamps.created_at,
            last_event_at: timestamps.last_event_at,
            duration_ms: timestamps.duration_ms,
            elapsed_secs: timestamps.elapsed_secs,
            timestamps,
            total_usd_micros,
            billing: wire.billing.or_else(|| {
                total_usd_micros.map(|total_usd_micros| RunBillingSummary {
                    total_usd_micros: Some(total_usd_micros),
                })
            }),
            diff_summary: diff,
            diff,
            pull_request: wire.pull_request,
            current_question: wire.current_question,
            superseded_by: wire.superseded_by,
            links: wire.links.unwrap_or(RunLinks { web: None }),
            run_id: id,
            workflow_name,
            workflow_slug,
            repo_origin_url,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowRef {
    #[serde(default)]
    pub slug: Option<String>,
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AutomationRef {
    pub id:   String,
    #[serde(default)]
    pub name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunOrigin {
    pub kind: RunOriginKind,
}

impl Default for RunOrigin {
    fn default() -> Self {
        Self {
            kind: RunOriginKind::Api,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RunOriginKind {
    Api,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunModel {
    #[serde(default)]
    pub provider: Option<String>,
    pub name:     String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunLifecycle {
    pub status:          RunStatus,
    #[serde(default)]
    pub pending_control: Option<RunControlAction>,
    #[serde(default)]
    pub queue_position:  Option<u32>,
    #[serde(default)]
    pub error:           Option<RunError>,
    pub archived:        bool,
    #[serde(default)]
    pub archived_at:     Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunError {
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunTimestamps {
    pub created_at:    DateTime<Utc>,
    #[serde(default)]
    pub started_at:    Option<DateTime<Utc>>,
    #[serde(default)]
    pub last_event_at: Option<DateTime<Utc>>,
    #[serde(default)]
    pub completed_at:  Option<DateTime<Utc>>,
    #[serde(default)]
    pub duration_ms:   Option<u64>,
    #[serde(default)]
    pub elapsed_secs:  Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunBillingSummary {
    #[serde(default)]
    pub total_usd_micros: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunLinks {
    #[serde(default)]
    pub web: Option<String>,
}

impl Run {
    #[allow(
        clippy::too_many_arguments,
        reason = "Run is a public wire DTO; the constructor centralizes derived fields."
    )]
    pub fn new(
        run_id: RunId,
        workflow_name: Option<String>,
        workflow_slug: Option<String>,
        goal: String,
        title: String,
        labels: HashMap<String, String>,
        source_directory: Option<String>,
        repo_origin_url: Option<String>,
        created_by: Option<Principal>,
        start_time: Option<DateTime<Utc>>,
        last_event_at: Option<DateTime<Utc>>,
        completed_at: Option<DateTime<Utc>>,
        status: RunStatus,
        pending_control: Option<RunControlAction>,
        duration_ms: Option<u64>,
        total_usd_micros: Option<i64>,
        superseded_by: Option<RunId>,
        diff_summary: Option<DiffSummary>,
        pull_request: Option<PullRequest>,
        archived_at: Option<DateTime<Utc>>,
        sandbox: Option<RunSandbox>,
        models: Vec<RunModel>,
        current_question: Option<InterviewQuestionRecord>,
        web_url: Option<String>,
    ) -> Self {
        let created_at = run_id.created_at();
        let repository = Some(repository_ref(
            repo_origin_url.as_deref(),
            source_directory.as_deref(),
        ));
        let elapsed_secs = elapsed_secs(duration_ms);
        let billing = total_usd_micros.map(|total_usd_micros| RunBillingSummary {
            total_usd_micros: Some(total_usd_micros),
        });
        let workflow_name_for_compat = workflow_name.unwrap_or_else(|| "unnamed".to_string());
        let workflow_slug_for_compat = workflow_slug.clone();

        Self {
            id: run_id,
            title,
            goal,
            workflow: WorkflowRef {
                slug: workflow_slug,
                name: workflow_name_for_compat.clone(),
            },
            automation: None,
            repository,
            created_by,
            origin: RunOrigin::default(),
            labels,
            lifecycle: RunLifecycle {
                status,
                pending_control,
                queue_position: None,
                error: None,
                archived: archived_at.is_some(),
                archived_at,
            },
            sandbox,
            models,
            source_directory,
            timestamps: RunTimestamps {
                created_at,
                started_at: start_time,
                last_event_at,
                completed_at,
                duration_ms,
                elapsed_secs,
            },
            billing,
            diff: diff_summary,
            pull_request,
            current_question,
            superseded_by,
            links: RunLinks { web: web_url },
            run_id,
            workflow_name: Some(workflow_name_for_compat.clone()),
            workflow_slug: workflow_slug_for_compat,
            repo_origin_url,
            start_time,
            created_at,
            last_event_at,
            status,
            pending_control,
            duration_ms,
            elapsed_secs,
            total_usd_micros,
            diff_summary,
        }
    }
}

fn default_run_status() -> RunStatus {
    RunStatus::Submitted
}

fn repository_ref(repo_origin_url: Option<&str>, source_directory: Option<&str>) -> RepositoryRef {
    RepositoryRef {
        name:       repository_name(repo_origin_url, source_directory),
        origin_url: repo_origin_url.map(ToOwned::to_owned),
        provider:   repository_provider(repo_origin_url),
    }
}

fn repository_provider(repo_origin_url: Option<&str>) -> RepositoryProvider {
    let Some(origin) = repo_origin_url.filter(|origin| !origin.trim().is_empty()) else {
        return RepositoryProvider::Unknown;
    };
    if is_github_origin(origin) {
        RepositoryProvider::Github
    } else {
        RepositoryProvider::Git
    }
}

fn is_github_origin(origin: &str) -> bool {
    origin.starts_with("git@github.com:")
        || origin.starts_with("https://github.com/")
        || origin.starts_with("http://github.com/")
        || origin.starts_with("ssh://git@github.com/")
}

fn repository_name(repo_origin_url: Option<&str>, source_directory: Option<&str>) -> String {
    repo_origin_url
        .and_then(repository_name_from_origin)
        .or_else(|| {
            source_directory
                .and_then(path_basename)
                .map(ToOwned::to_owned)
        })
        .unwrap_or_else(|| "unknown".to_string())
}

#[expect(
    clippy::disallowed_types,
    reason = "Run summaries parse the origin only to extract an owner/repo label; raw URLs are not logged."
)]
fn repository_name_from_origin(origin: &str) -> Option<String> {
    if let Some(path) = origin
        .strip_prefix("git@")
        .and_then(|url| url.split_once(':').map(|(_, path)| path))
    {
        return repository_name_from_path(path).map(ToOwned::to_owned);
    }

    let parsed = url::Url::parse(origin).ok()?;
    let path = parsed.path().trim_matches('/');
    repository_name_from_path(path).map(ToOwned::to_owned)
}

fn repository_name_from_path(path: &str) -> Option<&str> {
    let stripped = path.strip_suffix(".git").unwrap_or(path);
    let mut segments = stripped.rsplit('/').filter(|segment| !segment.is_empty());
    let repo = segments.next()?;
    let owner = segments.next();
    if let Some(owner) = owner {
        let start = stripped.len() - owner.len() - repo.len() - 1;
        stripped.get(start..)
    } else {
        Some(repo)
    }
}

fn path_basename(path: &str) -> Option<&str> {
    path.rsplit(['/', '\\']).find(|segment| !segment.is_empty())
}

fn elapsed_secs(duration_ms: Option<u64>) -> Option<f64> {
    duration_ms.map(|ms| ms as f64 / 1000.0)
}
