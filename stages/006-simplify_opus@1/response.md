Cut 60 lines off the migration module while fixing a real bug. Summary of fixes from the review:

**Fixes applied:**
1. **Correctness bug** (Agent 2 #1): `skip_clone = false` (the default) was wrongly rejected as unsupported. Now only non-bool values fail. Added test `explicit_skip_clone_false_is_accepted_as_default`.
2. **Code reuse** (Agent 1 #1, #2): Removed custom `is_table_like` / `copy_table` branching; now uses toml_edit's built-in `Item::is_table_like()` and `Item::as_table_like()` + `TableLike` trait.
3. **Duplicate helpers** (Agent 1 #3): Collapsed `path_table` and `path_table_in_table` into a single `ensure_table` that operates on `&mut Table`; callers use `doc.as_table_mut()`.
4. **Stringly-typed** (Agent 2 #3): Replaced raw `"daytona"` / `"docker"` matching with `EnvironmentProvider::from_str` + `IntoStaticStr`; eliminated the awkward `migrate_skip_clone` + `reject_provider_table` mirror-dispatch.
5. **Trivial wrappers** (Agent 1 #9, Agent 2 smaller): Dropped `set_value` and `set_item`; callers use `table[key] = …` directly.
6. **Efficiency** (Agent 3 main finding): `migrate_settings_path` now returns the already-parsed `SettingsLayer` instead of returning a string for the caller to re-parse — eliminates a redundant serde pass on the migration path.
7. **Double-report bug** (Agent 2 smaller): `item_path_keys` now stops after reporting an empty array-of-tables instead of re-pushing per element.
8. **Dead-code cleanup** (Agent 1 #4): Trimmed `unwrap_or("settings.toml")` dead fallback and computed `file_name` once before the loop in `next_backup_path`.
9. **Dead-code warning**: Made `backup_path` a `#[cfg(test)]` field since it's only used in tests, avoiding a `dead_code` warning in non-test builds without sprinkling `#[allow]`.

**Skipped (deliberate):**
- Adding a dedicated `Error::WriteFile` variant and converting `MigrationFailure` into an Error variant (Agent 1 #5, #6) — out of scope for a soon-to-be-removed module.
- Promoting `next_backup_path` to `fabro-util` (Agent 1 #4, #7) — this file is going away pre-v1.0.
- `user.rs` test fix concerns (Agent 2 #5) — works correctly, leave alone.
- Test fixture builder consolidation — legacy TOML shape is the point of the tests.

**Verification:** `cargo nextest run -p fabro-config` (216 pass), `cargo +nightly-2026-04-14 fmt --check --all` (clean), `cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` (clean).