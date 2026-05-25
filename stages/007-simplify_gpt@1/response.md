Reviewed the provider probe endpoint changes against `origin/main` for reuse, quality, and efficiency. I didn’t find any cleanup issues that warranted code changes, so the working tree remains clean.

Verification run:

- `cargo nextest run -p fabro-server test_providers` — passed, 7/7
- `cargo nextest run -p fabro-server diagnostics` — passed, 14/14
- `cargo build -p fabro-api` — passed
- `cd apps/fabro-web && bun run typecheck` — passed

`git status --short` is clean.