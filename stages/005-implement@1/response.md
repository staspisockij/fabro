Implemented the stage timing and terminal failure rollup fixes.

Summary of changes:
- Added per-input `fabro-agent::Session` timing:
  - Tracks LLM inference/stream time and tool execution time.
  - Exposes `SessionInputTiming` via `Session::last_input_timing()`.
  - Resets timing at each `process_input_with_runtime` entry.
- Threaded timing through workflow LLM backends:
  - `CodergenResult::Text` now carries active `StageTiming`.
  - API backend measures one-shot inference and agent-loop inference/tool time.
  - ACP backend attributes opaque duration to inference.
- Populated `Outcome.timing` in production handlers:
  - Agent, prompt, fan-in, and command handlers now preserve active timing.
  - Command duration is reported as tool time.
- Preserved timing/billing for terminal run failures:
  - `persist_terminal_engine_failure` now uses `build_conclusion_from_store` timing and billing.
  - Detached bootstrap/completion guards now preserve conclusion timing/billing when a store exists.
  - Detached failure helper now rolls up timing/billing from the store.
- Added tests for:
  - Agent per-input inference/tool timing.
  - Agent/prompt/fan-in handler timing propagation.
  - Command handler tool timing.
  - Executor propagation into `NodeResult`.
  - Full workflow event rollup from `Outcome.timing` → `stage.completed` → `run.completed`.
  - Terminal engine failure and drop-guard timing/billing preservation.

Validation passed:
- `cargo nextest run -p fabro-agent -p fabro-workflow -p fabro-store -p fabro-core`
  - 1913 passed, 122 skipped
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `cargo build -p fabro-server`
- `git diff --check`

I did not run the interactive/live server + UI E2E workflow steps, but the server build and full requested automated validation are green.