Goal: ---
title: "feat: Add run approval controls to MCP and CLI"
type: feat
status: active
date: 2026-05-25
---

# feat: Add run approval controls to MCP and CLI

## Summary

Fabro already has pre-execution run approval state and REST endpoints:

- `POST /api/v1/runs/{id}/approve`
- `POST /api/v1/runs/{id}/deny`

This plan exposes that capability through the existing human run-management surfaces:

- `fabro_run_interact` gains `approve` and `deny` actions.
- The CLI gains top-level batch commands:
  - `fabro approve <RUNS>...`
  - `fabro deny [--reason <REASON>] <RUNS>...`

Approval remains a human/user action. Workflow-agent `fabro_tools` must not be able to approve or deny child runs it created.

## Key Interface Changes

### MCP

Extend `fabro_run_interact`:

- Add actions: `approve`, `deny`.
- Add optional parameter: `reason: string | null`.
- `reason` is valid only for `deny`; trim whitespace and send `None` for absent or blank values.
- `approve` and `deny` return the updated run summary using the existing `result.summary` shape.
- Update the tool description to include approval actions.

Example:

```json
{
  "run_id": "nightly",
  "action": "approve"
}
```

```json
{
  "run_id": "nightly",
  "action": "deny",
  "reason": "Not approved for execution"
}
```

### CLI

Add flattened top-level commands, alongside `archive` and `unarchive`:

```bash
fabro approve <RUNS>...
fabro deny [--reason <REASON>] <RUNS>...
```

Batch behavior:

- Resolve each argument using the same selector path as archive/unarchive.
- Attempt every requested run even if earlier runs fail.
- Text mode prints each successful short run id to stderr.
- If any run fails, exit non-zero after processing all runs.

JSON output:

```json
{
  "approved": ["01K..."],
  "errors": []
}
```

```json
{
  "denied": ["01K..."],
  "errors": []
}
```

Errors use the existing batch shape:

```json
{
  "identifier": "nightly",
  "error": "Run is not pending approval."
}
```

`fabro deny --reason <REASON>` applies the same reason to every run in the batch.

## Implementation Plan

### 1. Add client and shared tool backend methods

Files:

- `lib/crates/fabro-client/src/client.rs`
- `lib/crates/fabro-tool/src/common.rs`
- `lib/crates/fabro-tool/src/fabro_client.rs`
- Mock `FabroToolBackend` impls in tests under `fabro-tool` and `fabro-workflow`

Changes:

- Add `Client::approve_run(&RunId) -> Result<Run>`.
- Add `Client::deny_run(&RunId, Option<String>) -> Result<Run>`.
- Implement them by calling the generated `approve_run` and `deny_run` OpenAPI client methods.
- Add matching methods to `FabroToolBackend`.
- Implement them in `ClientBackend`.
- For `deny_run`, build `types::DenyRunRequest { reason }` only when the generated client requires a body; preserve the API behavior that omitted, null, empty, or whitespace-only reasons are stored as absent.

No OpenAPI or generated-client regeneration is expected because the endpoints and DTO already exist.

### 2. Extend `fabro_run_interact`

Files:

- `lib/crates/fabro-tool/src/interact.rs`
- `lib/crates/fabro-tool/src/common.rs`
- `lib/crates/fabro-tool/src/lib.rs`
- `lib/crates/fabro-mcp-server/src/server.rs`

Changes:

- Add `RunInteractAction::Approve` and `RunInteractAction::Deny`.
- Add `reason: Option<String>` to `FabroRunInteractParams`.
- Add `ValidatedInteractAction::Approve` and `ValidatedInteractAction::Deny { reason: Option<String> }`.
- Validate `reason` by trimming whitespace and dropping blank values.
- Dispatch:
  - `Approve` -> `backend.approve_run(&run_id)`
  - `Deny` -> `backend.deny_run(&run_id, reason)`
- Return `json!({ "summary": common::run_summary_result(&summary) })`.
- Update `interact_run_text` output automatically through the action name; no special summary text is required.
- Update tool descriptions from “start, message, interrupt, cancel…” to include “approve, deny”.

### 3. Block workflow-agent self-approval

Files:

- `lib/crates/fabro-workflow/src/handler/llm/api.rs`
- Existing run-tool tests in the same file

Changes:

- In `execute_fabro_run_tool`, parse `FabroRunInteractParams` before dispatching.
- If the tool call is `fabro_run_interact` with action `approve` or `deny`, return a `ToolError` explaining that run approval must be performed by a user through the API, CLI, web UI, or human MCP server.
- Do not rely only on server auth for this guard; the tool error should be immediate and explicit for workflow agents.
- Keep server `approve_run` and `deny_run` handlers on `RequiredUser`.
- Keep the existing server negative test that run-tools workers cannot call user-only routes, and extend it to include `/runs/{id}/deny`.

### 4. Add CLI approval commands

Files:

