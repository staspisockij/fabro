Implemented cleanup fixes from the review pass.

What I changed:
- Replaced blocking Dockerfile reads on async environment create/replace paths with `tokio::fs::read_to_string`.
- Threaded the server `EnvironmentStore` catalog into automation manifest materialization so automation-created manifests resolve server-owned environments.
- Added environment catalog injection to manifest/server tests that now require server-owned environment resolution.
- Updated obsolete tests that expected project `[environments.*]` Dockerfile bundling to instead assert the new targeted server-managed error.
- Fixed clippy issues:
  - imported async fs path instead of absolute `tokio::fs`.
  - removed stale `RunSettingsBuilder` usage/import.
  - restored non-test `ServerDaemon` import.
  - used explicit `MergeMap::<EnvironmentLayer>::default()`.

Validation run:
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy -q -p fabro-environment -p fabro-manifest -p fabro-server --all-targets -- -D warnings` ✅
- `cargo nextest run -p fabro-environment` ✅
- `cargo nextest run -p fabro-config` ✅
- `cargo nextest run -p fabro-manifest` ✅
- `cargo nextest run -p fabro-server` ✅

Note: the parallel subagents completed, but their tool responses did not expose visible findings in this environment, so I performed the targeted review directly and fixed the concrete issues found.