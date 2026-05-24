Implemented and committed the server sandbox provider policy.

Commit: `f5eac31bc feat: add server sandbox provider policy`

Summary:
- Added resolved `[server.sandbox.providers.{local,docker,daytona}].enabled` settings with backward-compatible defaults (`true`) and closed TOML schema validation.
- Enforced disabled-provider policy for:
  - run creation admission
  - preflight reports
  - launch-time rechecks before sandbox setup
- Policy uses the effective provider after dry-run coercion to local.
- Installer now writes all three provider policy tables with `enabled = true`.
- Updated OpenAPI schema, Rust API replacements/tests, regenerated TypeScript API client models, and docs.

Verification run:
- `cargo test -p fabro-config server_sandbox --quiet`
- `cargo test -p fabro-install write_sandbox_settings_records --quiet`
- `cargo test -p fabro-api server_settings_json_matches_openapi_shape --quiet`
- `cargo nextest run -p fabro-server --features test-support sandbox_provider_policy`
- `cargo nextest run -p fabro-server --features test-support --test it runs::create_run_rejects_disabled_sandbox_provider`
- `cargo nextest run -p fabro-server --features test-support --test it runs::preflight_reports_disabled_sandbox_provider`
- `cargo nextest run -p fabro-server --features test-support --test it install::token_install_finish_persists_settings_env_and_vault`
- `cargo nextest run -p fabro-server --features test-support --test it install::daytona_install_finish_writes_settings_and_vault_secret`
- `cargo build -p fabro-api`
- `cd lib/packages/fabro-api-client && bun run generate`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `cd lib/packages/fabro-api-client && bun run typecheck`
- `cd apps/fabro-web && bun run typecheck`

Working tree is clean.