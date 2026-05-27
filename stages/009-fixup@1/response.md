All verify steps pass. Summary of the fix:

**Root cause:** Two tests (`pause_run_sets_pending_control_on_board_response` and `unpause_run_sets_pending_control`) manually set `RunStatus::Running`/`Paused { prior_block: None }` and `worker_pid = Some(u32::MAX)` to simulate an active worker. The previous implementation used SIGUSR1/SIGUSR2 against `worker_pid`, so that was sufficient. After the control-bus refactor, pause/unpause now require a `RunAnswerTransport` on the managed run, so the handler returned 409 "Run worker is not available."

**Fix:** In both tests, attach a worker `RunAnswerTransport` (built via the existing `worker_transport_with_receiver` helper) to the managed run alongside the manual status/pid mutation.

Verified:
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `cargo nextest run --workspace --profile ci` (6438 passed, 179 skipped)
- `cargo dev docs check`
- `bun install`, `apps/fabro-web` typecheck + test, `lib/packages/fabro-api-client` typecheck
- `cargo dev build -- -p fabro-cli --release`