## Summary

Three parallel review agents (reuse, quality, efficiency) converged on the same core issues. Applied the following fixes:

1. **Removed redundant `state.store.open_run` call** in `delete_run_internal` (`server.rs`). Introduced a new internal enum `SandboxDeleteOutcome { Absent, Cleaned, Preserved(_) }` returned by `delete_run_sandbox_resource`, so the outer code derives `Deleted`/`AlreadyAbsent` from the helper's signal plus `had_managed_run` instead of doing a second store open. This also eliminates the dead `Preserved(response) => Ok(Preserved(response))` rewrap. (Flagged by all 3 reviewers.)

2. **Deleted the `validate_batch_run_ids` 1-line trampoline** in `lifecycle.rs`. Folded `validate_batch_run_id_strings` back into `validate_batch_run_ids(run_ids: Vec<String>)` with a single signature, updating both call sites (archive and delete). (Flagged by reuse + quality.)

3. **Reused the new `create_preserved_local_sandbox_run` helper** in the existing `delete_run_with_preserved_sandbox_returns_handoff` test, removing ~40 lines of duplicated event setup that would otherwise drift. (Flagged by quality.)

4. **Added a comment to `deleteRuns`** in `run-actions.ts` explaining the `as unknown as BatchDeleteRunsRequest` cast (openapi-generator `Set<T>` workaround), pointing to the canonical explanation on `batchRunLifecycleAction`. (Flagged by reuse + quality.)

**Skipped** (low value): generic batch dispatcher unifying archive/delete (different value-bearing fields), merging `deleteRuns` into `batchRunLifecycleAction` (different action shape with `force`), parallelizing the batch loop (consistency with archive batch matters more than speculative concurrency), and `&Arc<AppState>` vs `&AppState` (driven by the inner signature, not this diff).

Verification: `cargo nextest run -p fabro-server batch_delete delete_run prune_runs` (11/11 pass), `cargo fmt --check`, `cargo clippy -p fabro-server -- -D warnings`, `cargo check --workspace`, `bun test app/lib/run-actions.test.ts` (17/17 pass), and `bun run typecheck` all pass.