Goal: # Agent Compaction API Usage Baseline Plan

Date: 2026-05-23

## Summary

Change Fabro's agent compaction trigger from a whole-history `chars / 4`
estimate to a Claude Code-style hot-path estimate: use the latest real
assistant response's stored `usage.total_tokens()` as the baseline, then add
local estimates for turns appended after that response. This avoids token-count
provider API calls while making compaction sensitive to actual
provider-reported context usage, including cache and reasoning tokens.

No provider token-count API calls should be added in this change.

## Key Changes

- Replace the current compaction estimate in `fabro-agent` with a new
  active-context estimator.
- Find the newest assistant turn whose `usage.total_tokens() > 0`.
- Use that `usage.total_tokens()` as the baseline.
- Add local estimates only for turns after that assistant turn.
- If no usable assistant usage exists, fall back to the existing local
  whole-history estimate.
- Reuse a shared per-turn local estimate helper so fallback and post-baseline
  delta counting stay consistent.
- Keep the estimator local and in-process. Do not call
  `llm_client.count_input_tokens()` from `compact_if_needed()`.

## Implementation Details

- Update `lib/crates/fabro-agent/src/compaction.rs`:
  - Add an estimator that returns both token count and method, for example
    `ApiUsagePlusLocalDelta` or `LocalEstimate`.
  - Make `check_context_usage()` use the new estimator and include the method
    in warning `details`.
  - Make `compact_context()` report the same improved estimate in
    `CompactionStarted`.
  - Move `CompactionStarted` emission after the
    `original_turn_count <= preserve_count` no-op check, so a no-op compact
    cannot emit started without completed.
- Update `lib/crates/fabro-agent/src/history.rs`:
  - In `History::compact()`, invalidate preserved assistant usage by replacing
    preserved assistant `usage` with `TokenCounts::default()`.
  - Keep provider parts, response IDs, text, and tool calls unchanged.
  - Rationale: preserved assistant usage reflects the pre-compaction context and
    must not become the next baseline. Billing remains available from emitted
    run events, so mutable runtime history should prefer compaction correctness.
- Leave public run event names and schemas unchanged:
  - `agent.compaction.started`
  - `agent.compaction.completed`
  - Existing warning event remains a warning with richer `details`.

## Test Plan

- Add unit coverage in `lib/crates/fabro-agent/src/compaction.rs`:
  - No assistant usage: estimator matches current local whole-history behavior.
  - Latest assistant usage present: estimator uses `usage.total_tokens()` plus
    only later tool/user/steering turns.
  - Usage fields include cache and reasoning through `TokenCounts::total_tokens()`.
  - Earlier assistant usage is ignored when a later assistant usage exists.
- Add unit coverage in `lib/crates/fabro-agent/src/history.rs`:
  - `History::compact()` preserves assistant content, tool calls, and provider
    parts, but resets preserved assistant usage to default.
  - Existing OpenAI opaque stripping and Anthropic thinking preservation tests
    still pass.
- Add session coverage in `lib/crates/fabro-agent/src/session.rs`:
  - A short assistant response with high `usage.total_tokens()` triggers
    compaction even when text length is small.
  - A compact no-op due to `turns.len() <= preserve_count` does not emit
    `CompactionStarted`.
  - Compaction disabled still prevents compaction even if the API usage
    baseline exceeds threshold.
- Run targeted verification:
  - `cargo nextest run -p fabro-agent compaction`
  - `cargo nextest run -p fabro-agent history`
  - If those pass, run `cargo nextest run -p fabro-agent`.

## Assumptions

- Runtime/session `Message::Assistant.usage` is safe to invalidate after
  compaction because authoritative billing comes from emitted workflow/run
  events, not preserved mutable agent history.
- A zero-token `TokenCounts::default()` should be treated as no usable API
  baseline.
- Provider token-count APIs remain available for future near-threshold
  confirmation, but are intentionally out of scope for this change.


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
- **implement**: succeeded
  - Model: gpt-5.5, 168.6k tokens in / 21.5k out


# Simplify: Code Review and Cleanup

Review changes vs. origin for reuse, quality, and efficiency. Fix any issues found.

## Phase 1: Identify Changes

Run git diff (or git diff HEAD if there are staged changes) to see what changed. If there are no git changes, review the most recently modified files that the user mentioned or that you edited earlier in this conversation.

## Phase 2: Launch Three Review Agents in Parallel

Use the Agent tool to launch all three agents concurrently in a single message. Pass each agent the full diff so it has the complete context.

### Agent 1: Code Reuse Review

For each change:

1. Search for existing utilities and helpers that could replace newly written code. Use Grep to find similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. Flag any new function that duplicates existing functionality. Suggest the existing function to use instead.
3. Flag any inline logic that could use an existing utility — hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

Note: This is a greenfield app, so focus on maximizing simplicity and don't worry about changing things to achieve it.

### Agent 2: Code Quality Review

Review the same changes for hacky patterns:

1. Redundant state: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. Parameter sprawl: adding new parameters to a function instead of generalizing or restructuring existing ones
3. Copy-paste with slight variation: near-duplicate code blocks that should be unified with a shared abstraction
4. Leaky abstractions: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. Stringly-typed code: using raw strings where constants, enums (string unions), or branded types already exist in the codebase

Note: This is a greenfield app, so be aggressive in optimizing quality.

### Agent 3: Efficiency Review

Review the same changes for efficiency:

1. Unnecessary work: redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns
2. Missed concurrency: independent operations run sequentially when they could run in parallel
3. Hot-path bloat: new blocking work added to startup or per-request/per-render hot paths
4. Unnecessary existence checks: pre-checking file/resource existence before operating (TOCTOU anti-pattern) — operate directly and handle the error
5. Memory: unbounded data structures, missing cleanup, event listener leaks
6. Overly broad operations: reading entire files when only a portion is needed, loading all items when filtering for one

## Phase 3: Fix Issues

Wait for all three agents to complete. Aggregate their findings and fix each issue directly. If a finding is a false positive or not worth addressing, note it and move on — do not argue with the finding, just skip it.

When done, briefly summarize what was fixed (or confirm the code was already clean).