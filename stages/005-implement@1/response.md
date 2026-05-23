Implemented the per-stage agent state projection end-to-end.

Summary:
- Added `StageProjection` fields for:
  - `todos`
  - `subagents`
  - `skills`
  - `mcp_servers`
- Added colocated projection types/status enums in `fabro-types`.
- Removed run-level `RunProjection.todos_by_list`.
- Updated `fabro-store` reducer to project:
  - todo create/update/delete onto the owning stage
  - subagent lifecycle events
  - skill discovery/activation events
  - MCP ready/failed events
- Updated reducer tests using red/green TDD.
- Updated OpenAPI schema and Rust API replacements/parity tests.
- Regenerated TypeScript Axios client and removed the stale web comment.
- Verified `todos_by_list` is gone from code/schema/client references.

Validation run:
- `cargo build --workspace` ✅
- `cargo nextest run -p fabro-types -p fabro-store -p fabro-api -p fabro-server` ✅
- `cd lib/packages/fabro-api-client && bun run generate` ✅
- `cd lib/packages/fabro-api-client && bun run typecheck` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` ✅

Note: the server graph tests require the `fabro` binary to exist at `target/debug/fabro`, so I ran `cargo build --workspace` before the package nextest run.