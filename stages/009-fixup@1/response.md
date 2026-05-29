All verify steps now pass:

- `cargo +nightly-2026-04-14 fmt --check --all` ✓
- `cargo dev docs refresh` / `check` ✓
- No forbidden auth patterns ✓
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` ✓
- `cargo nextest run --workspace --status-level slow --profile ci` — 6474 passed, 0 failed ✓
- `bun install --frozen-lockfile` ✓
- `apps/fabro-web` typecheck + tests (503 pass) ✓
- `lib/packages/fabro-api-client` typecheck ✓
- `cargo dev build -- -p fabro-cli --release` ✓

The previous verify failure was classified as `transient_infra` ("failed to spawn script"), and there were no actual code defects to fix. The working tree was already clean and re-running the full verification pipeline succeeded end-to-end with no source changes needed.