Implemented review cleanup on top of the billing cost-on-read changes.

What changed:
- Removed `BilledTokenCounts::ensure_priced`, which was an extra thin helper only used by rollup code.
- Renamed `to_token_counts()` to `token_counts()` to match the requested API and nearby accessor style.
- Updated `billing_rollup` pricing helper to avoid cloning stage usage unless a missing cost can actually be priced:
  - borrows existing usage for finalized/already-priced/no-catalog/no-model/unpriceable cases
  - only clones when setting a computed `total_usd_micros`

Review outcome:
- The parallel review agents did not return actionable findings.
- I applied the above cleanup for reduced abstraction and less per-read work.

Verification passed:
- `cargo nextest run -p fabro-workflow billing_rollup`
- `cargo nextest run -p fabro-server billing`
- `cargo +nightly-2026-04-14 clippy -q -p fabro-model -p fabro-workflow -p fabro-server --all-targets -- -D warnings`

Current working tree has modifications in:
- `lib/crates/fabro-model/src/billing.rs`
- `lib/crates/fabro-workflow/src/billing_rollup.rs`