Reviewed the changes with three parallel subagents for reuse, quality, and efficiency.

Fixed two small cleanup issues:

- Replaced raw GitHub App secret-name strings in `lib/crates/fabro-cli/src/commands/install.rs` with existing constants.
- Avoided repeated vault lock acquisition during Slack credential resolution in `lib/crates/fabro-server/src/server.rs` by taking one read guard and reusing it.

Validation run:

- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo nextest run -p fabro-server slack` ✅
- `cargo nextest run -p fabro-cli install` ✅

Working tree now has only those two cleanup modifications.