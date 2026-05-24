Goal: # Batch Delete Runs API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-soft batch API endpoint for deleting runs, matching the existing archive/unarchive batch behavior while preserving single-run delete semantics.

**Architecture:** Keep OpenAPI as the source of truth, generate Rust and TypeScript client types from the spec, and implement the server endpoint as a small batch wrapper around the existing delete flow. Refactor delete internals to return structured `ApiError` values so both single-delete HTTP responses and per-item batch errors use the same source behavior.

**Tech Stack:** Rust, Axum, OpenAPI/progenitor, openapi-generator TypeScript Axios client, React/TypeScript web helpers, Bun tests, cargo nextest.

---

## Contract Decisions

- Add `POST /api/v1/runs/delete`, not `DELETE /api/v1/runs`, because batch archive/unarchive already use JSON-body action endpoints and JSON request bodies on `DELETE` are less portable.
- Request body is `BatchDeleteRunsRequest`:

```yaml
run_ids:
  type: array
  minItems: 1
  maxItems: 250
  uniqueItems: true
  items:
    type: string
force:
  type: boolean
  default: false
```

- Response body is `BatchDeleteRunsResponse` with ordered `results` and a `{ requested, succeeded, failed }` summary.
- Valid batch requests return `200` even when individual items fail.
- Invalid batch requests return request-level `400` before deleting any run.
- Missing valid run IDs count as success with outcome `already_absent`, matching the existing single-delete documentation: `204` means "Run deleted or already absent."
- `force` is batch-wide. Callers needing mixed force behavior should issue separate requests.
- This plan adds API/client support only. It does not add a visible bulk delete button to the runs UI.

## Files

- Modify `docs/public/api-reference/fabro-api.yaml`: add endpoint and schemas.
- Modify `lib/crates/fabro-server/src/server.rs`: refactor delete internals to return `ApiError` and distinguish deleted/absent/preserved outcomes.
- Modify `lib/crates/fabro-server/src/server/handler/runs.rs`: adapt single-run delete handler to the refactored return type.
- Modify `lib/crates/fabro-server/src/server/handler/system.rs`: adapt prune delete loop to the refactored return type.
- Modify `lib/crates/fabro-server/src/server/handler/lifecycle.rs`: add batch delete route, handler, validation reuse, and per-item response assembly.
- Modify `lib/crates/fabro-server/src/server/tests.rs`: add server coverage.
- Regenerate Rust API code by running `cargo build -p fabro-api`.
- Regenerate TypeScript API client under `lib/packages/fabro-api-client`.
- Modify `apps/fabro-web/app/lib/run-actions.ts`: add `deleteRuns`.
- Modify `apps/fabro-web/app/lib/run-actions.test.ts`: add helper tests.

## Tasks

### Task 1: Add Server Tests First

**Files:**
- Modify `lib/crates/fabro-server/src/server/tests.rs`

- [ ] Add a `batch_delete_body` helper near `batch_lifecycle_body`:

```rust
fn batch_delete_body(run_ids: &[RunId], force: bool) -> serde_json::Value {
    json!({
        "run_ids": run_ids.iter().map(ToString::to_string).collect::<Vec<_>>(),
        "force": force,
    })
}
```

- [ ] Add an assertion helper for delete batch results:

```rust
fn assert_batch_delete_result(
    result: &serde_json::Value,
    run_id: RunId,
    ok: bool,
    outcome: &str,
) {
    assert_eq!(result["run_id"], run_id.to_string());
    assert_eq!(result["ok"], ok);
    assert_eq!(result["outcome"], outcome);
    if ok {
        assert!(
            result["error"].is_null(),
            "successful delete result should omit error: {result}"
        );
    } else {
        assert!(
            result["error"].is_object(),
            "failed delete result should include error: {result}"
        );
    }
}
```

- [ ] Add `batch_delete_removes_runs_and_reports_ordered_results`.
  - Create two succeeded durable runs.
  - `POST /runs/delete` with both IDs and `force: false`.
  - Assert `summary.requested == 2`, `summary.succeeded == 2`, `summary.failed == 0`.
  - Assert outcomes are `deleted`, in request order.
  - Assert subsequent `GET /runs/{id}` returns `404` for both IDs.

