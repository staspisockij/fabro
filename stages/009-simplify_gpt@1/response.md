Implemented cleanup after the review pass.

Fixed:
- Centralized environment env-var interpolation in `RunEnvironmentSettings::resolve_env(...)`.
  - Reused by Docker sandbox mapping and workflow startup.
  - Removed duplicate `resolve_interp` helpers.
  - Added unit tests for interpolation success, fallback, and empty env.
- Updated stale CLI integration tests from removed `--sandbox` run-selection flag to `--environment`.
  - Also refreshed help snapshots/text for `run`, `create`, `preflight`, and `server start`.
- Minor comment cleanup: “sandbox selection” → “environment selection”.

Validated with:
- `cargo +nightly-2026-04-14 fmt --all`
- `cargo check -q -p fabro-types -p fabro-sandbox -p fabro-workflow -p fabro-cli`
- `cargo +nightly-2026-04-14 clippy -q -p fabro-types -p fabro-sandbox -p fabro-workflow -p fabro-cli --all-targets -- -D warnings`
- Targeted CLI help tests for updated snapshots
- `cargo test -q -p fabro-types run_environment_settings_tests -- --nocapture`
- `git diff --check`