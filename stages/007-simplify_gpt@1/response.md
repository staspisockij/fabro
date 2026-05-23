Implemented one cleanup from the review:

- Reused the shared lifecycle action helper for `retryRun`.
- Made `runLifecycleAction` exhaustive for the expanded `LifecycleAction` union by adding the `"retry"` case.
- This removes duplicated retry request/error-handling logic and keeps future lifecycle action handling centralized.

Validation passed:

- `cd apps/fabro-web && bun test app/lib/run-actions.test.ts app/routes/run-detail.test.ts app/components/run-summary-panel.test.tsx`
- `cargo nextest run -p fabro-workflow operations::retry --no-fail-fast`
- `cargo nextest run -p fabro-server retry --no-fail-fast`
- `cd apps/fabro-web && bun run typecheck`

Only file changed in this cleanup pass:

- `apps/fabro-web/app/lib/run-actions.ts`