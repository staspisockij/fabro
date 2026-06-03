## Summary

Three review agents (reuse, quality, efficiency) inspected the two-commit change (Anonymous principal removal + total run provenance). Applied fixes:

**Efficiency**
- `apps/fabro-web/app/components/runs-list/run-table-row.tsx` — `principalDisplay(run.createdBy)` was being computed on every row render even when the `created_by` column was hidden. Moved the call inside the `show("created_by") &&` guard.

**Quality**
- `lib/crates/fabro-server/src/principal_middleware.rs` — `principal_without_log_unused_fields` had an awkward `Option<&Principal> → Option<Principal>` signature with redundant `None`/`Some(clone)` arms. Simplified to `&Principal → Principal` and let the caller `.as_ref().map(...)`.
- `apps/fabro-web/app/components/run-summary-panel.test.tsx` — Test "shows unavailable copy for missing run fields after load" asserted "Created by" rendered "Ttest", which is not an unavailable copy. Split into a separate `renders creator from run.created_by` test.
- `apps/fabro-web/app/components/run-summary-panel.tsx` — Removed dead `created ? ... : <EmptyValue/>` branch that suggested `created_by` could still be null after a run loads; now skeleton while loading, principal display once loaded.

**Reuse**
- `lib/crates/fabro-types/Cargo.toml` — Added self dev-dep `fabro-types = { path = ".", features = ["test-support"] }` to make the new `test_support::test_run_provenance()` available to integration tests.
- `lib/crates/fabro-types/tests/{run_event_serde,run_spec_serde,run_spec_methods}.rs` — Deleted three byte-identical local `test_run_provenance()` copies and the now-unused `Principal`/`RunProvenance`/`SystemActorKind` imports; all three now call the canonical helper.

**Skipped (false positive or out of scope)**
- Demo principal `LazyLock` (already idiomatic; clone is unavoidable given owned `Run.created_by`).
- Gate-helper boilerplate consolidation in `principal_middleware.rs` (pre-existing pattern, out of scope).
- `fabro-workflow/src/test_support.rs` inline `RunProvenance` literal (its `test_support` module is not feature-gated, so it cannot depend on `fabro-types`'s feature-gated helper without a broader refactor).
- `cmd/inspect.rs` inline JSON principal (low value).

**Verification**
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` ✅
- `cargo nextest run -p fabro-types -p fabro-server` (1036 + server tests passed) ✅
- `cd apps/fabro-web && bun run typecheck` ✅
- `cd apps/fabro-web && bun test` (509 passed) ✅