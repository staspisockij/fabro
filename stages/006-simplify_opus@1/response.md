All clean. Here's a summary of what was fixed based on the three reviews:

## Summary of cleanup applied

**`lib/crates/fabro-agent/src/compaction.rs`**
- Removed the no-longer-needed `pub fn estimate_token_count` (no external callers); tests updated to call `estimate_active_context_usage` directly.
- Replaced the hand-rolled `ContextEstimateMethod::as_str()` with `#[derive(strum::IntoStaticStr)] #[strum(serialize_all = "snake_case")]` per repo convention in CLAUDE.md.
- Split `estimate_local_token_count(system_prompt, turns)` into two single-purpose helpers (`estimate_turns_local_tokens`, `estimate_system_prompt_local_tokens`) to remove the `""` sentinel call from the baseline+delta path.
- Replaced the literal `4` in `summary_token_estimate = summary_content.len() / 4` with `APPROX_CHARS_PER_TOKEN`.
- Made `check_context_usage` return `Option<ContextEstimate>` and `compact_context` accept the pre-computed estimate, eliminating a duplicate full estimate scan per actual compaction. Both fns are now `pub(crate)` since they have no external callers. Dropped the redundant `system_prompt` parameter from `compact_context`.
- Tightened visibility on `ContextEstimate` and `ContextEstimateMethod` to `pub(crate)`.

**`lib/crates/fabro-agent/src/history.rs`**
- Moved the free `invalidate_assistant_usage` function into `impl History` as a private `invalidate_preserved_usage` method.
- Added a doc comment on `History::compact` explaining the usage-invalidation invariant.

**`lib/crates/fabro-agent/src/session.rs`**
- Rewired `compact_if_needed` to consume the `Option<ContextEstimate>` from `check_context_usage` and pass it through.
- Renamed misleading test helper `response_with_total_usage` → `response_with_input_tokens` (it only set `input_tokens`, never the other usage fields).

**`lib/crates/fabro-agent/Cargo.toml`**
- Added `strum.workspace = true` (workspace dep) to support the derive.

## Findings skipped

- **Test builder for `Message::Assistant`** (Quality #3): broader scope than just the diff and only marginal cleanup.
- **Counting-writer for JSON length** (Efficiency #3): the hot-path concern is real but speculative without profiling; the prevailing pattern in fabro-agent uses `Value::to_string()`. Out of scope.
- **Extract `"context_window"` / `"estimate_method"` JSON-key constants** (Quality #5): pre-existing pattern beyond this diff.
- **Reshape `latest_assistant_usage_baseline` to return `(tokens, &[Message])`** (Quality #4): cosmetic; current `+ 1` indexing is local and clear.
- **`APPROX_CHARS_PER_TOKEN` in `history.rs` `extract_recent_user_messages`** (Reuse #1): out of scope — that code is not part of the change.

Verification: `cargo nextest run -p fabro-agent` → 447/447 pass; `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` → clean; `cargo +nightly-2026-04-14 fmt --check --all` → clean.