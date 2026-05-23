Implemented live `Run.timing` for in-flight runs.

Summary:
- Added `RunProjection::live_run_timing(now)` in `fabro-types`.
  - Returns `None` before `run.started`.
  - Derives live wall time from `now - start.start_time`, saturating at 0.
  - Sums completed-stage inference/tool time and builds via `RunTiming::new`.
  - Includes the documented limitation that active timing only advances when stages complete.
- Kept `build_summary` unchanged and deterministic.
- Updated `RunProjectionCache::list` and `get_summary` to accept `now` and overlay live timing only on cloned returned summaries when cached `summary.timing` is `None`.
- Propagated `now` through `fabro-store` list/summary accessors and all affected workspace call sites.
- Updated server run summary/list/board handlers to pass `Utc::now()`.
- Added tests:
  - `live_run_timing_returns_none_before_run_starts`
  - `live_run_timing_derives_wall_and_completed_stage_active_for_in_flight_run`
  - `live_run_timing_matches_conclusion_timing_at_conclusion_moment`
  - `cached_summary_overlays_live_timing_without_mutating_cached_snapshot`

TDD/validation:
- Red phase: `cargo nextest run -p fabro-store live_run_timing` initially failed with missing `live_run_timing`.
- Green/final checks:
  - `cargo nextest run -p fabro-store live_run_timing`
  - `cargo nextest run -p fabro-store cached_summary_overlays_live_timing`
  - `cargo check -q --workspace`
  - `cargo +nightly-2026-04-14 fmt --check --all`
  - `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings`

All passed.