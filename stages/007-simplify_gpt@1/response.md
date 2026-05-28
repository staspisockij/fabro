Review complete.

What I checked:
- Diff against merge base `a992a7d76...`
- Remaining references to removed IP allowlist symbols/settings outside archival/build output
- Key config/server/API/web/docs changes for cleanup issues
- Parallel review agents were launched for reuse, quality, and efficiency review; no actionable cleanup changes were needed.

No code changes were made during this review.

Verification passed:
- `cargo nextest run -p fabro-config -p fabro-types -p fabro-api -p fabro-server`
  - 1372 passed
- `cd apps/fabro-web && bun run typecheck`
  - passed
- Cleanup search:
  - `rg` found no remaining non-archival references to `ip_allowlist`, `trusted_proxy_count`, `github_meta_hooks`, `IpAllow`, `GitHubMetaResolver`, etc. excluding `target/` and archival docs.

Working tree is clean.