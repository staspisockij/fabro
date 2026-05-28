Clippy is clean. The merge conflict was the only issue. My fix resolves it by accepting the upstream changes (automation_materializer imports) and dropping the no-longer-needed `IpAllowlistConfig` import that this branch already removed.

Summary:
- The verify step failed because the auto-merge from origin/main left conflict markers in `lib/crates/fabro-server/src/test_support.rs`.
- The conflict was between this branch's removal of `crate::ip_allowlist` and origin/main's addition of `crate::automation_materializer` imports.
- Resolved by keeping the new `automation_materializer` imports and dropping the obsolete `IpAllowlistConfig` import.
- `cargo check`, `cargo fmt`, and `cargo clippy --workspace --all-targets -- -D warnings` all pass.