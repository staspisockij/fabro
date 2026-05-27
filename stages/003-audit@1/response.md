Audit result: incomplete.

Evidence checked:
- Direct effect search across `apps/fabro-web/app` still finds `useEffect` usage.
- After excluding hooks/lib/tests, direct route/component usage remains in `apps/fabro-web/app/install-app.tsx`:
  - import at line 1
  - effects at lines 306, 316, 328, 355, 422
  - comment at line 541 referencing session-fetch `useEffect`
- Validation commands pass:
  - `cd apps/fabro-web && bun run typecheck` ✅
  - `cd apps/fabro-web && bun test --isolate` ✅ — 493 pass, 0 fail

Why this does not prove completion:
- The policy explicitly says route/component code should not call `useEffect` directly.
- `install-app.tsx` is route/component-level app code and still has direct effects for URL token/error consumption, install session loading, restart health polling, and root redirect navigation.
- The goal itself names `install-app.tsx` as an existing hotspot needing SWR/query hooks or a small install state machine before the policy can be considered enforced there.
- Passing tests/typecheck proves the current implementation is valid TypeScript and behavior is covered by existing tests, but it does not satisfy the “no direct route/component effects” policy requirement.

Next concrete work:
- Migrate `install-app.tsx` direct effects into purpose-named approved hooks or a small install state machine/SWR-backed flow, preserving token URL scrubbing, GitHub callback error handling, session loading, restart health polling, and root redirect behavior.
- Re-run:
  - direct-effect search
  - `cd apps/fabro-web && bun test --isolate`
  - `cd apps/fabro-web && bun run typecheck`

{
  "outcome": "failed",
  "preferred_next_label": "Continue",
  "failure_reason": "apps/fabro-web/app/install-app.tsx still contains direct useEffect calls in route/component-level code, which violates the policy and was explicitly listed as a hotspot needing migration.",
  "context_updates": {
    "goal_status": "incomplete",
    "goal_remaining_work": "Migrate install-app.tsx direct effects into purpose-named approved hooks or a small install state machine/SWR-backed flow, then rerun the direct-effect search, bun test --isolate, and bun run typecheck."
  }
}