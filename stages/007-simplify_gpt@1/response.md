Reviewed the branch against `origin/main`, launched the three requested parallel review agents, and did a direct focused pass over the changed auth/tool/pair code.

Found and fixed one small code-reuse cleanup:

- Consolidated repeated `fabro_run_pair is not available` default backend error construction in `lib/crates/fabro-tool/src/common.rs` into `pair_tool_unavailable_error()`.

Verification run:

- `cargo nextest run -p fabro-tool -p fabro-workflow -p fabro-server -p fabro-cli` — passed before the cleanup.
- `cargo nextest run -p fabro-tool` — passed after the cleanup.
- `cargo +nightly-2026-04-14 fmt --check --all` — passed.
- `cargo +nightly-2026-04-14 clippy -q -p fabro-tool --all-targets -- -D warnings` — passed.

Only remaining working-tree change is the cleanup in `lib/crates/fabro-tool/src/common.rs`.