Implemented the two-commit plan and committed both changes.

Commits:
- `43a12a3e1 refactor(auth): remove anonymous principal`
- `9ae80132d refactor(runs): require creator provenance`

Summary:
- Removed `Principal::Anonymous`; unauthenticated/invalid request state is now represented as `None`, with HTTP logs using `principal_kind="none"`.
- Made persisted run actors/provenance total:
  - `Run.created_by: Principal`
  - `RunSpec.provenance: RunProvenance`
  - `RunProvenance.subject: Principal`
  - `run.created` provenance required/non-null
- Updated OpenAPI and regenerated Rust/TS API outputs.
- Added `fabro-types::test_support` helpers behind `test-support`.
- Updated server/workflow/store projections, create/retry flows, demo principal, frontend UI/data assumptions, and test fixtures/snapshots.
- Final working tree is clean.

Verification run:
- `cargo build -p fabro-api`
- `cd lib/packages/fabro-api-client && bun run generate`
- `cd lib/packages/fabro-api-client && bun run typecheck`
- `cd apps/fabro-web && bun run typecheck && bun test && bun run build`
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `cargo build --workspace`
- `cargo nextest run --workspace`
- `cargo nextest run -p fabro-server`
- Final sweeps for anonymous principal and nullable creator/provenance patterns:
  - only unrelated `crossorigin="anonymous"` and unrelated todo/web-auth `subject` fields remain.

Notes:
- `cargo insta pending-snapshots` could not run because `cargo-insta` is not installed in this environment; I checked for pending `*.snap.new` files and found none.
- Manual browser/server E2E verification was not performed in this environment.