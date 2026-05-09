Goal: Exercise run file scopes with committed and uncommitted sandbox changes

## Completed stages
- **committed**: succeeded
  - Model: claude-sonnet-4-6, 582 tokens in / 118 out


Run exactly one Bash tool command with timeout_ms set to 310000 or higher: printf '
Modified by second node before sleeping at %s
' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> docs/internal/live-run-files-scope-tracked.md && sleep 300. Wait for it to return. Do not run any other commands, do not read files, and do not edit anything else. Then reply with the single word done and stop.