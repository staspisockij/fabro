All verification steps pass. Summary:

The plan was already fully implemented in the working tree:

1. **`lib/crates/fabro-model/src/billing.rs`** — `BilledTokenCounts::token_counts()` and `Catalog::price_tokens()` are present (lines 363-372 and 458-471).

2. **`lib/crates/fabro-workflow/src/billing_rollup.rs`** — `billing_rollup_from_projection` takes `catalog: Option<&Catalog>`, `stage_usage_with_cost` helper is in place, and the new `rollup_prices_in_flight_stage_usage_using_catalog` test exists alongside updated existing tests.

3. **Call sites** — All updated:
   - `fabro-server/src/server/handler/billing.rs:82-83` — passes `Some(&catalog)` from `state.catalog()`.
   - `fabro-server/src/server.rs:3337,3622` — aggregate-billing sites pass `None`.
   - `fabro-workflow/src/pipeline/finalize.rs:85,442,558,983` — all four sites pass `None`.

Verification (all green):
- ✅ `cargo nextest run -p fabro-workflow billing_rollup` — 4 tests pass (incl. new in-flight pricing test)
- ✅ `cargo nextest run -p fabro-server billing` — 7 tests pass
- ✅ `cargo build --workspace`
- ✅ `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`