Review/cleanup completed.

Changed:
- Fixed a stale test comment in `lib/crates/fabro-api/tests/provider_round_trip.rs`:
  - `four skip_serializing_if fields` → `five skip_serializing_if fields`

No code changes were needed for the TODO projection reducer; the implementation remains focused and matches the requested behavior.

Validated with:
- `cargo nextest run -p fabro-store todo_reducer` ✅
- `cargo test -p fabro-api --test provider_round_trip` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅

Working tree now has one local cleanup change:
- `M lib/crates/fabro-api/tests/provider_round_trip.rs`