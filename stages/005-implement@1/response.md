Implemented the fail-soft batch delete runs API end-to-end.

Summary:
- Added `POST /api/v1/runs/delete` to OpenAPI with `BatchDeleteRuns*` schemas.
- Regenerated Rust API types via `cargo build -p fabro-api`.
- Regenerated TypeScript Axios client with `batchDeleteRuns` and new models.
- Added server batch delete route/handler with:
  - ordered per-run results
  - `deleted`, `already_absent`, `sandbox_preserved`, `conflict`, `error`
  - request-level validation before mutation
  - user auth requirement
- Refactored shared delete internals to return structured `ApiError` and `DeleteRunOutcome`.
- Preserved existing single-delete behavior while enabling batch per-item errors.
- Added `deleteRuns` web helper and tests.
- No bulk delete UI was added.

Red/green TDD:
- Initial `cargo nextest run -p fabro-server batch_delete` failed as expected with missing route behavior.
- After implementation, the batch delete tests pass.

Verification run:
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo nextest run -p fabro-server batch_delete delete_run prune_runs`
- `cargo build -p fabro-api`
- `cd apps/fabro-web && bun test app/lib/run-actions.test.ts`
- `cd apps/fabro-web && bun run typecheck`
- Extra focused lint: `cargo +nightly-2026-04-14 clippy -q -p fabro-server --all-targets -- -D warnings`

All passed.