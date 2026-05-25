## Summary

Three review agents flagged findings across reuse, quality, and efficiency. I fixed the high-value, contained ones and noted the rest.

**Fixed:**

1. **Triple-duplicated install secret lists** (all three agents flagged): The same 4-element "all GitHub install secrets" list and 3-element "GitHub App vault keys" list appeared verbatim in `fabro-server/src/install.rs`, `fabro-cli/src/commands/install.rs` (both `run_install_github_inner` and `run_install_inner`). Hoisted to `fabro_install::{GITHUB_INSTALL_SECRET_KEYS, GITHUB_APP_VAULT_KEYS}` and consumed from all three sites.

2. **Dead helper** `test_app_state_with_env_lookup_and_server_secret_env` in `fabro-server/src/test_support.rs` (no callers after the PR's tests.rs change). Deleted.

3. **Unused public surface** in `fabro-static::secret_registry`. `SecretScope`, `secret_scope`, and `is_optional_vault_secret` had no consumers outside the registry's own tests. Made them private; only `is_bootstrap_secret` remains exported.

4. **Test fixture gap from the implementation** — three tests still wrote optional secrets via `server.env`/`env_lookup` instead of vault (broken by the vault-only refactor):
   - `worker_auth.rs` `RunningGithubOnlyServer` — was writing `GITHUB_APP_CLIENT_SECRET` to server.env.
   - `auth_harness.rs` — was passing `GITHUB_APP_CLIENT_SECRET` via `server_secret_env`.
   - `openapi_conformance.rs` `github_webhook_spec_route_is_routable_when_webhook_secret_is_present` — same shape.
   - `helpers.rs` `test_app_with_mock_anthropic` — was supplying `ANTHROPIC_API_KEY` via env_lookup; LLM creds are now vault-only.
   
   Added `TestAppStateBuilder::vault_entries(...)` to seed vault contents and migrated all four sites. These tests would have been silently red against the new behavior.

**Noted but skipped:**

- **`AppState::vault_secret` swallows `try_read()` failure as `None`** (MED-1). Real behavior concern under contention but the `try_read().ok()` pattern is pre-existing (was in `vault_or_env` on origin); fixing it cascades through many sync helpers (`session_key`, `github_credentials`, `worker_command`). Out of scope for this review.
- **`AppStateConfig.preloaded_vault: Option<Vault>`** transition wart — bigger refactor.
- **`ToolSecrets` one-field struct** — over-engineered but cost-to-rip exceeds benefit.
- **Composite auth lookup hardcodes `GITHUB_APP_CLIENT_SECRET`** — only one secret crosses scopes today; will revisit if a second does.
- **Multiple `vault_secret` calls per request** could share one guard — LOW severity, current behavior is correct.
- **`run_responses_include_ask_fabro_affordance`** test failure is pre-existing on the implement commit; unrelated.

**Verification:** `cargo +nightly-2026-04-14 fmt --check`, `clippy -- -D warnings`, and the focused test set (`fabro-static`, `fabro-install`, `fabro-server`, `fabro-cli`, `fabro-auth`, `fabro-agent`, `fabro-slack`) all green except the pre-existing `ask_fabro_affordance` failure.