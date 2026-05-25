Implemented `POST /api/v1/providers/test`.

Summary:
- Added OpenAPI `testProviders` operation and schemas:
  - `ProviderTestList`
  - `ProviderTestResult`
  - `ProviderTestSummary`
  - `ProviderTestStatus` (`ok | error`)
- Added server route:
  - `.route("/providers/test", post(test_providers))`
  - protected by `RequiredUser`
- Extracted shared provider probe logic in diagnostics:
  - Catalog-order configured provider selection
  - Auth/registration failures returned as `error` without network calls
  - Probe model from `Catalog::probe_for_provider`
  - Probe prompt `Say OK`, `max_tokens=16`, 30s timeout
  - HTTP 200 for provider-level failures
  - No-provider case returns empty `data` with `summary.status = "error"`
  - Redacts provider error messages before returning them
- Mapped shared structured probe results back into existing `/health/diagnostics` `LLM Providers` check format.
- Regenerated TypeScript API client models and `ModelsApi.testProviders`.
- Added server tests for no providers, success, auth issue, registration issue, mixed order/counts, secret redaction, and auth requirement.
- Added diagnostics regression tests for no-provider and pass summaries.

Validation run:
- `cargo nextest run -p fabro-server test_providers` ✅
- `cargo nextest run -p fabro-server diagnostics` ✅
- `cargo nextest run -p fabro-server --features test-support openapi_conformance --no-tests=pass` ✅
- `cargo build -p fabro-api` ✅
- `cd lib/packages/fabro-api-client && bun run generate` ✅
- `cd lib/packages/fabro-api-client && bun run typecheck` ✅
- `cd apps/fabro-web && bun run typecheck` ✅
- `cargo +nightly-2026-04-14 fmt --check --all` ✅
- `cargo +nightly-2026-04-14 clippy -q -p fabro-server --all-targets -- -D warnings` ✅

Red/green TDD note: the new `test_providers` tests initially failed with 404 before the route/handler implementation, then passed after implementation.