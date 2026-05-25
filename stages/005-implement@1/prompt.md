Goal: # Plan: Fix stage timing (inference + tool) reporting

## Context

The web UI's Duration popover shows `Active (inference + tools): 0ms` for every run, including agent-heavy runs that obviously did substantial LLM and tool work. Verified on `01KSE2PAVXD56N4TWNK4T5H5VA`: 10 stage.completed events and 1 run.failed event all carry `inference_time_ms: 0, tool_time_ms: 0`, even though stages like `implement@1` (94 min wall) and `simplify_opus@1` (29 min wall) were doing nothing but inference and tool calls.

Two independent bugs:

1. **No production handler ever populates `Outcome.timing`.** The plumbing from `Outcome.timing` → `NodeResult` (`lib/crates/fabro-core/src/executor.rs:30-37`) → `StageTiming` → `stage.completed` props → projection → billing rollup → run.completed/failed → UI is fully wired and shipped as of #343 (2026-05-21), but `AgentHandler::execute`, `PromptHandler::execute`, `CommandHandler::execute`, and `FanInHandler` all build `Outcome::success()` and never touch `.timing`. The executor falls back to zero, and every downstream consumer faithfully aggregates zero.

2. **`persist_terminal_engine_failure` and its sibling Drop-guard failure paths discard timing/billing entirely.** When the engine returns `Err` (e.g. `VisitLimitExceeded`, which is what killed the user's run), `lib/crates/fabro-workflow/src/operations/start.rs:284-308` builds a `Conclusion` via `build_conclusion_from_store`, then throws it away (`let _conclusion = ...`) and emits `WorkflowRunFailed` with `RunTiming::wall_only(...)` and `None` for billing/diff. The three Drop-guard paths (`start.rs:934`, `1001`, `1033`) do similar with `RunTiming::default()` and never even build a conclusion.

Goal: stage and run events carry real per-stage `inference_time_ms` + `tool_time_ms`; engine-failure terminal events preserve the conclusion's rolled-up timing and billing.

## Approach

### Part A — Capture inference + tool time in handlers (Bug 1)

**A1. `fabro-agent` — accumulate per-input timing in `Session`**

`lib/crates/fabro-agent/src/session.rs`

Add two `Duration` accumulators to `Session` (initialised to `Duration::ZERO`):
- `last_input_inference_duration`
- `last_input_tool_duration`

In `process_input_with_runtime` (line 1196), zero them at entry so each call's totals are independent.

In `run_single_input` (line 1254):
- Wrap the inference span: capture `Instant::now()` immediately before opening the stream at line 1391, and add `.elapsed()` to `last_input_inference_duration` once `response = Some(resp)` (line 1487-1490) OR when the loop exits with an error/cancellation. The whole `'streamattempts` loop counts as inference work — retries included.
- Wrap the tool span around `execute_tool_calls` at line 1705-1719: `Instant::now()` before, accumulate `.elapsed()` after `.await`.

Expose a getter:
```rust
pub fn last_input_timing(&self) -> SessionInputTiming { ... }
```
where `SessionInputTiming { pub inference: Duration, pub tool: Duration }` is a new tiny struct in `fabro-agent`.

**A2. `fabro-workflow` — thread timing through the backend boundary**

`lib/crates/fabro-workflow/src/handler/agent.rs`

Extend `CodergenResult::Text` with a `timing: fabro_types::StageTiming` field (wall is irrelevant — see note below). Update the few `CodergenResult::Text { ... }` constructions found by the explore agent to populate it; existing match-bindings only read `text`/`usage`/`files_touched` so they keep compiling with `..` patterns. `CodergenResult::Full(outcome)` keeps current behaviour — the outcome itself already carries any timing.

Note on wall: `lib/crates/fabro-core/src/executor.rs:30-37` reads ONLY `inference_time_ms` and `tool_time_ms` out of `outcome.timing`. The wall comes from the executor's own stopwatch. So we construct `StageTiming::new(0, inference_ms, tool_ms)` and document that the wall field is ignored in this hop.

`lib/crates/fabro-workflow/src/handler/llm/api.rs`

- `AgentApiBackend::run` (line 1103): after `session.process_input_with_runtime(...)` returns, read `session.last_input_timing()` and set the new `timing` on `CodergenResult::Text` at line 1094.
- `AgentApiBackend::one_shot` (line 994): wrap the `complete_one_shot_request` call at line 1053 with `Instant::now()` / `.elapsed()`. Accumulate across repair iterations of the surrounding loop. All of it counts as inference; no tool work happens in `one_shot`. Set `timing` on `CodergenResult::Text` at line 1094.

`lib/crates/fabro-workflow/src/handler/llm/acp.rs`

`AgentAcpBackend::run` (line ~140): already exposes `result.duration_ms`. Set `timing: StageTiming::new(0, duration_ms, 0)` on the returned `CodergenResult::Text` (per user decision: attribute all ACP duration to inference; ACP is opaque about the split).

**A3. Consume timing in stage handlers and set `outcome.timing`**

- `lib/crates/fabro-workflow/src/handler/agent.rs:341` — after building `outcome`, before the final `Ok(outcome)`, set `outcome.timing = Some(timing_from_codergen_result)`.
- `lib/crates/fabro-workflow/src/handler/prompt.rs:180` — same pattern.
- `lib/crates/fabro-workflow/src/handler/fan_in.rs:266` — backend returns timing; pass it onto the outcome built from the fan-in response.
- `lib/crates/fabro-workflow/src/handler/command.rs:175` — `outcome.timing = Some(StageTiming::new(0, 0, result.duration_ms))`. All command wall-time is tool time. `result.duration_ms` is already at line 154 in scope.

Other handlers (`human`, `wait`, `conditional`, `parallel`, `start`, `exit`, `structured_output`, `manager_loop`) do no inference or tool work. Leave `outcome.timing` as `None`; the executor will naturally produce `inference: 0, tool: 0` for those stages, which is correct.

### Part B — Preserve conclusion timing on engine failure (Bug 2)

`lib/crates/fabro-workflow/src/operations/start.rs`

**B1. Main path** (`persist_terminal_engine_failure`, line 274-308):
- Rename `_conclusion` → `conclusion` and use it:
  - Pass `conclusion.timing` (already a `RunTiming` with the proper inference/tool/wall rollup from `build_conclusion_from_parts`) instead of `RunTiming::wall_only(...)`.
  - Pass `conclusion.billing.clone()` instead of `None` for the billing arg of `workflow_run_failed_from_error`.
  - `final_git_commit_sha`, `final_patch`, `diff_summary` stay `None` — those require the finalize-side workspace diff computation that this path deliberately skips.

**B2. Drop-guard paths** (per user decision: fix them too):

- `DetachedRunBootstrapGuard` (line 882-948): add an `Option<RunStoreHandle>` field. The bootstrap function builds the guard before the store exists, then mutates `bootstrap_guard.run_store = Some(store.clone())` once the store is in scope. On Drop, if the store is `Some`, the spawned task calls `build_conclusion_from_store` and uses its timing/billing; otherwise falls back to `RunTiming::default()` (pre-store failure means no stages can possibly exist).

- `DetachedRunCompletionGuard` (line 953-1021): armed after the store exists, so add a non-optional `run_store: RunStoreHandle`. Drop's spawned task builds the conclusion and uses it.

- `persist_detached_failure` (line 1023): add a `run_store: &RunStoreHandle` parameter. Call `build_conclusion_from_store` and forward `timing` + `billing` to the failure event. Update the two callers (postrun-related) to pass the store they already have in scope.

`RunStoreHandle` is already `Clone` (the surrounding code clones it routinely), so move-into-spawned-task is fine.

### Critical existing utilities to reuse (do not duplicate)

- `fabro_types::StageTiming::new(wall, inference, tool)` and `RunTiming::new(...)` — invariant-enforcing constructors at `lib/crates/fabro-types/src/timing.rs:38, 91`.
- `crate::millis_u64(duration)` helper for `Duration → u64` ms in `fabro-workflow` (used widely; see `lifecycle/event.rs:80-86`).
- `build_conclusion_from_store` at `lib/crates/fabro-workflow/src/pipeline/finalize.rs:71` already does the rollup we need on the engine-failure path.
- `billing_rollup_from_projection` (called inside `build_conclusion_from_parts`) sums per-stage timings into `RunTiming` — no need to reimplement.

## Tests

- **`fabro-agent` unit test**: feed `Session` a fake `LlmClient` whose `stream` sleeps a known duration and a fake tool that sleeps another known duration. Drive one `process_input_with_runtime` call. Assert `session.last_input_timing()` reports both non-zero and roughly matching the sleeps. Then call again and assert it's per-call (not cumulative).
- **`fabro-workflow` handler tests**: in `handler/agent.rs`'s test module, wire a `CodergenBackend` that returns `CodergenResult::Text { timing: StageTiming::new(0, 200, 300), .. }` and assert `AgentHandler::execute`'s returned `Outcome.timing` carries those values. Mirror for `prompt.rs` and `fan_in.rs`. Add a `command.rs` test that mocks a `sandbox.exec_command_streaming` returning `duration_ms = 500` and asserts `outcome.timing.tool_time_ms == 500`.
- **Executor integration**: add a test in `fabro-workflow` (or extend an existing one in `pipeline/finalize.rs` tests) that runs a tiny graph with a handler producing `Outcome.timing = Some(StageTiming::new(0, 100, 50))` and asserts the emitted `stage.completed` event carries those values, and that `run.completed` carries the summed rollup.
- **`persist_terminal_engine_failure` test**: seed a `RunStore` with a couple of `stage.completed` events whose timing is non-zero, drive the engine-failure path, and assert the emitted `WorkflowRunFailed` event has `timing.inference_time_ms` and `tool_time_ms` matching the per-stage sum and `billing` populated.
- **Drop guard tests**: trickier because of `Handle::try_current` + spawn. Add focused tests that arm a guard, drop it, and `tokio::task::yield_now().await` enough times to let the spawned task run, then assert the emitted failure event carries non-zero timing.
- Run `cargo nextest run -p fabro-agent -p fabro-workflow -p fabro-store -p fabro-core`.
- Run formatter and lints per CLAUDE.md: `cargo +nightly-2026-04-14 fmt --check --all` and `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`.

## End-to-end verification

1. Build the server: `cargo build -p fabro-server`.
2. Start server: `fabro server start`.
3. Run a small agent-backed workflow (e.g. `fabro run repl` with a short prompt that fires at least one tool call).
4. `fabro events <run_id> --json | jq -s '[.[] | select(.event=="stage.completed")] | .[].properties.timing'` — confirm `inference_time_ms > 0` and `tool_time_ms > 0` for the agent stage.
5. `fabro events <run_id> --json | jq -s '[.[] | select(.event=="run.completed" or .event=="run.failed")] | .[].properties.timing'` — confirm `active_time_ms == inference_time_ms + tool_time_ms` and both are non-zero.
6. Open the run in the web UI (start the SPA dev build per CLAUDE.md or rebuild the embedded SPA with `cargo dev build`), hover the Duration chip, confirm **Active (inference + tools)** is non-zero.
7. For Bug 2: force an engine failure by setting a very low visit limit and rerunning the same workflow; confirm the `run.failed` event timing breakdown is non-zero and matches the per-stage sum.

## Out of scope

- Adding `wall_time_ms` correctness to `Outcome.timing` (executor ignores it; doc tweak only if necessary).
- Surfacing inference vs tool split for ACP backend beyond "all-inference" attribution.
- Backfilling timing for historical runs that have already emitted zero events — past events are immutable.
- Web UI changes beyond what the existing popover already renders.


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