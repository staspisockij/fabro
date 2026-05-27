Implemented the overlay replacement across `fabro-web`.

What changed:
- Replaced DIY `Tooltip` / `HoverCard` in `app/components/ui.tsx` with Radix wrappers.
- Added app-level `TooltipProvider` and Sonner `<Toaster richColors position="bottom-right" />` in `app/layouts/app-shell.tsx`.
- Replaced custom toast context/rendering with a Sonner-backed shim preserving `useToast()` / `ToastProvider` API.
- Rewrote `toast.test.tsx` around Sonner observable behavior and persistent error toasts.
- Converted CSS-only settings model tooltips to real `<Tooltip>`.
- Added shared `FloatingTooltip` for SVG/DOMRect-anchored hovers and migrated:
  - `run-overview`
  - `event-debug` DNA popover
  - `event-debug` thread DNA popover
- Deleted `hover-card-style.ts`.
- Added dependencies:
  - `@radix-ui/react-tooltip`
  - `@radix-ui/react-hover-card`
  - `sonner`
- Removed the stale toast `action` type usage from the remaining test helper.

Verification:
- `cd apps/fabro-web && bun run typecheck` ✅
- `cd apps/fabro-web && bun run test` ✅  
  - This runs the package script: `bun test --isolate`
  - 493 tests passed.