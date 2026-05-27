Implemented the worker control bus plan end-to-end.

### What changed

- Added shared protocol support:
  - `run.pause` / `run.unpause`
  - `WorkerControlDeliveryFrame { id, envelope }`

- Added server-side worker control bus:
  - `WorkerControlBus` abstraction
  - opaque `WorkerControlMessageId`
  - `WorkerControlCursor::{Start, After(...)}`
  - `LocalWorkerControlBus` with ordered replay, `after` resume, bounded retention, invalid-cursor detection, and cleanup

- Added server WebSocket route:
  - `GET /api/v1/runs/{id}/worker/control-stream`
  - worker-JWT-only and run-scoped
  - rejects missing/terminal/archived runs before upgrade
  - invalid cursor returns HTTP 410 before upgrade
  - sends JSON delivery frames
  - explicit ping/pong liveness

- Removed worker stdin JSONL runtime transport:
  - server now publishes all controls through the bus
  - `__run-worker` subprocess stdin is configured as null
  - no `control_tx` / stdin control pump remains

- Added CLI worker WebSocket control manager:
  - connects before start/resume for non-terminal runs
  - supports HTTP → WS, HTTPS → WSS, and Unix socket targets
  - reconnects with exponential backoff capped at 5s
  - first connect omits `after`; reconnect uses last fully applied id
  - applies frames only once by delivery id
  - updates `last_applied_id` only after successful application
  - handles pause/unpause/cancel/answer/steer/interrupt/pair controls
  - explicit ping/pong liveness and timeout
  - HTTP 410 / `invalid_cursor` close is fatal control-channel loss

- Added/updated tests across protocol, bus, route, CLI, server transport, and lifecycle/cancel flows.

- Fixed a lifecycle regression where cancellation at a human gate could race with the detached completion guard and emit a duplicate terminal failure.

### Verification run

Passed:

- `cargo nextest run -p fabro-interview control_protocol`
- `cargo nextest run -p fabro-server worker_control`
- `cargo nextest run -p fabro-cli runner`
- `cargo nextest run -p fabro-server worker_command`
- `cargo nextest run -p fabro-cli --test it runner`
- `cargo nextest run -p fabro-server --features test-support --test it lifecycle`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `git diff --check`

Also confirmed by grep:

- no worker-control stdin pump / `control_tx` remnants in server or CLI runtime code
- no `Latest` worker-control cursor
- no Redis dependency/config/runtime path added, only future-backend comments in the bus contract.