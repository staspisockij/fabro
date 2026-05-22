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


Read the plan file referenced in the goal and implement every step. Make all the code changes described in the plan. Use red/green TDD.