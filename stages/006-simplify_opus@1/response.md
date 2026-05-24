All checks pass. Here's a summary of what was fixed.

## Summary

Launched three parallel review agents (reuse / quality / efficiency) and aggregated their findings. Applied the high-value fixes:

### Rust (`lib/crates/fabro-server`)

1. **Efficiency P0 — readiness resolved once per batch.** `batch_run_archive_item` previously called `state.decorate_run_summary(...)` inside the per-id loop, which re-resolves LLM credentials on every iteration (up to 250 LLM client builds per request). Now `batch_run_archive_action` calls `state.ask_fabro_readiness().await` once, then per-item uses `readiness.decorate(summary)` directly. Exposed `AskFabroReadiness`, `AskFabroReadiness::decorate`, and `AppState::ask_fabro_readiness` as `pub(crate)`.
2. **Removed duplicate `WorkflowError → HTTP` mapping.** Extracted `archive_workflow_error_to_api_error(err) -> ApiError` and shared it between the new batch handler and the existing single-run `run_archive_action`.
3. **Removed duplicate `operations::{archive,unarchive}` glue.** Extracted `run_archive_operation(state, id, actor, action)` returning `Result<BatchRunLifecycleResultOutcome, WorkflowError>` (the single-run handler discards the outcome). The single-run handler and batch handler now share this body.
4. **Removed hand-rolled `batch_error_entry` builder.** Added `ApiError::into_response_entry() -> ErrorResponseEntry` in `error.rs` (one source of truth for the wire shape). Batch failures now construct standard `ApiError` instances (`ApiError::not_found`, `ApiError::new(StatusCode::CONFLICT, ...)`, etc.) and convert at the boundary. Dropped the `batch_success_result` / `batch_failure_result` builders; result entries are now inlined or built via `batch_result_failure(id, outcome, ApiError)`.
5. Removed now-unused `Run` and `ErrorResponseEntry` imports from `lifecycle.rs`.

### TypeScript (`apps/fabro-web`)

6. **Removed local `runWord` helper**, switched all callers to the existing `plural(n, "run", "runs")` helper from `components/settings-panel`.
7. **Simplified `summarizeBatchLifecycleAction`.** Dropped the redundant `total` parameter (was always either `summary.requested` or fabricated by callers) and the redundant `allSucceeded` wrapper (derivable from `summary.failed === 0`). Now takes a single `BatchRunLifecycleSummary` and returns the toast directly. Callers in `ColumnActionsMenu` and `BulkActionToolbar` updated; tests rewritten accordingly.

### Skipped findings (intentional)

- **`uniqueItems: true` on `BatchRunLifecycleRequest.run_ids`** — explicitly required by the implementation plan; the `as unknown as` cast workaround stays. The server-side dedup validation matches the schema constraint and produces a 400 with a clear message.
- **Boilerplate handler pair `batch_archive_runs`/`batch_unarchive_runs`** — mirrors the existing single-run `archive_run`/`unarchive_run` pattern in the same file; collapsing would diverge from convention.
- **`json_bearer_request` → `json_request` refactor** — pre-existing helper, low-priority; left alone.
- **`BatchLifecycleLabel` stringly-typed verb** — localized to one helper, low impact; the simplification above already removed the redundant `.toLowerCase()` plumbing in callers.

### Verification

- `cargo check -p fabro-server --tests` — clean
- `cargo +nightly-2026-04-14 clippy -p fabro-server --all-targets -- -D warnings` — clean
- `cargo +nightly-2026-04-14 fmt -p fabro-server` — applied
- `cargo nextest run -p fabro-server -E 'test(/archive|api_error/)'` — 11/11 pass (6 batch tests + 5 single-run/error tests)
- `cd apps/fabro-web && bun test app/routes/runs.test.tsx app/lib/run-actions.test.ts` — 27/27 pass
- `cd apps/fabro-web && bun run typecheck` — clean