Done. Here's a summary of what was fixed:

## High-impact refactors

1. **Extracted duplicated `runtime_*_config` helpers** (~180 LOC dedup): moved `runtime_daytona_config`, `runtime_docker_config`, `duration_to_minutes_i32`, `size_to_gb_i32`, `resolve_interp` from both `fabro-workflow/operations/start.rs` and `fabro-server/run_manifest.rs` into a new `fabro-sandbox::from_environment` module. Both callers now share one implementation.

2. **Replaced `apply_*_override` with `Combine`-based merge** (~95 LOC removed): wired up the previously-dead `RunEnvironmentLayer::into_environment_override` so `run_layer.into_environment_override().combine(base.clone())` replaces all five `apply_*_override` functions and their hand-rolled CIDR/extend logic.

3. **Dropped duplicate `validate_daytona_snapshot_name` call**: the snapshot check was running twice for the run-selected environment. Now runs once.

4. **Dropped dead `WorkflowSettings.environments` dense field**: only one test assertion read it; also removed `resolve_environments` and `Combine`-resolution plumbing.

5. **Replaced stringly-typed `clone_sandbox_*_github_credentials(&str)` with `EnvironmentProvider::is_clone_based()`**: the enum already had this method.

6. **Deduplicated demo `EnvironmentSettings` literal**: bound to a local in `demo/mod.rs::runs::settings()`.

## Skipped (after weighing trade-offs)

- **Flatten `RunEnvironmentSettings → { id, environment: EnvironmentSettings }`**: saves ~30 lines but adds an access-path hop on every field read.
- **Type provider/mode as enums in sparse layers**: would break `workflow_settings_accumulate_multiple_run_errors`, which depends on resolve-time error accumulation across the provider field and `run.prepare`.
- **Derive `Combine` on `EnvironmentNetworkLayer`**: would require touching the resolver in 3 places for negligible savings.

## Verification

- `cargo check --workspace --tests` — clean.
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean.
- `cargo nextest run` on affected crates — 2194/2195 pass, 1 fail (pre-existing `[run.sandbox]` test fixture that the original implement stage left broken).
- Compared full workspace failures vs origin: same 30 distinct test names fail on both branches (all `--sandbox`/old-fixture pre-existing failures); **0 net regressions** from the refactor.

Net diff: **~360 lines removed** across 14 files.