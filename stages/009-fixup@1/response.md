All verify steps pass. The verify failure was due to an unset git identity preventing the merge, and the merge introduced two conflicts:

1. **`lib/crates/fabro-slack/src/blocks.rs`** — Resolved by keeping both new tests (the local `option_descriptions_are_rendered_and_preview_is_not_special_cased` test and the four new run-lifecycle tests from main).

2. **`lib/crates/fabro-workflow/src/handler/agent.rs`** — Resolved by adopting `main`'s new `emit_stage_prompt` helper while preserving the local `AgentToolRuntime` construction (with `WorkflowAgentQuestionRuntime`) needed for the agent question tools.

Verification results:
- `cargo +nightly-2026-04-14 fmt --check --all`: clean
- Forbidden-token grep: clean
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`: clean
- `cargo nextest run --workspace --profile ci`: 6203 passed, 181 skipped
- `cargo dev docs check`: up to date
- `bun install --frozen-lockfile`: no changes
- `apps/fabro-web` typecheck + test: 440 pass, 0 fail
- `lib/packages/fabro-api-client` typecheck: clean
- `cargo dev build -- -p fabro-cli --release`: success