- `lib/crates/fabro-cli/src/args.rs`
- `lib/crates/fabro-cli/src/commands/runs/mod.rs`
- Create `lib/crates/fabro-cli/src/commands/runs/approval.rs`

Changes:

- Add:
  - `RunsApproveArgs { server: ServerTargetArgs, runs: Vec<String> }`
  - `RunsDenyArgs { server: ServerTargetArgs, reason: Option<String>, runs: Vec<String> }`
- Add `RunsCommands::Approve(RunsApproveArgs)` and `RunsCommands::Deny(RunsDenyArgs)`.
- Command help:
  - approve: “Approve pending workflow runs.”
  - deny: “Deny pending workflow runs.”
  - run args: “Run IDs or workflow names to approve/deny.”
  - reason flag: “Reason for denying execution.”
- Implement shared batch logic in `commands/runs/approval.rs`, patterned after `archive.rs`:
  - Resolve each identifier with `client.resolve_run`.
  - Call `client.approve_run` or `client.deny_run`.
  - Collect successes and per-identifier errors.
  - Print short run ids to stderr in text mode.
  - Print JSON only in JSON mode.
  - Fail at the end with `some runs could not be approved` or `some runs could not be denied`.
- Register the new dispatch arms in `commands/runs/mod.rs`.
- Update command-name reporting in `RunsCommands::name()`.

### 5. Update docs

Files:

- `docs/public/agents/mcp.mdx`
- `docs/public/reference/cli.mdx`

Changes:

- Update the `fabro_run_interact` row to include approve/deny.
- Add a short MCP example for approving or denying a pending run.
- Add generated or manually updated CLI reference sections for:
  - `fabro approve`
  - `fabro deny`
- If `docs/public/reference/cli.mdx` is generated from `fabro __cli-reference`, regenerate it after the CLI args are implemented.

## Test Plan

### `fabro-tool`

- Add unit tests for action validation:
  - `approve` validates with only `run_id` and action.
  - `deny` validates with absent reason as `None`.
  - `deny` trims a nonblank reason.
  - `deny` converts blank reason to `None`.
- Add dispatch tests with a mock backend:
  - `approve` calls `approve_run` and returns `result.summary`.
  - `deny` calls `deny_run` with the expected reason and returns `result.summary`.
- Update schema/tool-definition assertions to prove `approve`, `deny`, and `reason` appear in the `fabro_run_interact` schema.

Run:

```bash
cargo nextest run -p fabro-tool interact
```

### MCP integration

File:

- `lib/crates/fabro-cli/tests/it/cmd/mcp.rs`

Scenarios:

- `fabro_run_interact` action `approve`:
  - resolves selector through `/api/v1/runs/resolve`
  - posts to `/api/v1/runs/{id}/approve`
  - returns updated summary
- `fabro_run_interact` action `deny`:
  - resolves selector
  - posts to `/api/v1/runs/{id}/deny`
  - sends `{ "reason": "Not approved for execution" }` when reason is supplied
  - returns updated summary
- Existing tool-list/schema test checks the new actions and parameter.

Run:

```bash
cargo nextest run -p fabro-cli mcp_interact
```

### CLI command tests

Files:

- Create `lib/crates/fabro-cli/tests/it/cmd/approve.rs`
- Create `lib/crates/fabro-cli/tests/it/cmd/deny.rs`
- Modify `lib/crates/fabro-cli/tests/it/cmd/mod.rs`
- Modify `lib/crates/fabro-cli/tests/it/cmd/fabro.rs`

Scenarios:

- Help snapshots for `fabro approve --help` and `fabro deny --help`.
- Required-argument snapshots for missing `<RUNS>...`.
- Mock-server success path:
  - resolve `nightly-build`
  - call approve/deny endpoint
  - print short run id in text mode
- JSON success path:
  - approve returns `approved`
  - deny returns `denied`
  - both include `errors: []`
- Partial-error path:
  - one selector or endpoint fails
  - remaining runs are still attempted
  - JSON includes both successes and errors
  - process exits non-zero
- `fabro deny --reason "Needs review"` sends that reason in the request body.
- Top-level help snapshot includes `approve` and `deny`.

Run:

```bash
cargo nextest run -p fabro-cli approve deny fabro::help
```

### Server auth regression

File:

- `lib/crates/fabro-server/src/server/tests.rs`

Scenario:

- Extend `run_tools_worker_cannot_call_user_only_non_mcp_routes` so a run-tools worker remains rejected for:
  - `POST /runs/{target}/approve`
  - `POST /runs/{target}/deny`
  - an existing user-only route such as timeline

Run:

```bash
cargo nextest run -p fabro-server run_tools_worker_cannot_call_user_only_non_mcp_routes
```

### Final verification

Run targeted checks first:

```bash
cargo nextest run -p fabro-tool -p fabro-cli -p fabro-server
```

Before merge, run:

```bash
cargo +nightly-2026-04-14 fmt --check --all
cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings
```

