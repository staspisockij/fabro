Goal: # Event-Sourced Agent Todo Tools

Date: 2026-05-22

## Summary

Add one shared todo/task engine behind two model-native tool surfaces:

- OpenAI models get Codex-compatible `update_plan`.
- Anthropic models get Claude-compatible `TaskCreate`, `TaskUpdate`, and `TaskList`.
- All mutations persist as individual `todo.created`, `todo.updated`, and `todo.deleted` run events.
- `RunProjection` maintains current todo state by replaying those events.

Scoping matches latest upstream behavior:

- OpenAI plan todos are scoped to the emitting session: `openai_plan:<session_id>`.
- Anthropic task todos are scoped to the root agent session: `anthropic_tasks:<root_session_id>`, shared by subagents.

## Key Changes

- Add shared todo domain types in `fabro-types`: `TodoStatus`, `TodoListKind`, `TodoProjection`, `TodoListProjection`, and `todos_by_list` on `RunProjection`.
- Add run event bodies for `todo.created`, `todo.updated`, and `todo.deleted`; map them through Fabro's typed event pipeline and replay them in `fabro-store`'s `RunProjectionReducer`.
- Extend `fabro-agent` tool runtime context with `session_id`, `root_session_id`, `tool_call_id`, and a narrow agent-event emitter so tools can emit todo mutation events with correct session metadata.
- Add a shared `TodoRuntime` in `fabro-agent` that owns the in-memory current todo projection for active sessions and emits individual mutation events.
- Register `update_plan` only in `OpenAiProfile`. It accepts Codex's schema, diffs incoming steps by exact `step`, and emits create/update/delete events so the projected list equals the submitted plan.
- Register `TaskCreate`, `TaskUpdate`, and `TaskList` only in `AnthropicProfile`. Use generated numeric task IDs per Anthropic task list, preserve Claude field names and result text, and support status `deleted` as a delete operation.
- Thread root session identity through parent and child sessions. Root sessions use their own ID as `root_session_id`; subagent sessions inherit the parent root ID while retaining their own `session_id`.
- Update OpenAPI `RunProjection` schema and regenerate Rust/TypeScript API types. Existing run-state and run-events APIs remain the exposure point; no new HTTP route is required.
- Update web run-event invalidation so `todo.*` events refresh `getRunState` consumers and the run events list.

## Tool Semantics

### OpenAI `update_plan`

Input:

- `explanation?: string`
- `plan: [{ step: string, status: "pending" | "in_progress" | "completed" }]`

Behavior:

- Return Codex-compatible success text: `Plan updated`.
- Scope todos to `openai_plan:<session_id>`.
- Use exact `step` string as identity within that scope.
- Reject duplicate `step` strings with a model-visible tool error.
- New step string emits `todo.created`.
- Existing step with changed status or order emits `todo.updated`.
- Omitted previous step emits `todo.deleted`.
- Todo ID is deterministic from `list_id + step`.

### Anthropic `TaskCreate`

Input:

- `subject: string`
- `description: string`
- `activeForm?: string`
- `metadata?: object`

Behavior:

- Scope tasks to `anthropic_tasks:<root_session_id>`.
- Generate numeric task IDs per Anthropic task list.
- Emit `todo.created`.
- Return `Task #<id> created successfully: <subject>`.

### Anthropic `TaskUpdate`

Input:

- `taskId: string`
- `subject?: string`
- `description?: string`
- `activeForm?: string`
- `status?: "pending" | "in_progress" | "completed" | "deleted"`
- `owner?: string`
- `addBlocks?: string[]`
- `addBlockedBy?: string[]`
- `metadata?: object`

Behavior:

- `status: "deleted"` emits `todo.deleted`.
- Other changes emit `todo.updated`.
- Metadata merges into existing metadata; a `null` metadata value deletes that key.
- Missing task returns a non-error tool result: `Task not found`.

### Anthropic `TaskList`

Input:

```json
{}
```

Behavior:

- Reads the projected Anthropic task list for `anthropic_tasks:<root_session_id>`.
- Returns Claude-style task lines containing ID, status, subject, optional owner, and uncompleted blockers.
- Returns `No tasks found` when the list is empty.

## Test Plan

- Unit-test tool schemas and registration:
  - OpenAI profile includes `update_plan`; Anthropic profile does not.
  - Anthropic profile includes `TaskCreate`, `TaskUpdate`, `TaskList`; OpenAI profile does not.
- Unit-test OpenAI reconciliation:
  - create initial steps
  - update status and order
  - delete omitted steps
  - subagent session writes to a different OpenAI list than parent
- Unit-test Anthropic task behavior:
  - create, list, update, complete, and delete
  - metadata merge and `null` deletion
  - `addBlocks` and `addBlockedBy`
  - parent and subagent share the same Anthropic task list
- Unit-test event serialization and conversion:
  - `todo.created`, `todo.updated`, `todo.deleted` have stable event names and properties
  - envelope includes emitting `session_id`, `parent_session_id` when present, and `tool_call_id`
- Unit-test `RunProjection` replay:
  - replaying todo events reconstructs current lists
  - deleted todos are absent from current projection
  - multiple lists in one run remain isolated
- API and web checks:
  - `cargo build -p fabro-api`
  - `cargo nextest run -p fabro-server`
  - `cd lib/packages/fabro-api-client && bun run generate`
  - `cd apps/fabro-web && bun test && bun run typecheck`

## Assumptions

- Ignore deprecated Claude `TodoWrite`; implement only latest Anthropic Task tools.
- Duplicate OpenAI `step` strings are rejected with a model-visible tool error because step text is the identity.
- Todo events are individual mutations only; no plan-replace event is added.
- Todo state is exposed through existing run projection and event APIs, not a new endpoint.


## Completed stages
- **toolchain**: succeeded
  - Script: `command -v cargo >/dev/null || { curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && sudo ln -sf $HOME/.cargo/bin/* /usr/local/bin/; }; cargo --version 2>&1`
  - Output:
    ```
    cargo 1.95.0 (f2d3ce0bd 2026-03-21)
    ```
- **preflight_compile**: succeeded
  - Script: `cargo check -q --workspace 2>&1`
  - Output: (empty)
- **preflight_lint**: succeeded
  - Script: `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings 2>&1`
  - Output: (empty)


Read the plan file referenced in the goal and implement every step. Make all the code changes described in the plan. Use red/green TDD.