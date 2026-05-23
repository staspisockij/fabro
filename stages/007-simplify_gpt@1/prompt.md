Goal: ---
title: Add Manual Run Retry
type: feat
status: active
date: 2026-05-23
---

# Add Manual Run Retry

## Summary

Add a **Retry** action for failed Fabro runs that creates and immediately starts a new run from the failed run's captured run definition. The new run is independent runtime state, records `retried_from: <source_run_id>`, and leaves the source run unchanged.

This is a fresh run, not resume/fork/rewind. It should copy the source run's durable definition and settings, but not checkpoints, stage state, sandbox state, PR links, billing, questions, conclusions, or pending controls.

## Key Changes

- Add `retried_from` as a nullable public field on `Run`.
  - Store it on the new run only.
  - Do not add a reverse `retried_by` field in v1.
  - Preserve backward compatibility with old events by defaulting to `null`.

- Add `POST /api/v1/runs/{id}/retry`.
  - Response: `201` with the newly created/queued `Run`.
  - Eligible source states: `failed` except `reason=cancelled`, and `dead`.
  - Reject active, succeeded, cancelled, archived, and missing runs with existing API error patterns.
  - The new run should use the current authenticated actor as `created_by`.
  - The new run should preserve the source run's current `parent_id`, title, labels, workflow graph/source, resolved settings, git context, manifest/definition blob refs, and `fork_source_ref` if present.

- Implement retry using a workflow operation similar in shape to `fork`, but without replaying checkpoint/runtime events.
  - Create a new run store.
  - Append `run.created` with `retried_from`.
  - Append `run.submitted`.
  - Queue/start it through the same internal start path used by `POST /runs/{id}/start`.

- Update OpenAPI and generated clients.
  - Edit `docs/public/api-reference/fabro-api.yaml`.
  - Regenerate Rust API types through `cargo build -p fabro-api`.
  - Regenerate TypeScript client in `lib/packages/fabro-api-client`.

- Update the web UI.
  - Add `Retry` to the run action menu for eligible failed/dead runs.
  - Disable the action while pending.
  - On success, navigate to the new run page and refresh run/list caches.
  - Add a compact "Retried from" link in the run summary panel when `retried_from` is present.
  - Add demo-mode support or hide the action in demo mode so the button never navigates to a missing demo run.

## Test Plan

- Rust workflow/store tests:
  - `run.created` serializes/deserializes `retried_from`.
  - Old `run.created` events project with `retried_from = None`.
  - Retry creates a new run with a different ID, copied durable definition, no runtime state, and `retried_from` set.
  - Retry preserves current `parent_id`, title, labels, git context, settings, and `fork_source_ref`.
  - Retry rejects succeeded, active, cancelled, and archived source runs.

- Rust server/API tests:
  - `POST /runs/{id}/retry` on a failed run returns `201`, a new run ID, `retried_from`, and queued/started lifecycle state.
  - Source run remains unchanged.
  - `404` for unknown run.
  - `409` for non-retryable status.
  - Generated Rust API compiles against the updated OpenAPI contract.

- Web tests:
  - `canRetry` returns true for failed/dead, false for cancelled/succeeded/active/archived.
  - Action menu renders `Retry` only when eligible.
  - Successful retry calls the generated client and navigates to `/runs/:newId`.
  - Retry errors show a useful toast/message.
  - Run summary panel renders the `Retried from` link when present.
  - Typecheck passes with regenerated client types.

## Assumptions

- V1 does not add a CLI `fabro retry` command.
- V1 does not add automatic retry attempts, retry counts, or idempotency keys.
- Multiple manual clicks after the first request completes may create multiple retry runs.
- "Same settings" means the source run's captured durable definition/settings, not latest local files from the user's machine.
- Cancelled runs are excluded because cancellation is user intent, not execution failure.


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
  - Model: gpt-5.5, 463.1k tokens in / 56.1k out
  - Files: /home/daytona/workspace/fabro/lib/crates/fabro-workflow/src/operations/retry.rs
- **simplify_opus**: succeeded
  - Model: claude-opus-4-7, 194.0k tokens in / 33.0k out
  - Files: /home/daytona/workspace/fabro/apps/fabro-web/app/lib/mutations.ts, /home/daytona/workspace/fabro/apps/fabro-web/app/lib/run-actions.ts, /home/daytona/workspace/fabro/apps/fabro-web/app/routes/run-detail.test.ts, /home/daytona/workspace/fabro/apps/fabro-web/app/routes/run-detail.tsx, /home/daytona/workspace/fabro/lib/crates/fabro-server/src/server/handler/lifecycle.rs, /home/daytona/workspace/fabro/lib/crates/fabro-workflow/src/operations/retry.rs


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