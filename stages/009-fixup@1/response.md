Both tests and typecheck pass. The failure was caused by a stale test file: commit `aa1613e95` on main simplified the `StageInsightsSidebar` component (dropped the permission badge and stripped tool row metadata) but did not update `stage-insights-sidebar.test.tsx`. After merging main into this branch, those assertions broke.

Fixes:
- Removed the two permission-badge tests (`Read-only`, `Full access`) since the component no longer renders that badge.
- Removed the `legacy stages without agent tools keep permission fallback only` test (same reason).
- Trimmed the agent-tools test to assert only the tool names, descriptions (as `title` tooltips), and the `1/2` count, matching what the slimmed `AgentToolsSection` actually renders.
- Removed the `Unknown` assertion from the empty-state test.
- Replaced the unused `PermissionLevel` import with `AgentToolCategory` (still required by the `AgentToolSummary` type).

Final result: 486 pass / 0 fail, typecheck clean.