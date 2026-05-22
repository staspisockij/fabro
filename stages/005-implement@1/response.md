All tasks from the plan have been completed:

## Summary

### Removed `[features]` settings namespace and `session_sandboxes` flag

**Config layer (`fabro-config`):**
- Deleted `FeaturesLayer` (`layers/features.rs`) and `resolve_features` (`resolve/features.rs`)
- Removed `features` from `SettingsLayer` and the parser allow-list — old `[features]` config is now rejected as an unknown top-level key (with a new regression test)
- Removed `[features]` section from `defaults.toml`
- Removed `features` resolution from `ServerSettingsBuilder` and `UserSettingsBuilder`

**Types (`fabro-types`):**
- Deleted `settings/features.rs` and `FeaturesNamespace`
- Removed `features` field from `ServerSettings` and `UserSettings` (dense)
- Removed `FeatureDisabled` variant from `AskFabroUnavailableReason`

**Server (`fabro-server`):**
- Simplified `AskFabroReadiness` to only depend on sandbox presence/runtime and LLM configuration
- Deleted `system_features()` helper and removed `features` from `SystemInfoResponse`
- Updated tests in `server/tests.rs`, `tests/it/api/settings.rs`, `tests/it/api/system.rs`, `tests/it/api/runs.rs`
- Cleaned up demo-mode fixtures

**API (`fabro-api`):**
- Removed `FeaturesNamespace`/`SystemFeatures`/`feature_disabled` from OpenAPI spec
- Removed `with_replacement` for `FeaturesNamespace` in `build.rs`
- Removed reexport from `src/lib.rs`
- Updated `server_settings_round_trip` test
- TypeScript Axios client updated manually (generator broken under Node 18): removed `features-namespace.ts`/`system-features.ts`, updated `server-settings.ts`/`system-info-response.ts`, removed `FEATURE_DISABLED` from `ask-fabro.ts`, updated `index.ts` and `FILES` manifest

**Frontend (`apps/fabro-web`):**
- `start.tsx`: removed `useSystemInfo` and the gated project/branch controls; controls are now always rendered
- `run-detail.tsx`: removed `FEATURE_DISABLED` from the unavailable-reason tooltip map
- `settings-resources.test.tsx`: removed `features` from the fixture

**Docs:**
- Removed `[features]` content from `docs/public/administration/server-configuration.mdx`, `docs/public/reference/user-configuration.mdx`, and `docs/public/execution/run-configuration.mdx`
- OpenAPI spec (`fabro-api.yaml`) cleaned up
- `cargo dev docs check` passes; `cargo dev docs refresh` regenerated generated docs (no diff in user-config except trailing newline)

### Verification
- `cargo build -p fabro-api` ✅
- `cargo nextest run -p fabro-config -p fabro-api -p fabro-server -p fabro-cli` ✅ (3 pre-existing graph-render failures unrelated to this change)
- `bun test` ✅ (same 7 pre-existing failures as base commit)
- `bun run typecheck` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` ✅
- `cargo dev docs check` ✅
- Acceptance grep: `session_sandboxes|FeaturesNamespace|SystemFeatures|feature_disabled|"Ask Fabro is disabled"` returns no matches in `lib`/`apps`/`docs/public` (only stale binaries and historical plans, which are explicitly out of scope)