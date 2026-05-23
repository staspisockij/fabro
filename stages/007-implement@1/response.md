Implemented named environments across the Rust config/types/runtime stack, CLI/API/tool manifest surfaces, OpenAPI, TypeScript client generation, and public docs.

### What changed

- Added top-level `[environments.<slug>]` catalog support and `[run.environment] id = "..."`.
- Added sparse config layers and dense settings types for:
  - `EnvironmentSettings`
  - `RunEnvironmentSettings`
  - image/resources/network/lifecycle/labels/volumes/env
  - `EnvironmentProvider`
  - `EnvironmentNetworkMode`
- Removed user-facing `[run.sandbox]` parsing/resolution/types.
- Added defaults:
  - selected `run.environment.id = "default"`
  - Docker `default` environment
  - convenience built-in `local`, `docker`, and `daytona` named environments.
- Implemented environment resolution:
  - slug lookup and missing slug errors
  - sparse run-level overrides
  - `env`/`labels` merge by key
  - `volumes` replace wholesale
  - CIDR validation
  - hard security capability errors
- Replaced runtime mapping:
  - Docker image/CPU/memory/network/env mapping
  - Daytona snapshot/resources/network/labels/volumes/env/lifecycle mapping
  - Local environment env handling
- Added preflight capability warnings for unsupported best-effort hints.
- Renamed selection surfaces from `sandbox` to `environment` where they select an execution profile:
  - CLI `--environment`
  - server `--environment`
  - `ManifestArgs.environment`
  - Fabro tool create spec `environment`
- Preserved runtime “sandbox” terminology for concrete instances and commands.
- Updated OpenAPI schema and regenerated the TypeScript Axios client.
- Updated core environment/run/server/Daytona/CLI docs and repo `.fabro` configs.

### Validation run

Passed:

- `cargo check -q --workspace`
- `cargo test -q --workspace --no-run`
- `cargo test -q -p fabro-config`
- `cargo test -q -p fabro-workflow runtime_docker_config_maps_environment_hints`
- `cargo test -q -p fabro-server prepare_manifest_inlines_project_config_daytona_dockerfile_from_bundle`
- `cargo test -q -p fabro-server prepare_manifest_errors_when_project_config_dockerfile_bundle_is_missing`
- `cargo test -q -p fabro-tool`
- `cargo test -q -p fabro-api`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings`
- `cd lib/packages/fabro-api-client && bun run typecheck`

Note: full `cargo test -q -p fabro-server` still has 3 order-dependent storage-related failures unrelated to this change; each of those failing tests passes when run individually.