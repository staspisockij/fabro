All verify steps now pass:

- **Clippy**: clean
- **Tests**: 5480 passed, 182 skipped
- **Docs refresh**: regenerated cleanly
- **Docs check**: up to date

## Summary

Two stale tests in `lib/crates/fabro-cli/tests/it/cmd/mcp.rs` were out of sync with recent commits to the MCP server contract:

1. **Snapshot test `mcp_create_and_search_manage_real_runs_with_cli_auth`** (line 554): the inline insta snapshot still expected the old `goal` field, but commit `ab78422c` ("fix(mcp): bound search goal previews") replaced it with `goal_preview` + `goal_truncated`. Updated the snapshot to match the new shape.

2. **Test `mcp_search_includes_archived_runs_by_default`** (line 787): the test's name and assertions encoded the old behavior (archived runs returned by default), but commit `8774abd7` ("fix(mcp): hide archived runs by default") flipped the default. Renamed to `mcp_search_hides_archived_runs_by_default` and updated assertions: expects 1 run (active only), and asserts `archived == false` on all returned runs.