- [ ] Add `batch_delete_reports_mixed_results_without_rollback`.
  - Create one succeeded run and one running run.
  - Include a third missing `RunId::new()`.
  - `POST /runs/delete` with `force: false`.
  - Assert outcomes: `deleted`, `conflict`, `already_absent`.
  - Assert the deleted run is gone.
  - Assert the running run still returns `200`.
  - Assert the missing ID counts as success.

- [ ] Add `batch_delete_force_removes_active_runs`.
  - Create a running run.
  - `POST /runs/delete` with `force: true`.
  - Assert outcome `deleted`.
  - Assert subsequent `GET /runs/{id}` returns `404`.

- [ ] Add `batch_delete_with_preserved_sandbox_returns_handoff`.
  - Reuse the durable run setup pattern from `delete_run_with_preserved_sandbox_returns_handoff`.
  - `POST /runs/delete` with `force: true`.
  - Assert outcome `sandbox_preserved`.
  - Assert `sandbox.provider == "local"` and `sandbox.id == "sandbox-preserve-1"`.
  - Assert subsequent `GET /runs/{id}` returns `404`.

- [ ] Add `batch_delete_rejects_invalid_requests_before_mutating_runs`.
  - Create one succeeded run.
  - Send invalid bodies: empty `run_ids`, duplicate IDs, invalid ID string, 251 IDs.
  - Assert each response is `400`.
  - Assert the original run still returns `200`.

- [ ] Add `batch_delete_requires_user_authentication`.
  - Use the existing `jwt_auth_app` pattern.
  - Assert unauthenticated `POST /runs/delete` returns `401`.
  - Assert worker-token `POST /runs/delete` returns `401` or `403`, matching the existing batch lifecycle auth assertion style.

- [ ] Run the new tests before implementation:

```bash
cargo nextest run -p fabro-server batch_delete
```

Expected result: tests fail because `/runs/delete` is not routed and generated API types do not exist yet.

### Task 2: Add OpenAPI Contract And Regenerate Clients

**Files:**
- Modify `docs/public/api-reference/fabro-api.yaml`
- Generated by command: `lib/crates/fabro-api` build output
- Generated by command: `lib/packages/fabro-api-client/src/**`

- [ ] Add `POST /api/v1/runs/delete` near `/api/v1/runs/archive` and `/api/v1/runs/unarchive`.

```yaml
  /api/v1/runs/delete:
    post:
      operationId: batchDeleteRuns
      tags: [Runs]
      summary: Delete Runs
      description: >
        Deletes up to 250 runs in one fail-soft, non-transactional request.
        Each run is processed independently. A valid batch returns `200` even
        when some items fail; inspect `results` and `summary` for per-run
        outcomes. Invalid request bodies are rejected before mutating any run.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/BatchDeleteRunsRequest"
      responses:
        "200":
          description: Batch processed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/BatchDeleteRunsResponse"
        "400":
          description: Invalid batch request
          headers:
            x-request-id:
              $ref: "#/components/headers/XRequestId"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "401":
          description: Not authenticated
          headers:
            x-request-id:
              $ref: "#/components/headers/XRequestId"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Request-level server error
          headers:
            x-request-id:
              $ref: "#/components/headers/XRequestId"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
```

- [ ] Add these schemas near the batch lifecycle schemas:

