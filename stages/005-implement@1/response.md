Implemented the Agent Compaction API Usage Baseline plan.

Changes made:
- Added active context estimation in `lib/crates/fabro-agent/src/compaction.rs`
  - Uses newest assistant turn with `usage.total_tokens() > 0` as baseline.
  - Adds local estimates only for turns after that assistant response.
  - Falls back to existing whole-history `chars / 4` local estimate when no usable assistant usage exists.
  - Adds `estimate_method` to context-window warning details.
  - Uses the improved estimate for `CompactionStarted`.
  - Prevents no-op compaction from emitting `CompactionStarted`.
- Updated `lib/crates/fabro-agent/src/history.rs`
  - `History::compact()` now resets preserved assistant `usage` to `TokenCounts::default()`.
  - Assistant content, tool calls, response IDs, and non-stripped provider parts remain preserved.
- Added/updated tests in:
  - `compaction.rs`
  - `history.rs`
  - `session.rs`
- Confirmed no `llm_client.count_input_tokens()` / provider token-count API calls were added.

Verification:
- Red phase confirmed initially with failing new compaction tests.
- Passed:
  - `cargo nextest run -p fabro-agent compaction`
  - `cargo nextest run -p fabro-agent history`
  - `cargo nextest run -p fabro-agent session`
  - `cargo nextest run -p fabro-agent`
  - `cargo +nightly-2026-04-14 fmt --check --all`
  - `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings`