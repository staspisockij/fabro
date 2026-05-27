Goal: # Issue #398: Build automation run materialization core

Source: https://github.com/fabro-sh/fabro/issues/398
State: OPEN
Author: brynary
Created: 2026-05-25T15:06:26Z
Updated: 2026-05-27T21:42:25Z
Labels: none
Assignees: none
Comments: none

## Body

## Goal

Refactor server run creation so automation-triggered runs can share the existing run creation pipeline, and add a production materializer that turns an automation target into a run manifest.

## Scope

Extract the common body of `handler/runs.rs::create_run` into a crate-private helper that accepts a request object shaped like:

```rust
struct CreateRunFromManifestRequest {
    manifest: fabro_api::types::RunManifest,
    submitted_manifest_bytes: Vec<u8>,
    explicit_run_id: Option<fabro_types::RunId>,
    explicit_title_supplied: bool,
    actor: fabro_types::Principal,
    headers: axum::http::HeaderMap,
    automation: Option<fabro_types::AutomationRef>,
}
```

Keep existing `POST /runs` behavior unchanged by calling the helper with `automation: None`.

Add a crate-private materializer abstraction:

```rust
pub(crate) struct AutomationRunMaterializeInput {
    pub automation_id: fabro_automation::AutomationId,
    pub target: fabro_automation::AutomationTarget,
    pub run_id: fabro_types::RunId,
    pub user_settings_path: std::path::PathBuf,
    pub temp_root: std::path::PathBuf,
}

pub(crate) struct AutomationRunMaterialized {
    pub manifest: fabro_api::types::RunManifest,
    pub submitted_manifest_bytes: Vec<u8>,
}

#[derive(thiserror::Error, Debug)]
pub(crate) enum AutomationRunMaterializeError {
    #[error("invalid automation target: {0}")]
    InvalidTarget(String),
    #[error("failed to clone automation repository: {0}")]
    CloneFailed(String),
    #[error("failed to resolve automation workflow: {0}")]
    WorkflowNotFound(String),
    #[error("failed to build run manifest: {0}")]
    Manifest(String),
}

#[async_trait::async_trait]
pub(crate) trait AutomationRunMaterializer: Send + Sync {
    async fn materialize(
        &self,
        input: AutomationRunMaterializeInput,
    ) -> Result<AutomationRunMaterialized, AutomationRunMaterializeError>;
}
```

Production materializer behavior:

- Validate target repository as GitHub `owner/repo`.
- Construct uncredentialed metadata URLs only; never persist credentialed clone URLs.
- Use server GitHub credentials and existing clone credential helpers when configured.
- Create a per-run temp directory under `AutomationRunMaterializeInput.temp_root`.
- Shallow clone `https://github.com/{owner}/{repo}.git`.
- Check out the configured ref.
- Resolve the workflow selector with `fabro_config::project::WorkflowLocation::resolve`.
- Build a `RunManifest` with `fabro_manifest::build_run_manifest`.
- Pass `user_settings_path: Some(state.active_config_path().to_path_buf())`.
- Run git commands with `tokio::process::Command` argv values, not shell command strings.
- Set `GIT_TERMINAL_PROMPT=0` and explicit command timeouts.

Test support:

- Add test-only injection for a fake `AutomationRunMaterializer` behind tests or the existing `test-support` feature.
- The fake should let route tests assert the input and return a controlled manifest without live GitHub access.

## Files

Create:

- `lib/crates/fabro-server/src/automation_materializer.rs`

Modify:

- `lib/crates/fabro-server/src/server.rs`
- `lib/crates/fabro-server/src/server/handler/runs.rs`
- `lib/crates/fabro-server/src/test_support.rs`
- Relevant server tests around run creation and test support

Read before implementation:

- `docs/internal/error-handling-strategy.md`
- `docs/internal/server-secrets-strategy.md`
- `docs/internal/testing-strategy.md`

## Acceptance Criteria

- Existing `POST /runs` behavior and response shape are unchanged.
- Shared run creation can attach optional automation metadata to the created run.
- The production materializer builds a run manifest from a GitHub automation target.
- Git operations use argv-based process execution, disable terminal prompts, and have explicit timeouts.
- Credentialed URLs are never stored in run metadata or error text.
- Tests can use a fake materializer without network or live GitHub access.

## Verification

Add tests for:

- Existing `POST /runs` regression behavior.
- Helper-created runs with `automation: None` and with automation metadata.
- Fake materializer injection.
- Target URL construction.
- Credential redaction.
- Ref checkout command planning.
- Workflow path resolution using temp directories.

Run:

```bash
cargo nextest run -p fabro-server runs
cargo nextest run -p fabro-server automation_materializer
```


## Completed stages
- **toolchain**: succeeded
  - Script: `command -v cargo >/dev/null || { curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && sudo ln -sf $HOME/.cargo/bin/* /usr/local/bin/; }; cargo --version 2>&1`
  - Output:
    ```
    cargo 1.95.0 (f2d3ce0bd 2026-03-21)
    ```
- **preflight_compile**: succeeded
  - Script: `cargo check -q --workspace 2>&1`
  - Output: (empty)
- **preflight_lint**: succeeded
  - Script: `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings 2>&1`
  - Output: (empty)


Read the plan file referenced in the goal and implement every step. Make all the code changes described in the plan. Use red/green TDD.