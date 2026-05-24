All clean. Summary:

The verify failure was caused by two snapshot tests in `lib/crates/fabro-cli/src/commands/run/run_progress/mod.rs` that hardcoded `gpt-5-mini` and expected a `$0.00` cost segment. Upstream `main` (commit 4ad9827b "Remove retired OpenAI catalog models") removed `gpt-5-mini` from the catalog, so `pricing.bill(...)` now returns `None`, the renderer omits the cost segment, and the snapshots no longer matched.

Fix: updated the two inline snapshots to reflect the new rendering (no cost section):
- `plain_default_stage_snapshot`: `    ✓ Plan  $0.00   5s` → `    ✓ Plan  5s`
- `plain_verbose_snapshot`: `✓ Code  $0.00   5s  (1 turns, 0 tools, 1.5k toks)` → `✓ Code  5s  (1 turns, 0 tools, 1.5k toks)`

Verified locally:
- `cargo nextest run --workspace --profile ci` — 6331 passed, 181 skipped
- `cargo +nightly-2026-04-14 fmt --check --all` — clean
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean