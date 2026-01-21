# Codex Task Tool Plan

## Goals
- Ensure sc-codex task tool and harness behavior stays aligned with PQA expectations.
- Fix CI failures introduced by new validation scripts merged from develop.
- Improve HTML reporting for sc-codex fixture tests (clarity, parity, observability).

## Active Work Plan
1) CI Stability (Done)
   - Fix validation failures from new scripts (schemas artifact support, codex allowlist).
   - Update registry/schema/docs and regenerate reports.
   - Re-run unit tests + sc-codex fixture tests.

2) HTML Report Improvements (Next)
   - Expectations section readability and layout.
   - Timeline tool call formatting (pretty command + JSONL output).
   - Log Warnings & Errors: show full raw log context with highlight.
   - Report path readability and layout in header.

3) Validation/Observability Rules (Ongoing)
   - Ensure `.claude/state/logs/*/*` are captured and visible in reports.
   - Keep JSON/HTML report parity (no hidden data).
   - Enforce `allow_warnings_reason` when suppressing warnings.

## Latest Status
- CI validations updated and passing.
- sc-codex schemas promoted to first-class artifacts.
- sc-codex package docs added (README/CHANGELOG/LICENSE).
- Unit tests and sc-codex fixture tests passed; HTML report generated.

## Next Steps (Immediate)
- Resume HTML report improvements for sc-codex fixtures.
- Review sc-codex HTML report output for clarity and parity.
