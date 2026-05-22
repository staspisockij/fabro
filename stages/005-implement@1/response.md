The implementation is complete. Summary of changes:

## Summary

**Domain types in `fabro-types`** (new `todo.rs`):
- `TodoStatus` (pending/in_progress/completed/deleted), `TodoListKind` (openai_plan/anthropic_tasks), `TodoProjection`, `TodoListProjection` with `upsert`/`remove`/`get`.
- Added `todos_by_list: BTreeMap<String, TodoListProjection>` to `RunProjection`.

**Run-event bodies** (new `run_event/todo.rs`):
- `TodoCreatedProps`, `TodoUpdatedProps`, `TodoDeletedProps` with full field-level patch semantics for updates.
- Wired into `EventBody` enum, `event_name()` match, and `is_known_event_name`.

**Reducer in `fabro-store`**:
- Three new arms in `RunProjectionReducer::apply_event` that replay `todo.created`/`updated`/`deleted` into `todos_by_list`. Supports metadata patches with `null` deletion and `addBlocks`/`addBlockedBy` deduplication.

**Agent runtime (`fabro-agent`)**:
- `AgentEvent::TodoCreated/Updated/Deleted` variants with full payloads.
- Extended `ToolContext` with `session_id`, `root_session_id`, `tool_call_id`, and an `AgentEventEmitter` trait.
- New `TodoRuntime` (`todo_runtime.rs`) maintaining in-memory projection per `list_id`, emitting one event per mutation.
- New `update_plan` (OpenAI), `TaskCreate`/`TaskUpdate`/`TaskList` (Anthropic) tools in `todo_tools.rs`, registered only in their respective profiles.
- `Session.root_session_id` field with accessor + setter; `spawn_agent` tool inherits the parent's root into subagent sessions.
- `Emitter::emit_with_parent` + `SessionBoundEmitter` plug into `tool_execution::execute_one_tool`, populating `ToolContext` with the live session metadata.

**Conversion in `fabro-workflow`**:
- Added arms in `event/convert.rs` and `event/names.rs` to translate `AgentEvent::Todo*` into `EventBody::Todo*`.

**OpenAPI + TypeScript**:
- Extended `docs/public/api-reference/fabro-api.yaml` with `todos_by_list`, `TodoStatus`, `TodoListKind`, `TodoProjection`, `TodoListProjection` schemas.
- Added corresponding TS models in `lib/packages/fabro-api-client/src/models/` and updated `RunProjection` model.

**Web (`apps/fabro-web`)**:
- Added `TODO_EVENTS` set in `run-events.ts`; `todo.*` events now invalidate `queryKeys.runs.state(id)` and `queryKeys.runs.events(id, 1000)`, plus the current stage's events.

**Tests added** (all passing):
- 4 unit tests in `fabro-types::todo` (`list_id_is_prefix_colon_session`, ordering, upsert/remove).
- 4 event-serde tests in `fabro-types::run_event` (event names known, envelope metadata, round-trip create/delete).
- 4 reducer tests in `fabro-store` (replay reconstructs list, deletes absent, multi-list isolation, metadata patch + null).
- 3 `TodoRuntime` tests (create/update/delete cycle, deleted-status emits delete, missing-todo returns false).
- 11 tool tests in `todo_tools` (`update_plan`: create initial / status+order / delete omitted / reject duplicate / subagent different list; `TaskCreate`/`TaskUpdate`/`TaskList`: numeric IDs, cycle, metadata merge + null, addBlocks dedupe, empty list, missing taskId, parent+subagent share Anthropic list).
- Profile tests updated to assert exact tool registration (OpenAI has `update_plan`, Anthropic has the three Task tools, neither bleeds).
- 2 web tests for `queryKeysForRunEvent` on `todo.*` events.

**Verified clean**:
- `cargo +nightly-2026-04-14 fmt --check --all` — clean.
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` — clean.
- `cargo nextest run` across `fabro-types`, `fabro-store`, `fabro-workflow`, `fabro-agent`, `fabro-server`, `fabro-api`: 2638 passed (3 pre-existing graphviz-env failures unrelated to this change).
- `cargo build -p fabro-api` — clean.
- `cd apps/fabro-web && bun run typecheck` — clean. `bun test`: 421 pass (7 pre-existing failures unrelated to this change).