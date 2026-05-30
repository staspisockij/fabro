Reviewed the branch diff against `origin/feat/settings-environments-crud` with three parallel review agents.

Findings:
- Code reuse / quality agents both flagged a possible duplicate `test_principal()` in `lib/crates/fabro-cli/tests/it/cmd/support.rs`.
- I checked the current file: it already imports and uses `fabro_types::test_support::test_principal`; there is no local duplicate helper. So this was a false positive from the branch diff context.
- Efficiency agent found no actionable issues.
- Forbidden nullable/anonymous sweep only found unrelated `TodoUpdatedProps.subject` and web auth `idp_subject` fields.

No code changes were needed.

Verification run:
- `cargo check -q --workspace` ✅
- `cd apps/fabro-web && bun run typecheck` ✅