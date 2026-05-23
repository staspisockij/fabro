Reviewed the branch changes and made one cleanup fix:

- Restored serialized `McpServerProjection.tool_count` across:
  - `fabro-types`
  - reducer upserts in `fabro-store`
  - OpenAPI schema
  - API parity tests
  - generated TS client model

This keeps the endpoint aligned with the intended projection shape and preserves `AgentMcpReadyProps.tool_count` even when the emitted tool summaries are empty/truncated.

Validation run:

- `cargo check -q -p fabro-types -p fabro-store -p fabro-api`
- `cargo nextest run -p fabro-store -p fabro-api`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cd lib/packages/fabro-api-client && bun run typecheck`

All passed.