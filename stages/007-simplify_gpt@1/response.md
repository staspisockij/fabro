Implemented review cleanup and validation.

What I fixed:
- Restored the durable `provider_profile` contract to `String` for:
  - `AgentMemoryLoadedProps`
  - `AgentSkillsDiscoveredProps`
- Added explicit `loaded_bytes` to `MemoryDocument` instead of deriving it ad hoc from `content.len()`.
- Reduced `fabro-agent` coupling to durable API props by adding internal agent summary types:
  - `MemoryFileSummary`
  - `SkillSummary`
  - `SkillActivationSource`
  - `McpToolSummary`
- Restored explicit internal `tool_count` on `AgentEvent::McpServerReady`, while still carrying names-only tool summaries.
- Updated workflow conversion to map internal agent summary types into `fabro-types` event props.
- Updated tests to match the cleaned-up internal/durable boundaries.
- Ran rustfmt.

Validation passed:
- `cargo nextest run -p fabro-agent -p fabro-workflow -p fabro-types -p fabro-mcp`
  - 1840 passed, 122 skipped
- `cargo +nightly-2026-04-14 fmt --all`
- `cargo +nightly-2026-04-14 clippy -q -p fabro-agent -p fabro-workflow -p fabro-types -p fabro-mcp --all-targets -- -D warnings`

Working tree now has cleanup modifications in 8 Rust files; no docs changes were needed during this review pass.