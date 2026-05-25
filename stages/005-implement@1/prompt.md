Goal: ---
date: 2026-05-25
status: active
---

# Add Provider Probe Endpoint

## Summary

Add `POST /api/v1/providers/test` as the focused LLM-provider subset of server diagnostics. V1 has no request body: it tests every configured LLM provider once, using the catalog probe model, and returns typed results suitable for API, CLI, or UI callers without parsing `/health/diagnostics`.

## Key Changes

- Add OpenAPI operation `testProviders` under the Models tag:
  - `POST /api/v1/providers/test`
  - Response schema `ProviderTestList`
  - `data[]`: `{ provider, model_id, status, error_message }`
  - `summary`: `{ status, total, passed, failed }`
- Use provider status enum `ok | error`; do not include `skip` because v1 only tests configured providers.
- Make `model_id` nullable for configuration, auth, or registration failures where no probe was sent.
- Return HTTP `200` for provider-level failures; use `summary.status = "error"` when any provider fails or when no providers are configured.
- Keep auth required via the same `RequiredUser` path as `/models` and `/providers`.

## Implementation Changes

- Add `.route("/providers/test", post(test_providers))` alongside existing model routes in the models handler.
- Extract the LLM provider probing portion of diagnostics into shared logic used by both `/providers/test` and `/health/diagnostics`.
- Probe flow:
  - Determine configured providers from server credentials/config in catalog order.
  - For each configured provider, report auth or registration issues as `error` without making a network call.
  - Otherwise choose `Catalog::probe_for_provider(provider)` and send the existing cheap basic probe (`Say OK`, `max_tokens=16`, 30s timeout).
  - Preserve diagnostics output by mapping the shared structured results back into the existing `LLM Providers` check/details format.
- Regenerate API clients after editing `docs/public/api-reference/fabro-api.yaml`:
  - Rust: `cargo build -p fabro-api`
  - TypeScript: `cd lib/packages/fabro-api-client && bun run generate`

## Test Plan

- Add server handler tests for:
  - No configured providers returns `200`, empty `data`, and `summary.status = "error"`.
  - One configured provider with a mocked successful probe returns one `ok` row with the selected probe model.
  - Provider auth or registration issue returns one `error` row and does not call the upstream provider.
  - Mixed providers preserve catalog order and summary counts.
  - Response body does not leak API keys or internal credential material.
- Add or adjust diagnostics test coverage to confirm `/health/diagnostics` still reports the same `LLM Providers` pass/error summaries after sharing the probe logic.
- Run focused verification:
  - `cargo nextest run -p fabro-server test_providers`
  - `cargo nextest run -p fabro-server diagnostics`
  - `cargo build -p fabro-api`
  - `cd apps/fabro-web && bun run typecheck` after TypeScript client regeneration if web imports are affected.

## Assumptions

- V1 intentionally has no request body or provider filter.
- This endpoint is API-only; no CLI command or web UI flow changes are included.
- Provider probe failures are data results, not HTTP failures, matching `POST /api/v1/models/{id}/test` behavior.


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