Run full workspace tests if the client/backend trait changes produce broad compile churn:

```bash
cargo nextest run --workspace
```

## Assumptions

- Approval and denial remain user-authorized operations.
- Human MCP clients use normal CLI/server user auth and may approve or deny.
- Workflow-agent `fabro_tools` may inspect pending runs but must not approve or deny them.
- `fabro deny --reason <REASON>` applies one reason to every run in the batch.
- No API contract change is required because the REST approval endpoints already exist.


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
- **implement**: succeeded
  - Model: gpt-5.5, 5.1m tokens in / 34.7k out
- **simplify_opus**: succeeded
  - Model: claude-opus-4-7, 86.1k tokens in / 22.8k out
  - Files: /home/daytona/workspace/fabro/lib/crates/fabro-cli/src/commands/runs/approval.rs, /home/daytona/workspace/fabro/lib/crates/fabro-cli/tests/it/cmd/approve.rs, /home/daytona/workspace/fabro/lib/crates/fabro-cli/tests/it/cmd/archive.rs, /home/daytona/workspace/fabro/lib/crates/fabro-cli/tests/it/cmd/deny.rs, /home/daytona/workspace/fabro/lib/crates/fabro-cli/tests/it/cmd/support.rs, /home/daytona/workspace/fabro/lib/crates/fabro-cli/tests/it/cmd/unarchive.rs, /home/daytona/workspace/fabro/lib/crates/fabro-client/src/client.rs, /home/daytona/workspace/fabro/lib/crates/fabro-tool/src/interact.rs, /home/daytona/workspace/fabro/lib/crates/fabro-workflow/src/handler/llm/api.rs
- **simplify_gpt**: succeeded
  - Model: gpt-5.5, 726.4k tokens in / 6.6k out
- **verify**: failed
  - Script: `git fetch origin main 2>&1 && git merge --no-edit --no-stat origin/main 2>&1 && cargo +nightly-2026-04-14 fmt --all 2>&1 && cargo dev docs refresh 2>&1 && cargo +nightly-2026-04-14 fmt --check --all 2>&1 && { command -v rg >/dev/null 2>&1 || { echo 'rg is required for verify'; exit 127; }; } && ! rg -n 'AuthMode::Disabled|RunAuthMethod|RunSubjectProvenance|\bActorRef\b|\bActorKind\b|AuthenticatedSubject|AuthenticatedService|AuthorizeRunScoped|AuthorizeRunBlob|AuthorizeStageArtifact|AuthorizeCommandLog|auth_method\s*==\s*"disabled"' lib/crates apps lib/packages docs/public/api-reference/fabro-api.yaml 2>&1 && cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings 2>&1 && cargo nextest run --workspace --status-level slow --profile ci 2>&1 && cargo dev docs check 2>&1 && bun install --frozen-lockfile 2>&1 && (cd apps/fabro-web && bun run typecheck) 2>&1 && (cd apps/fabro-web && bun run test) 2>&1 && (cd lib/packages/fabro-api-client && bun run typecheck) 2>&1 && cargo dev build -- -p fabro-cli --release 2>&1`
  - Output:
    ```
    (1087 lines omitted)
    react-test-renderer is deprecated. See https://react.dev/warnings/react-test-renderer
    The current testing environment is not configured to support act(...)
    The current testing environment is not configured to support act(...)
    (pass) VncPanel render > renders an iframe with the signed URL on success [0.66ms]
    react-test-renderer is deprecated. See https://react.dev/warnings/react-test-renderer
    The current testing environment is not configured to support act(...)
    The current testing environment is not configured to support act(...)
    (pass) VncPanel render > renders an actionable error state for 409 startup failures [0.75ms]
    react-test-renderer is deprecated. See https://react.dev/warnings/react-test-renderer
    The current testing environment is not configured to support act(...)
    The current testing environment is not configured to support act(...)
    (pass) VncPanel render > reconnect button refetches the signed URL [0.71ms]
    
    5 tests failed:
    (fail) StageInsightsSidebar > renders permission badge for read-only [0.78ms]
    (fail) StageInsightsSidebar > renders permission badge for full access [0.70ms]
    (fail) StageInsightsSidebar > renders projected agent tool names, descriptions, categories, and invoked state [0.93ms]
    (fail) StageInsightsSidebar > legacy stages without agent tools keep permission fallback only [0.91ms]
    (fail) StageInsightsSidebar > renders empty-friendly content when stage projection is missing [0.63ms]
    
     484 pass
     5 fail
     1189 expect() calls
    Ran 489 tests across 59 files. [9.65s]
    error: script "test" exited with code 1
    ```

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## output icespanelview > shows api error state with the error message [<n>.68ms] react-test-renderer is deprecated. see https://react.dev/warnings/react-test-renderer the current testing environment is not


The verify step failed. Read the build output from context and fix all format, clippy, Rust test, docs, TypeScript typecheck/test, and build failures.