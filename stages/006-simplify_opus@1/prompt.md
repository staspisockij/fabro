Goal: # Plan: Compute LLM cost on-read for in-flight stages

## Context

On the run billing page (`/runs/{id}/billing`), an active stage shows token
usage but no dollar cost — cost renders as `—` until the stage completes.

Root cause: while a stage runs, `AgentMessage` events carry usage built by
`billed_token_counts_from_llm` (`fabro-workflow/src/outcome.rs:43`), which
hard-codes `total_usd_micros: None`. Dollar cost is only computed by
`billed_model_usage_from_llm` (`outcome.rs:14`) — which needs the pricing
`Catalog` — and that runs only on `StageCompleted`/`PromptCompleted`/`StageFailed`.
So an in-flight stage's `StageProjection.usage.total_usd_micros` stays `None`.

Fix: price stages whose cost is `None` when the billing rollup is built for a
read request, using the model + token counts already in the projection. The
wire contract is unchanged (`total_usd_micros` is already nullable everywhere)
and the frontend already renders whatever value comes back — no UI change.

## Decisions

- **Price any stage with `total_usd_micros == None`**, not just in-flight ones.
  Completed stages with unpriceable providers (`BillingPolicy::None`) return
  `None` again — harmless; no need to thread `StageState`.
- **No "estimated" label.** Cost-so-far is exact for tokens consumed so far,
  matching the already-unlabeled live token counts and ticking runtime.
- **Aggregate billing stays finalized-only.** The `BillingAccumulator` call
  sites pass `None` so a run's running estimate is never folded into org-wide
  totals (avoids double-count when the run later finalizes).
- Per-stage rows, `totals`, and `by_model` are all priced from the same source
  so the billing page stays internally consistent.

## Changes

### 1. `lib/crates/fabro-model/src/billing.rs`

- Add `BilledTokenCounts::token_counts(&self) -> TokenCounts` — drops
  `total_tokens`/`total_usd_micros`, keeps the five disjoint buckets.
- Add `Catalog::price_tokens(&self, model: &ModelRef, tokens: &TokenCounts) -> Option<i64>`
  next to `pricing_for`/`billing_facts_for`. Body mirrors the cost lines of
  `billed_model_usage_from_llm`: build `ModelBillingFacts` via
  `billing_facts_for`, assemble `ModelBillingInput { ModelUsage { model, tokens }, facts }`,
  then `pricing_for(model).and_then(|p| p.bill(&input)).map(|a| a.0)`. Returns
  `None` when the provider has no billing policy.

### 2. `lib/crates/fabro-workflow/src/billing_rollup.rs`

- Change signature to
  `billing_rollup_from_projection(projection: &RunProjection, catalog: Option<&Catalog>)`.
- Add a module-private helper `stage_usage_with_cost(catalog, stage) -> BilledTokenCounts`:
  clone `stage.usage`; if `total_usd_micros.is_none()` and both `catalog` and
  `stage.model` are present, set it via `catalog.price_tokens(model, &usage.token_counts())`.
- In the loop, compute `priced` once per stage and use it in place of
  `&stage.usage` for the `is_zero` check, `row.billing.add_counts`,
  `totals.add_counts`, and `model_entry.billing.add_counts`.
- Update the existing tests to pass `None`; add one new test: an in-flight
  stage (no `completion`, non-zero `usage` with `total_usd_micros: None`, a
  builtin `model`) yields `Some(..)` cost on the stage row and in `totals` when
  called with `Some(Catalog::builtin())`.

### 3. Call sites of `billing_rollup_from_projection`

- `lib/crates/fabro-server/src/server/handler/billing.rs:82` — bind
  `let catalog = state.catalog();` (returns `Arc<Catalog>`) and pass
  `Some(&catalog)`.
- `lib/crates/fabro-server/src/server.rs` (2 aggregate-billing sites) — pass `None`.
- `lib/crates/fabro-workflow/src/pipeline/finalize.rs` (4 sites) — pass `None`
  (stages already priced at completion; pricing would be a no-op anyway).

No changes to `fabro-api.yaml`, the generated clients, or `apps/fabro-web`.

## Out of scope / known limitation

In-flight **prompt** stages have no `model` until `PromptCompleted` (only
`AgentMessage` sets `stage.model` mid-run), so they still show `—` while
running. Acceptable: prompt stages are a single short LLM call. The bug report
concerns agent stages, where `model` is available.

## Verification

- `cargo nextest run -p fabro-workflow billing_rollup` — new + updated unit tests pass.
- `cargo nextest run -p fabro-server billing` — handler conformance still passes.
- `cargo build --workspace` and `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`.
- Manual: `fabro server start` + `cd apps/fabro-web && bun run dev`, start a
  workflow with an agent stage, open `/runs/{id}/billing` mid-run — the active
  stage row and totals show a non-`—` dollar amount that grows with tokens.


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
  - Model: claude-opus-4-7, 92.9k tokens in / 16.0k out
  - Files: /home/daytona/workspace/fabro/lib/crates/fabro-model/src/billing.rs, /home/daytona/workspace/fabro/lib/crates/fabro-server/src/server.rs, /home/daytona/workspace/fabro/lib/crates/fabro-server/src/server/handler/billing.rs, /home/daytona/workspace/fabro/lib/crates/fabro-workflow/src/billing_rollup.rs, /home/daytona/workspace/fabro/lib/crates/fabro-workflow/src/pipeline/finalize.rs


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