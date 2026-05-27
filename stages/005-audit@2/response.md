Audit result: incomplete.

What current evidence proves:
- `apps/fabro-web` typecheck passes:
  - `cd apps/fabro-web && bun run typecheck` ✅
- Test suite passes:
  - `cd apps/fabro-web && bun test --isolate` ✅ — 493 pass, 0 fail
- Direct React effect search outside `app/hooks`, `app/lib`, and tests returns no matches:
  - This supports that ordinary route/component files no longer directly call `useEffect`, `useLayoutEffect`, or related APIs.

What prevents declaring the goal complete:
- The broad search still has many direct effect hits in hooks/lib files, and completion requires those to be approved integrations, not just wrappers.
- I found remaining cases that are not clearly compliant with the policy:
  - `apps/fabro-web/app/lib/ask-fabro-layout.tsx` uses `useEffect` in `usePublishedAskFabroSidebarWidth` to copy a React-rendered width into React context state. That looks like a React-state bridge rather than synchronization with an external system.
  - `apps/fabro-web/app/hooks/use-install-effects.ts` includes `useInstallSessionLoader`, which performs a normal server read in an effect. The policy prefers SWR/query hooks for server reads, and specifically called install session loading a hotspot needing SWR/query/state-machine treatment before enforcement.
  - `apps/fabro-web/app/routes/insights-editor.tsx` still calls `useMountEffect`. The call is only unmount cleanup for a timeout created elsewhere, not a mount-time resource setup, so it does not obviously satisfy the documented `useMountEffect` rules.

Because the policy explicitly says the goal is not to hide `useEffect` behind nicer names, these questionable hooks mean completion is not proven.

{
  "outcome": "failed",
  "preferred_next_label": "Continue",
  "failure_reason": "Remaining effect wrappers are not all proven approved external integrations; at least the Ask Fabro layout context bridge, install session loader server fetch, and insights-editor useMountEffect cleanup-only usage need repair or stronger justification.",
  "context_updates": {
    "goal_status": "incomplete",
    "goal_remaining_work": "Audit and fix the remaining questionable effect wrappers: replace the Ask Fabro layout width effect with a declarative/context-owned design or approved external integration, move install session loading to SWR/query/state-machine semantics, and replace the insights-editor cleanup-only useMountEffect with a purpose-named timer cleanup hook or event-owned cleanup."
  }
}