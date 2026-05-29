## Summary of cleanup

Aggregated findings from three parallel review agents and fixed the meaningful issues:

**High-priority fixes:**

1. **Race condition causing lost edits** (`automations-new.tsx`) — Both query agents flagged that `sourceFormKey` keyed on derived `name/repository/ref/workflow` plus a `hasSettings` flag would remount the form (and discard user edits) when the parallel `useRunSettings` query resolved after `useRun`. Fixed by:
   - Waiting for both queries to settle before mounting the form
   - Reducing the key to `from-run:${fromRunId}` so SWR revalidation can't trigger spurious remounts
   - Deleted the `sourceFormKey` helper

2. **Parameter sprawl in `makeRunSummary`** (`run-detail.test.ts`) — The function had grown to 6 positional args (most `any`-typed and defaulting to `null`). Converted to an options bag and updated all call sites.

**Medium-priority fixes:**

3. **Redundant default fields in `automationFormValuesFromRun`** (`automation-form.tsx`) — Removed `description`, `enabled`, `manualEnabled`, `scheduleEnabled`, `cron`, and `ref` fallback since they're already provided by the `...EMPTY_AUTOMATION_FORM` spread. The function is now significantly tighter.

4. **Duplicated test helper** (`run-detail.test.ts`) — Collapsed `findButtonByText` to delegate to `findButtonsByText` instead of duplicating the `findAll` predicate.

**Skipped:**

- Extracting GitHub URL parsing to a shared lib — no other callers exist; keeping it co-located with its single consumer is fine for greenfield.
- `firstPresentString` helper — borderline; agent confirmed no existing equivalent and inlining would hurt readability.
- Test fixtures still use `any` — pre-existing pattern; not worth widening this diff.

**Verification:** All 31 tests pass in the focused test suite, `tsc` clean.