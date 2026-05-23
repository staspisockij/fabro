Implemented the legacy `[run.sandbox]` auto-migration.

Summary:
- Added isolated `fabro-config` migration module:
  - Detects legacy `[run.sandbox]`
  - Rewrites to `[run.environment] id = "default"` plus `[environments.default]`
  - Supports Daytona/Docker field mappings, `preserve`, `env`, `skip_clone = true`, labels, snapshots, volumes, Docker image/memory/cpu quota
  - Writes numbered sibling backups
  - Reports unsupported/ambiguous keys with full paths
- Hooked migration only into file loading via `load_settings_path`; in-memory parsing remains strict.
- Added migration tests, loader test, backup tests, failure diagnostics tests, and `skip_clone` coverage.
- Added docs warning and new changelog entry.
- Added a small existing test isolation fix in `fabro-config/src/user.rs` to prevent `FABRO_HOME` races during full crate tests.

Verification run:
- `cargo test -p fabro-config --quiet` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` ✅
- `cargo test -p fabro-config legacy_run_sandbox_is_rejected --quiet` ✅
- Loader migration focused test ✅

Docs reference check:
- Requested `rg ...` command could not run because `rg` is not installed in the environment.
- Used an equivalent `grep -R -n -E ...` check instead; remaining `[run.sandbox]` references are migration/removal notes or historical changelog entries.