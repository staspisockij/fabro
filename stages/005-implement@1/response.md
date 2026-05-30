Implemented the full two-commit plan and committed both changes.

Commits:
- `4be785588 refactor(auth): remove anonymous principal actor`
- `65cf44f8c refactor(runs): require creator provenance`

What changed:
- Removed anonymous principal usage in auth flow/API/frontend docs in commit 1.
- Made run creator/provenance total end-to-end in commit 2:
  - `Run.created_by: Principal`
  - `RunProvenance.subject: Principal`
  - `RunSpec.provenance: RunProvenance`
  - `RunCreatedProps.provenance: RunProvenance`
  - `Event::RunCreated.provenance: RunProvenance`
- Removed nullable/default/fallback run provenance handling.
- Updated run creation/retry/projection/event conversion flows.
- Added Rust and TS test fixture helpers for fake dev-token principals.
- Updated OpenAPI and regenerated generated clients.
- Updated internal event docs for required run-created provenance.
- Replaced stale fixtures/tests that used null/missing creator/provenance.

Validation completed:
- `cargo +nightly-2026-04-14 fmt --check --all`
- `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings`
- `cargo build --workspace`
- `cargo nextest run --workspace` — 6493 passed
- `cargo nextest run -p fabro-server` — 717 passed
- `cd apps/fabro-web && bun run typecheck && bun test && bun run build` — 508 frontend tests passed
- Final sweeps for anonymous principal and nullable run creator/provenance passed; remaining `subject: None` / anonymous references are unrelated todo/web-auth/telemetry/git/html cases.

Working tree is clean. Manual browser-based end-to-end verification was not run in this terminal environment.