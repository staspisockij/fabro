Net 32-line reduction. Here's the summary of fixes applied:

## Summary

Three review agents flagged duplication and clone churn in the retry feature. I applied these focused fixes:

**Rust (`retry.rs`, `lifecycle.rs`):**
- Removed dead writes (`spec.run_id = ...`, `spec.provenance = ...`) and double clones of every spec field. Destructured `source.spec` by move so each field flows directly into the `RunCreated` event without an intermediate `RunSpec` clone.
- Changed `RetryRunInput::new_run_id` from `Option<RunId>` to required `RunId` — the handler always pre-generates one to compute `web_url`; the operation no longer carries a phantom default.

**Frontend (`run-actions.ts`, `mutations.ts`, `run-detail.tsx`):**
- Added `"retry"` to the `LifecycleAction` union and folded `retryErrorMessage` into `mapError` (both had identical 404 + detail + fallback shape).
- Dropped `RetryMutationResult` — now uses the existing `LifecycleMutationResult` with `intent: "retry"`.
- Folded `useRetryRun` into `useLifecycleMutation` via an `onSuccessExtra` callback. The retry path now skips invalidating the source run's `detail`/`billing` caches (which retry doesn't change).
- Folded `handleRetryResult` + `lastRetryResultRef` into the existing `handleLifecycleToastResult` + `lifecycleToastStateRef` with an optional `navigate` parameter. The parallel toast-state machine is gone.
- Updated the matching test to use the unified handler.

**Verified:** `cargo check`, `cargo nextest run -p fabro-workflow operations::retry`, `cargo nextest run -p fabro-server retry` (4 + 9 tests pass), `cargo clippy --workspace --all-targets -D warnings`, `cargo fmt`, `bun run typecheck`. The 8 web test failures present when running all files together exist on the baseline (HEAD before my changes), so they're pre-existing and unrelated.

**Findings I deliberately skipped** (out of scope or low ROI for a retry-focused review):
- Extracting a shared `RunCreated`-from-`RunSpec` builder between `fork.rs` and `retry.rs` (broader refactor).
- Fixing `fork.rs`/`rewind.rs` to use `map_open_run_error` (pre-existing bugs, not introduced here).
- Moving retry test fixtures into a shared `test_support` module.
- Auditing the `Box::pin(...)` additions in server tests.
- The `pt-3` → `pt-3.5` test-only fix that snuck into this commit.
- Normalizing the `canRetry` signature to match `canCancel`/`canArchive` — the divergence is justified (needs failure reason + archived flag).