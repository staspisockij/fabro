All verification steps now pass. Let me summarize the outcome:

The verify step had failed at `git merge --no-edit --no-stat origin/main` because the repo's refspec only fetched `feat/settings-environments-crud`, so `git fetch origin main` only updated `FETCH_HEAD` and `origin/main` didn't exist as a remote-tracking ref.

I fixed this by explicitly fetching into the remote-tracking ref:
- `git fetch origin main:refs/remotes/origin/main`
- `git merge --no-edit --no-stat origin/main` — merged cleanly (auto-merging `lifecycle.rs` and `server/tests.rs`)

Then ran the remaining verify steps end-to-end:
- `cargo +nightly-2026-04-14 fmt --all` — no diff
- `cargo dev docs refresh` + `fmt --check --all` — clean
- Forbidden-token `rg` sweep — no hits
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean
- `cargo nextest run --workspace --status-level slow --profile ci` — **6494 passed, 181 skipped, 0 failed**
- `cargo dev docs check` — up to date
- `bun install --frozen-lockfile` — no changes
- `cd apps/fabro-web && bun run typecheck` — clean
- `cd apps/fabro-web && bun run test` — **508 pass, 0 fail**
- `cd lib/packages/fabro-api-client && bun run typecheck` — clean
- `cargo dev build -- -p fabro-cli --release` — finished `release` profile in 4m 39s

One transient environment issue: the release build initially failed with "No space left on device" (target/debug was 17G on a 20G volume). Cleared `target/debug` (tests had already passed) and the release build succeeded.

No source code changes were needed — the only fix was the git fetch refspec for `origin/main`.