```yaml
    BatchDeleteRunsRequest:
      description: Run IDs to delete as one bounded fail-soft batch.
      type: object
      additionalProperties: false
      required:
        - run_ids
      properties:
        run_ids:
          type: array
          description: Run IDs to process, in result order.
          minItems: 1
          maxItems: 250
          uniqueItems: true
          items:
            type: string
            example: 01HZX6M29F1CD5YYMHT1F5D7WQ
        force:
          type: boolean
          description: Whether to force deletion of active runs. Defaults to `false`.
          default: false

    BatchDeleteRunsResponse:
      description: Per-run results for a fail-soft batch delete request.
      type: object
      additionalProperties: false
      required:
        - results
        - summary
      properties:
        results:
          type: array
          description: Results ordered exactly like the request `run_ids`.
          items:
            $ref: "#/components/schemas/BatchDeleteRunsResult"
        summary:
          $ref: "#/components/schemas/BatchDeleteRunsSummary"

    BatchDeleteRunsResult:
      description: Result for one run in a batch delete request.
      type: object
      additionalProperties: false
      required:
        - run_id
        - ok
        - outcome
      properties:
        run_id:
          type: string
          description: Run ID from the request item.
        ok:
          type: boolean
          description: Whether this item succeeded.
        outcome:
          type: string
          enum:
            - deleted
            - already_absent
            - sandbox_preserved
            - conflict
            - error
          description: Machine-readable item outcome.
        sandbox:
          $ref: "#/components/schemas/DeleteRunSandbox"
          description: Sandbox handoff details when `outcome` is `sandbox_preserved`.
        error:
          $ref: "#/components/schemas/ErrorResponseEntry"
          description: Structured item error for failed items.

    BatchDeleteRunsSummary:
      description: Aggregate counts for a batch delete request.
      type: object
      additionalProperties: false
      required:
        - requested
        - succeeded
        - failed
      properties:
        requested:
          type: integer
          minimum: 0
          description: Number of requested run IDs.
        succeeded:
          type: integer
          minimum: 0
          description: Number of item results with `ok=true`.
        failed:
          type: integer
          minimum: 0
          description: Number of item results with `ok=false`.
```

- [ ] Build the Rust API crate to verify code generation:

```bash
cargo build -p fabro-api
```

Expected result: succeeds and exposes `BatchDeleteRunsRequest`, `BatchDeleteRunsResponse`, `BatchDeleteRunsResult`, `BatchDeleteRunsResultOutcome`, and `BatchDeleteRunsSummary` through `fabro_api::types`.

- [ ] Regenerate the TypeScript client:

```bash
cd lib/packages/fabro-api-client && bun run generate
```

Expected result: generated `RunsApi` includes `batchDeleteRuns`, and generated models include the new batch delete request/result/response/summary types.

### Task 3: Refactor Delete Internals For Shared Single And Batch Use

**Files:**
- Modify `lib/crates/fabro-server/src/server.rs`
- Modify `lib/crates/fabro-server/src/server/handler/runs.rs`
- Modify `lib/crates/fabro-server/src/server/handler/system.rs`

- [ ] Change `DeleteRunOutcome` in `server.rs` to:

```rust
enum DeleteRunOutcome {
    Deleted,
    AlreadyAbsent,
    Preserved(DeleteRunResponse),
}
```

- [ ] Change `delete_run_internal` to return `Result<DeleteRunOutcome, ApiError>`.
  - When `force` is false, propagate `reject_active_delete_without_force` as `ApiError`.
  - When the run is absent before deletion and no live managed run exists, return `DeleteRunOutcome::AlreadyAbsent` after idempotent cleanup succeeds.
  - When delete succeeds without preservation, return `DeleteRunOutcome::Deleted`.
  - When sandbox preservation applies, keep returning `DeleteRunOutcome::Preserved(DeleteRunResponse { deleted: true, sandbox_preserved: true, sandbox })`.

- [ ] Convert helper functions from `Response` errors to `ApiError` errors:
  - `delete_run_sandbox_resource`
  - `reject_active_delete_without_force`
  - any `remove_run_dir`, `state.store.delete_run`, or `artifact_store.delete_for_run` mapping inside the delete path

- [ ] Update single delete handler in `handler/runs.rs`:

```rust
match delete_run_internal(&state, id, query.force).await {
    Ok(DeleteRunOutcome::Deleted | DeleteRunOutcome::AlreadyAbsent) => {
        StatusCode::NO_CONTENT.into_response()
    }
    Ok(DeleteRunOutcome::Preserved(response)) => (StatusCode::OK, Json(response)).into_response(),
    Err(error) => error.into_response(),
}
```

- [ ] Update system prune in `handler/system.rs`:

