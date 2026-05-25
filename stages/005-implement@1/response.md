Implemented the full Secrets Rationalization plan and committed the remaining work.

Summary of changes:
- Added/kept shared secret scope registry and bootstrap-secret rejection in `/secrets`.
- Replaced server optional secret resolution with vault-only lookups for:
  - LLM provider credentials
  - GitHub token/App private key/client secret/webhook secret
  - Slack tokens
  - Daytona API key
  - Brave Search API key
- Kept bootstrap secrets on `process env -> server.env` via `ServerSecrets`.
- Added startup vault loading so GitHub auth validates `GITHUB_APP_CLIENT_SECRET` from the vault.
- Changed Brave Search so the tool no longer reads process env internally; runtime/CLI pass `ToolSecrets` explicitly.
- Updated install persistence so GitHub App secrets are written to vault, stale optional `server.env` keys are removed, and strategy switches clean up stale vault secrets.
- Updated docs/public/internal guidance to document the new bootstrap-vs-vault model.
- Working tree is clean.

Commits created:
- `75d77fb3a refactor: resolve optional server secrets from vault only`
- `1502c8d97 fix: persist optional install secrets in vault`
- `c14d44fb5 docs: document vault-only optional secrets`

Existing commits from earlier task progress:
- `097fb172c refactor: classify server secret scopes`
- `2e612af86 fix: reject bootstrap secrets in vault API`

Verification run:
- `cargo check -q --workspace`
- `cargo nextest run -p fabro-static`
- `cargo nextest run -p fabro-auth`
- `cargo nextest run -p fabro-vault`
- `cargo nextest run -p fabro-agent web_search`
- `cargo nextest run -p fabro-agent brave_search`
- `cargo nextest run -p fabro-slack`
- `cargo nextest run -p fabro-server`
- `cargo nextest run -p fabro-cli install --no-fail-fast`
- `cargo nextest run -p fabro-cli server_start --no-fail-fast`
- `cargo nextest run -p fabro-server github --no-fail-fast`
- `cargo nextest run -p fabro-workflow build_registry_accepts_vault_only_llm_provider`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`

Pattern checks:
- No `vault_or_env` / `vault_or_env_pub` server-runtime helper remains.
- No server-runtime `GH_TOKEN` fallback remains.
- Remaining `GH_TOKEN` hits are non-server-runtime/test/static/CLI legacy lookup references.