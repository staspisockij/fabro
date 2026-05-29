Goal: # Create Automation From Run Prefill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend-only flow that lets users start a new automation form from an existing run.

**Architecture:** Reuse the existing `/automations/new` route with an optional `from_run` search parameter. The route derives initial form values from existing run and run-settings queries, then mounts a keyed form child so source data initializes local form state without direct React effects. The run actions menu links to the prefill route for ordinary runs and to the existing automation detail page for automation-created runs.

**Tech Stack:** React 19, React Router, SWR, TypeScript, existing Fabro web API clients, Bun tests.

---

## Decisions

- Add only frontend behavior. Do not change backend routes, OpenAPI, generated clients, or automation persistence.
- Use `/automations/new?from_run=<run_id>` as the public UI interface.
- Treat `from_run` as a draft initializer only. Submitting still calls the existing `automationsApi.createAutomation`.
- If a run already has `run.automation.id`, show `View automation` instead of `Create automation from run`.
- Do not infer schedules from runs. Prefilled automations use manual/API trigger enabled and schedule disabled.
- Do not use direct `useEffect` in route/component code; follow `docs/internal/react-effects-policy.md`.

## Files

- Modify `apps/fabro-web/app/routes/run-detail.tsx` for the actions menu navigation.
- Modify `apps/fabro-web/app/routes/run-detail.test.ts` for run-action coverage.
- Modify `apps/fabro-web/app/routes/automations-new.tsx` for query-param parsing, data loading, and keyed form initialization.
- Modify `apps/fabro-web/app/components/automation-form.tsx` for a pure prefill helper built on existing `AutomationFormValues`, `kebabify`, `snakeify`, and `EMPTY_AUTOMATION_FORM`.
- Create `apps/fabro-web/app/routes/automations-new.test.tsx` for route-level prefill behavior.

## Implementation Tasks

### Task 1: Add A Pure Prefill Helper

- [ ] In `apps/fabro-web/app/components/automation-form.tsx`, add an exported helper named `automationFormValuesFromRun(run, settings)`.
- [ ] The helper should return a complete `AutomationFormValues` object:
  - `name`: run title if present, otherwise workflow name, graph name, slug, or `"New automation"`.
  - `id`: `kebabify(name)`.
  - `description`: empty string.
  - `enabled`: `true`.
  - `repository`: prefer `settings.run.scm.owner` plus `settings.run.scm.repository`; otherwise use a GitHub-looking `run.repository.name`; otherwise parse GitHub `origin_url`; otherwise empty string.
  - `ref`: prefer `sandboxRuntime(run.sandbox)?.clone_branch`; otherwise `"main"`.
  - `workflow`: prefer `run.workflow.slug`; otherwise `snakeify(workflow name, graph name, or name)`.
  - `manualEnabled`: `true`.
  - `scheduleEnabled`: `false`.
  - `cron`: preserve `EMPTY_AUTOMATION_FORM.cron`.
- [ ] Keep repository parsing intentionally narrow: only produce `owner/repo` for GitHub-style values. Leave non-GitHub or unknown repositories blank so users can edit them.

### Task 2: Wire `/automations/new?from_run=...`

- [ ] In `apps/fabro-web/app/routes/automations-new.tsx`, import `useSearchParams`, `useRun`, and `useRunSettings`.
- [ ] Split the route into a wrapper and a keyed form child:
  - Wrapper reads `from_run`.
  - Wrapper calls `useRun(fromRunId)` and `useRunSettings(fromRunId)` only when `from_run` is present.
  - Wrapper derives initial values during render.
  - Form child owns `useState(initialValues)` exactly as the current route does.
- [ ] For the blank path, preserve current behavior and render immediately with `EMPTY_AUTOMATION_FORM`.
- [ ] For `from_run`, render a small loading placeholder until the run query resolves.
- [ ] If the source run cannot be loaded, render the normal empty form with a non-blocking `ErrorMessage` explaining that the source run could not be loaded and the automation can be filled manually.
- [ ] On cancel, continue navigating to `/automations`.
- [ ] On submit success, keep the current toast and navigation to `/automations`.

### Task 3: Add Run Detail Actions

- [ ] In `apps/fabro-web/app/routes/run-detail.tsx`, add an operations action after `Preview` and before interrupt/steering actions.
- [ ] If `summary.automation?.id` is present:
  - key: `view-automation`
  - label: `View automation`
  - onSelect: navigate to `/automations/${encodeURIComponent(summary.automation.id)}`
- [ ] Otherwise:
  - key: `create-automation`
  - label: `Create automation from run`
  - onSelect: navigate to `/automations/new?from_run=${encodeURIComponent(params.id)}`
- [ ] Do not disable the action for terminal, active, archived, or demo runs. It is only navigation.

### Task 4: Add Focused Tests

- [ ] Add `apps/fabro-web/app/routes/automations-new.test.tsx`.
- [ ] Mock `../lib/queries` so `useRun` and `useRunSettings` can return controlled data.
- [ ] Test `/automations/new` still renders empty form values.
- [ ] Test `/automations/new?from_run=run_1` pre-populates name, slug, repository, branch, workflow, manual trigger, and disabled schedule from mocked run/settings data.
- [ ] Test missing source-run data renders the form with an error message and empty editable fields.
- [ ] Extend `apps/fabro-web/app/routes/run-detail.test.ts`:
  - Unlinked run shows `Create automation from run`; selecting it navigates to `/automations/new?from_run=run_1`.
  - Linked run shows `View automation`; selecting it navigates to `/automations/<automation_id>`.

## Verification

- [ ] Run the focused tests:

```bash
cd apps/fabro-web && bun test app/routes/automations-new.test.tsx app/routes/run-detail.test.ts
```

- [ ] Run type checking:

```bash
cd apps/fabro-web && bun run typecheck
```

- [ ] If focused tests expose shared test setup issues, run the full web test suite before finishing:

```bash
cd apps/fabro-web && bun test
```

## Acceptance Criteria

- From an ordinary run detail page, the actions menu includes `Create automation from run`.
- Selecting it opens `/automations/new?from_run=<run_id>` with editable prefilled automation fields.
- From a run that already has automation metadata, the actions menu includes `View automation` and does not offer a duplicate-create action.
- Creating the automation still uses the existing create automation API and persists the same automation shape as manual creation.
- No backend, OpenAPI, generated client, or scheduler files are changed.


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
  - Model: gpt-5.5, 1.1m tokens in / 21.5k out


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