## Summary

Reviewed the implementation with three parallel agents (code reuse, code quality, efficiency). Aggregated findings and applied the following fixes:

**Shared cron parsing** (Agent 1/3, high value)
- Added `fabro_automation::parse_schedule_expression` backed by a `LazyLock<CronParser>` and re-exported it. `validate_triggers` and the scheduler's `next_occurrence` now share one parser construction site, eliminating drift risk and the per-call parser build.

**`Automation::enabled_schedule_triggers()` helper** (Agent 1)
- Mirrors the existing `enabled_api_trigger`. The scheduler's nested `filter`/`filter_map` collapses to a single iterator call and keeps the "automation disabled ⇒ no triggers" invariant in one place.

**Shared `AppState::automation_temp_root()`** (Agent 1)
- Replaces the duplicated `Storage::new(...).scratch_dir().join("automations")` block in `handler/automations.rs` and the scheduler. `handler/automations.rs` no longer needs to import `Storage`.

**Deterministic ordering in `take_due`** (Agent 2)
- `HashMap` iteration was leaking non-determinism into spawn order and log output. Now sorted by `(automation_id, trigger_id)`.

**Unified `tick(...)` entry point** (Agent 2)
- Single method does `reconcile` + `take_due`. The production loop and the test helper both call it, so they can't drift.

**Span-based logging** (Agent 2)
- Production fires run inside `info_span!("automation_run", automation_id, trigger_id)`. Removed the repeated `automation_id`/`trigger_id` fields from 4 individual `warn!`/`info!` calls.

**Removed redundant `Box::pin`** (Agent 1/2)
- The `Box::pin` inside `tokio::spawn` is gone (spawn already boxes). `Instrument` is used for the span attachment. `Box::pin` is retained on `create_run_from_manifest` and inside the test helper — verified by clippy `large_futures` that both are genuinely needed, with comments explaining why.

**Removed misleading test assertion** (Agent 2)
- `enabled_api_trigger().is_none()` assert was testing `Automation`, not the scheduler. Renamed the test to focus on the actual scheduler behavior.

**Skipped (judged not worth it):**
- Caching parsed `Cron` on each cursor (small win, added complexity)
- In-place reconcile (small win at typical scale)
- Restructuring `AutomationRef` to use typed `AutomationId`/`AutomationTriggerId` (out of scope — the type is OpenAPI-generated)
- Sharing the materialize→create→start pipeline between `handler/automations.rs` and the scheduler (the actor and headers differ; abstraction would be premature with only two call sites)

**Verification (all green):**
- `cargo nextest run -p fabro-automation` — 10/10
- `cargo nextest run -p fabro-server automation_scheduler` — 12/12
- `cargo nextest run -p fabro-server automation_materializer automation_metadata` — 13/13
- `cargo nextest run -p fabro-server --features test-support api::automations` — 27/27
- `cargo +nightly-2026-04-14 fmt --check --all` — clean
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean