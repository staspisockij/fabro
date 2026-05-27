Implemented the audited missing piece: `install-app.tsx` no longer calls `useEffect` directly.

Changes made:
- Added `apps/fabro-web/app/hooks/use-install-effects.ts` with purpose-named install hooks:
  - `useInstallTokenFromUrl`
  - `useInstallGithubCallbackError`
  - `useInstallSessionLoader`
  - `useInstallRestartHealthPolling`
  - `useInstallRootRedirect`
- Updated `apps/fabro-web/app/install-app.tsx` to use those hooks and removed its direct `useEffect` / `startTransition` imports.
- Updated the loading comment so the direct-effect search no longer flags `install-app.tsx` via a comment.

Evidence checked:
- Direct route/component effect search excluding hooks/lib/tests now has no matches:
  ```sh
  rg -n "\buseEffect\b|React\.useEffect|\buse(Layout|Insertion)?Effect\b" apps/fabro-web/app --glob '*.{ts,tsx}' --glob '!apps/fabro-web/app/hooks/**' --glob '!apps/fabro-web/app/lib/**' --glob '!**/*.test.ts' --glob '!**/*.test.tsx'
  ```
  Result: no output.
- Full effect search still only finds approved hook/lib/test locations.
- `cd apps/fabro-web && bun run typecheck` ✅
- `cd apps/fabro-web && bun test --isolate` ✅ — 493 pass, 0 fail

Current worktree from this pass:
- Modified: `apps/fabro-web/app/install-app.tsx`
- Added: `apps/fabro-web/app/hooks/use-install-effects.ts`

Remaining uncertainty:
- I did not add a lint/CI gate, consistent with the policy’s “do not add enforcement until approved hook surface exists and migration path is clear” guidance.