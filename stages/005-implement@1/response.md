Implemented batch run archive/unarchive end-to-end.

Summary:
- Added OpenAPI endpoints:
  - `POST /api/v1/runs/archive`
  - `POST /api/v1/runs/unarchive`
- Added batch lifecycle schemas and regenerated Rust/TypeScript API clients.
- Implemented server batch handlers with:
  - `RequiredUser` auth only
  - pre-mutation validation for empty, >250, duplicate, and invalid IDs
  - sequential fail-soft processing
  - ordered per-run results and summary counts
  - existing `operations::archive` / `operations::unarchive` behavior and events
- Added server tests covering:
  - archive/unarchive visibility changes
  - mixed success/conflict/not_found results
  - idempotent archive/unarchive outcomes
  - invalid request rejection before mutation
  - unauthenticated and worker-token rejection
- Added web helpers:
  - `archiveRuns(runIds)`
  - `unarchiveRuns(runIds)`
- Updated runs list bulk actions and board “Archive all” to use one batch request per action.
- Preserved cache invalidation/toast behavior, with partial-success batch summaries.
- Added frontend helper and route-summary tests.

Validation run:
- `cargo build -q -p fabro-api` ✅
- `cargo check -q --workspace` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings` ✅
- `cargo nextest run -p fabro-api` ✅
- Targeted `fabro-server` batch/single archive tests ✅
- `cd lib/packages/fabro-api-client && bun run generate` ✅
- `cd lib/packages/fabro-api-client && bun run typecheck` ✅
- `cd apps/fabro-web && bun run typecheck` ✅
- `cd apps/fabro-web && bun run test` ✅

Note:
- Full `cargo nextest run -p fabro-server` still fails on existing/unrelated `server::tests::get_graph_returns_svg`; it invokes the test binary as the graph render subprocess and gets `running 0 tests...` instead of SVG. The new batch lifecycle tests pass.