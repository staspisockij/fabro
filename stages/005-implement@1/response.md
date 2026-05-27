Implemented #398 automation run materialization core.

Summary:
- Added crate-private `automation_materializer` module with:
  - `AutomationRunMaterializeInput`
  - `AutomationRunMaterialized`
  - `AutomationRunMaterializeError`
  - `AutomationRunMaterializer`
  - production materializer
  - test fake materializer
- Refactored `POST /runs` creation through `create_run_from_manifest(...)`, preserving existing API behavior with `automation: None`.
- Added optional automation metadata persistence through shared run creation.
- Wired test-support injection into `AppState` / `TestAppStateBuilder`.
- Production materializer now:
  - validates GitHub `owner/repo` targets,
  - uses uncredentialed clone/metadata URLs,
  - resolves server GitHub clone credentials via existing helper,
  - shallow clones and checks out refs using argv-based `tokio::process::Command`,
  - disables git terminal prompts,
  - uses explicit timeouts,
  - resolves workflows and builds run manifests from temp checkouts.
- Added tests for run creation regression, automation metadata, fake injection, URL construction, credential redaction, ref checkout planning, and workflow path resolution.

Verification run:
- `cargo check -q --workspace`
- `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings`
- `cargo nextest run -p fabro-server runs`
- `cargo nextest run -p fabro-server automation_materializer`

All passed.