All clean. Final summary:

## Cleanup Applied

Aggregated findings from three reviews and applied 7 focused fixes (3 files, net −31 lines):

**Efficiency**
- `bounded_display_field` now truncates in a single `char_indices().nth(...)` pass instead of `chars().count()` + `chars().take()`.
- Dropped redundant `Ulid::new()` from `internal_question_id` — slug + stage visit + tool-call-id + index is already unique.

**Code quality**
- De-duped the access-denial / hook-block / normal-execution event triple via shared `emit_tool_call_started` and `emit_tool_call_result` helpers in `tool_execution.rs`, dropping ~25 lines of copy-pasted emit code.
- Cleaned up dead `unwrap_or_else` fallbacks in `format_anthropic_answers` (infallible string serialization).
- Extracted repeated "root agent session" error string into `ROOT_SESSION_REQUIRED_ERROR` constant.
- Renamed `option_label` to `label_for_key`, dropping the redundant `selected_option.filter(key)` defensive check. Preserved the `selected_option`-first lookup for `Selected` (control-protocol path supplies `Selected(key)` with `selected_option: None`).
- Removed the unused `Default for RunInterviewBlocker` impl.
- De-duped `RunInterviewGuard::resolve` and `Drop` via a shared `resolve_in_place` method.

**Findings noted but not applied** (with rationale):
- Lifting `agent_tool_runtime` from a parameter into a task-local set once at the top: large cross-crate refactor; skipped to keep scope bounded.
- Unifying OpenAI/Anthropic question tools into one schema: schemas intentionally differ (`id`/`header` required for OpenAI, `multiSelect` and `preview` for Anthropic); separation matches provider contracts.
- `AgentToolRuntime` one-field wrapper: keeping a struct allows future expansion at no extra friction.
- `register_question_tools` moving into `AgentProfile` trait: cross-crate refactor; current explicit dispatch is fine for two profiles.
- Cleaning `ControlInterviewer.pending` on agent-batch cancel: needs a new `Interviewer` API; flagged as the most substantial follow-up.
- `..InterviewOption::default()` adoption in tests: high-churn, low-value compared to other items in this pass.
- The `mem::forget` suggestion for `RunInterviewGuard::resolve` is buggy — it would leak the `Arc<RunInterviewBlocker>` and `Arc<Emitter>` refs. Used a shared method instead.

**Verification**
- `cargo nextest run -p fabro-agent -p fabro-workflow -p fabro-interview -p fabro-server`: all tests pass except 3 pre-existing flaky SVG-render tests (confirmed by stashing changes and reproducing the same failures on the pre-cleanup tree).
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`: clean.
- `cargo +nightly-2026-04-14 fmt --check --all`: clean.