```rust
for run_id in &prune_plan.run_ids {
    if let Err(error) = delete_run_internal(&state, *run_id, true).await {
        return error.into_response();
    }
}
```

- [ ] Run existing single-delete and prune tests:

```bash
cargo nextest run -p fabro-server delete_run prune_runs
```

Expected result: existing single delete behavior still passes.

### Task 4: Implement Batch Delete Handler

**Files:**
- Modify `lib/crates/fabro-server/src/server/handler/lifecycle.rs`

- [ ] Import the generated batch delete types from `super::super`:

```rust
BatchDeleteRunsRequest, BatchDeleteRunsResponse, BatchDeleteRunsResult,
BatchDeleteRunsResultOutcome, BatchDeleteRunsSummary, DeleteRunOutcome, DeleteRunSandbox,
```

- [ ] Add the route next to batch archive/unarchive:

```rust
.route("/runs/delete", post(batch_delete_runs))
```

- [ ] Generalize `validate_batch_run_ids` so it accepts `Vec<String>` or a borrowed slice of raw IDs.
  - Keep exactly the same behavior and messages:
    - `run_ids must contain at least one run ID.`
    - `run_ids must contain no more than 250 run IDs.`
    - `run_ids contains invalid run ID: {raw}`
    - `run_ids must not contain duplicate IDs.`

- [ ] Add `batch_delete_runs`:

```rust
async fn batch_delete_runs(
    _auth: RequiredUser,
    State(state): State<Arc<AppState>>,
    Json(request): Json<BatchDeleteRunsRequest>,
) -> Response {
    let force = request.force.unwrap_or(false);
    let ids = match validate_batch_run_id_strings(request.run_ids) {
        Ok(ids) => ids,
        Err(err) => return err.into_response(),
    };

    let mut results = Vec::with_capacity(ids.len());
    for id in ids {
        results.push(batch_delete_run_item(&state, id, force).await);
    }

    let requested = results.len() as u64;
    let succeeded = results.iter().filter(|result| result.ok).count() as u64;
    (
        StatusCode::OK,
        Json(BatchDeleteRunsResponse {
            results,
            summary: BatchDeleteRunsSummary {
                requested,
                succeeded,
                failed: requested - succeeded,
            },
        }),
    )
        .into_response()
}
```

- [ ] If generated `BatchDeleteRunsRequest.force` is a plain `bool` rather than `Option<bool>`, use `let force = request.force;` and keep the OpenAPI default as the source of truth.

- [ ] Add `batch_delete_run_item`:

```rust
async fn batch_delete_run_item(
    state: &Arc<AppState>,
    id: RunId,
    force: bool,
) -> BatchDeleteRunsResult {
    match delete_run_internal(state, id, force).await {
        Ok(DeleteRunOutcome::Deleted) => batch_delete_success(
            id,
            BatchDeleteRunsResultOutcome::Deleted,
            None,
        ),
        Ok(DeleteRunOutcome::AlreadyAbsent) => batch_delete_success(
            id,
            BatchDeleteRunsResultOutcome::AlreadyAbsent,
            None,
        ),
        Ok(DeleteRunOutcome::Preserved(response)) => batch_delete_success(
            id,
            BatchDeleteRunsResultOutcome::SandboxPreserved,
            Some(response.sandbox),
        ),
        Err(error) => {
            let outcome = match error.status() {
                StatusCode::CONFLICT => BatchDeleteRunsResultOutcome::Conflict,
                _ => BatchDeleteRunsResultOutcome::Error,
            };
            BatchDeleteRunsResult {
                run_id: id.to_string(),
                ok: false,
                outcome,
                sandbox: None,
                error: Some(error.into_response_entry()),
            }
        }
    }
}
```

- [ ] Add `batch_delete_success`:

```rust
fn batch_delete_success(
    id: RunId,
    outcome: BatchDeleteRunsResultOutcome,
    sandbox: Option<DeleteRunSandbox>,
) -> BatchDeleteRunsResult {
    BatchDeleteRunsResult {
        run_id: id.to_string(),
        ok: true,
        outcome,
        sandbox,
        error: None,
    }
}
```

