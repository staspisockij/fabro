Let me summarize what was accomplished in this pass:

---

## Summary

### What Changed

**Goal**: Move all direct `useEffect` calls out of route/component code and into named hooks per the React Effects Policy.

**Completed migrations:**

| File | Before | After |
|---|---|---|
| `run-artifacts.tsx` | Direct `useEffect` for async URL fetch | `useMountEffect` (single-mount, stable entry props) |
| `run-artifacts.tsx` | Stale `useEffect(() => setStageParam(...), [selectedStage])` | Render-phase conditional `if (stageParam !== selectedStage) setStageParam(...)` |
| `run-sandbox/filesystem-panel.tsx` | `useEffect(() => { model.resetPaths(...) }, [])` | Render-phase `model.resetPaths(treeInputs.paths)` (safe: only mutates external widget) |
| `chats-detail.tsx` | `useEffect` with `didStartRef` guard + multiple deps | `useMountEffect` (ChatRuntime is keyed by chatId; pendingResponse is stable at mount) |
| `run-files.tsx` | 3 direct `useEffect` calls in route body | Extracted to `useRunFileTransition`, `useFocusAfterActive`, `useDeepLinkFocus` named hooks in same file |
| `run-overview.tsx` | Large SVG DOM + event-listener effect | Extracted to `useGraphSvgAnnotations` named hook |
| `automation-diagram.tsx` | Async viz.js render effect | Extracted to `useVizDiagram` named hook |
| `run-detail/docked-controls.tsx` | Layout context sync effect | Extracted to `useAskFabroSidebarWidth` named hook |
| `components/terminal-view.tsx` | Large xterm + WebSocket + ResizeObserver effect | Extracted to `useTerminalSession` named hook |
| `run-files/file-tree-sidebar.tsx` | 2 direct effects for imperative tree model | Extracted to `useFileTreeModelSync` named hook |

**Result**: Every `useEffect` in the non-test production codebase is now inside a purpose-named hook. The only exceptions are `install-app.tsx` (5 effects) which the policy doc explicitly defers as requiring SWR/query refactoring or a small state machine.

### Evidence
- `bun run typecheck`: passes ✓  
- `bun test`: 479 pass, 14 fail (same 14 pre-existing failures unrelated to changed files) ✓

### Remaining Uncertainty
- `install-app.tsx` is the last holdout — it requires a larger architectural change (SWR hooks or an install state machine) that the policy doc explicitly defers.
- The `run-files/file-tree-sidebar.tsx` hook passes refs from the component into `useFileTreeModelSync`; if `@pierre/trees` adds a React-integrated sync API in the future, the hook can be simplified.