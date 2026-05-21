All clean. Here's the summary:

## Summary

Three review agents (reuse, quality, efficiency) ran in parallel against the diff. Aggregated findings:

### Fixed

1. **Renamed `BilledTokenCounts::token_counts()` → `to_token_counts()`** (`fabro-model/src/billing.rs`)
   - Quality finding: original name read like a field accessor and hid the fact that the conversion is lossy (drops `total_tokens` and `total_usd_micros`). The `to_` prefix is the established Rust convention for lossy conversions.

2. **Moved pricing logic into `BilledTokenCounts::ensure_priced(catalog, model)`** (`fabro-model/src/billing.rs` + `fabro-workflow/src/billing_rollup.rs`)
   - Quality finding: the previous `stage_usage_with_cost` helper cloned `BilledTokenCounts` across a crate boundary and directly poked the private `total_usd_micros` field, leaking knowledge of how to price a `BilledTokenCounts` out of `fabro-model`. The new method encapsulates that logic next to `add_billed_usage` / `replace_with_billed_usage`, and the rollup-side helper is now a 3-line wrapper.

### Considered and skipped

- **Reuse #1 (refactor `billed_model_usage_from_llm` to use `price_tokens`)** — the "duplicated" pricing tail is 3 lines and the surrounding error-vs-option shapes don't compose cleanly. Refactoring adds more indirection than it removes.
- **`Option<&Catalog>` parameter sprawl** — 6 of 7 call sites pass `None`, but splitting into two functions doubles the public surface for marginal benefit; the single signature is fine.
- **`pricing_for` memoization across stages** — real but minor (a few `String` clones per stage on a polled endpoint). Worth doing if the path ever shows up in profiles; not justified at the cost of HashMap setup for this fix.
- **`Cow::Borrowed` for the usage clone** — `BilledTokenCounts` is ~64 bytes of POD; no heap allocation.
- **Bare `i64` return from `price_tokens`** — matches the established `total_usd_micros: Option<i64>` convention used throughout the codebase.

### Verified

- `cargo nextest run -p fabro-workflow billing_rollup` — 4/4 pass (including the new in-flight pricing test).
- `cargo nextest run -p fabro-model billed_token_counts` — 5/5 pass.
- `cargo nextest run -p fabro-server billing` — 7/7 pass.
- `cargo build --workspace` — clean.
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean.
- `cargo +nightly-2026-04-14 fmt --check --all` — clean.