- [ ] Run the server batch delete tests:

```bash
cargo nextest run -p fabro-server batch_delete
```

Expected result: all new batch delete server tests pass.

### Task 5: Add Web Helper Support

**Files:**
- Modify `apps/fabro-web/app/lib/run-actions.ts`
- Modify `apps/fabro-web/app/lib/run-actions.test.ts`

- [ ] Import generated delete batch types in `run-actions.ts`:

```ts
import type {
  BatchDeleteRunsRequest,
  BatchDeleteRunsResponse,
  BatchRunLifecycleRequest,
  BatchRunLifecycleResponse,
  ErrorResponseEntry,
  Run,
} from "@qltysh/fabro-api-client";
```

- [ ] Add the helper next to `archiveRuns` and `unarchiveRuns`:

```ts
export async function deleteRuns(
  runIds: string[],
  force = false,
  request?: Request,
): Promise<BatchDeleteRunsResponse> {
  try {
    const body = { run_ids: runIds, force } as unknown as BatchDeleteRunsRequest;
    return await apiData(() => runsApi.batchDeleteRuns(body, requestSignalOptions(request)));
  } catch (error) {
    throw lifecycleActionErrorFromError(error);
  }
}
```

- [ ] Add `deleteRuns sends one batch request and parses results` to `run-actions.test.ts`.
  - Stub a `200` body with `deleted` and `already_absent` results.
  - Assert one request was sent.
  - Assert method is `POST`.
  - Assert URL is `/api/v1/runs/delete`.
  - Assert JSON body is `{ run_ids: ["run-1", "run-missing"], force: false }`.
  - Assert parsed summary and outcomes.

- [ ] Add `deleteRuns sends force when requested`.
  - Call `deleteRuns(["run-1"], true)`.
  - Assert JSON body is `{ run_ids: ["run-1"], force: true }`.

- [ ] Add `deleteRuns preserves request-level error envelopes`.
  - Stub `400` with the standard `errors` array.
  - Assert `expectLifecycleError(deleteRuns([]))` returns the parsed status and errors.

- [ ] Run the focused web helper tests:

```bash
cd apps/fabro-web && bun test app/lib/run-actions.test.ts
```

Expected result: all run action helper tests pass.

### Task 6: Final Verification

**Files:**
- No additional source files unless verification exposes a bug in the implementation.

- [ ] Run formatting check:

```bash
cargo +nightly-2026-04-14 fmt --check --all
```

Expected result: succeeds.

- [ ] Run focused server tests:

```bash
cargo nextest run -p fabro-server batch_delete delete_run prune_runs
```

Expected result: succeeds.

- [ ] Run Rust API generation/build check:

```bash
cargo build -p fabro-api
```

Expected result: succeeds.

- [ ] Run frontend helper tests:

```bash
cd apps/fabro-web && bun test app/lib/run-actions.test.ts
```

Expected result: succeeds.

- [ ] Run frontend typecheck:

```bash
cd apps/fabro-web && bun run typecheck
```

Expected result: succeeds.

- [ ] Inspect generated/client changes before committing:

```bash
git diff -- docs/public/api-reference/fabro-api.yaml lib/crates/fabro-server apps/fabro-web/app/lib/run-actions.ts apps/fabro-web/app/lib/run-actions.test.ts lib/packages/fabro-api-client
```

Expected result: diff contains only the batch delete endpoint, generated client updates, server implementation, and helper tests.

## Acceptance Criteria

- `POST /api/v1/runs/delete` exists in the OpenAPI spec and generated TypeScript client.
- The endpoint processes 1-250 unique run IDs in order.
- The endpoint returns `200` for valid batch requests with ordered per-item results.
- Active runs fail with `conflict` unless `force` is true.
- Missing valid IDs return successful `already_absent`.
- Preserved sandboxes return successful `sandbox_preserved` with handoff details.
- Existing `DELETE /api/v1/runs/{id}` behavior remains unchanged.
- No bulk delete UI is added as part of this plan.


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
  - Model: gpt-5.5, 253.1k tokens in / 27.6k out


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