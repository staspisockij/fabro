All checks pass: `fabro-automation`, `fabro-api automation_round_trip`, `fabro-server` automation integration tests, web typecheck, api-client typecheck, `cargo fmt --check`, and `clippy -D warnings`.

## Summary of fixes applied

**Reuse / quality (web):**
- Created `apps/fabro-web/app/lib/automation.ts` with `findApiTrigger`, `findScheduleTrigger`, and `hasEnabledApiTrigger` — replaces five inline `triggers.find((t) => t.type === ...)` call sites across `automations.tsx`, `automation-detail.tsx`, and `automation-form.tsx`.
- Collapsed the `AutomationCard` `disabled` + `menuDisabled` props into a single `busy` prop; the run-button `disabled` is derived inside the card from `busy || !automation.apiEnabled`.
- Removed the redundant `!automation.apiEnabled` guard in `runAutomation` (already enforced by the button's `disabled`).
- `automation-detail.tsx` now uses the local `canRun` for the tooltip instead of re-reading `apiTrigger?.enabled`.

**Efficiency (web):**
- Hoisted `query.toLowerCase()` out of the filter callback in `automations.tsx`.

**Quality (Rust):**
- Renamed `persisted_toml_rejects_legacy_top_level_enabled` → `persisted_toml_rejects_unknown_top_level_fields` (greenfield app — no "legacy" migration story).
- Trimmed the redundant doc-comment on `Automation::enabled_api_trigger`.

**Skipped (with reasons):**
- Renaming the error code `automation_api_trigger_disabled` — the plan explicitly requires keeping it.
- Restoring the "at least one trigger enabled" form check — the plan explicitly removed it.
- Memoizing `mapAutomations`/`filtered` and lazy `CronParser` — micro-opts on bounded inputs, not worth the complexity.