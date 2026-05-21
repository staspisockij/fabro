Implemented one cleanup/fix from the review pass:

- Fixed retry attempt wall-time measurement in `lib/crates/fabro-core/src/executor.rs`.
  - Previously, `execute_with_retry` used one stopwatch for the whole retry loop, so later attempt `wall_time` included prior attempts and retry backoff.
  - Now each attempt gets its own `attempt_start`, keeping retry backoff as run/stage wall waiting time but not leaking into per-attempt stage timing.
- Added a regression test:
  - `executor_retry_attempt_wall_time_excludes_prior_attempts_and_backoff`

Validation run:

```bash
cargo test -p fabro-core executor_retry_attempt_wall_time_excludes_prior_attempts_and_backoff -- --nocapture
cargo test -p fabro-core executor_retry_backoff_delay -- --nocapture
cargo +nightly-2026-04-14 fmt --check --all
git diff --check
```

All passed.

Current working tree has one modified file:

```text
M lib/crates/fabro-core/src/executor.rs
```