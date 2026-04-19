# Prompt Rewrite Patterns

Use these transformations when editing prompts.

## Remove permissive severity filters

Replace patterns like:
- "Only report issues that truly matter"
- "Focus on blockers and important findings"
- "Minor issues may be omitted"

With:
- "Report all real findings that are actionable and within scope."
- "Fix straightforward findings directly when safe."
- "Do not suppress findings merely because they are non-blocking or minor."

## Remove ask-first behavior for easy fixes

Replace patterns like:
- "Ask the user before fixing small issues"
- "Stop when you encounter adjacent problems"

With:
- "Fix straightforward adjacent issues encountered in the same area unless doing so would materially expand scope."
- "Escalate only when the remaining path requires a real decision, approval, or major trade-off."

## Remove technical-debt escape hatches

Replace patterns like:
- "Consider tracking as technical debt"
- "Create follow-up tasks for minor issues"

With:
- "Do not propose technical debt or backlog entries for issues that can reasonably be fixed now."
- "Use deferral only when the fix would require a major refactor or materially change the task."

## Remove pre-existing dismissal

Replace patterns like:
- "Do not report pre-existing issues unless worsened"
- "Focus only on regressions introduced by the current change"

With:
- "Do not dismiss issues as pre-existing when they are real, relevant, and encountered in the current work area."
- "Pre-existing status may be noted, but it does not justify ignoring the issue."
- "Do NOT dismiss violations as 'pre-existing' or 'not worsened.' Every violation found is a finding regardless of whether it predates this sprint. List each finding with file:line and a remediation note. The pre-existing/new distinction is informational only. It does not change severity or blocking status."

## Tighten escalation wording

Replace patterns like:
- "Ask the user when unsure"
- "Pause for direction if there are multiple options"

With:
- "Before escalating, analyze whether one option is the obvious low-risk correction."
- "Escalate only when options materially differ in product behavior, architecture, or risk."

## Add validation-backed stopping rules

Replace patterns like:
- "Implemented the change; testing not run"
- "Validation can be run later"
- "Regression remains"

With:
- "Run the full relevant validation suite and verify no regression before stopping."
- "Do not report 'I changed the code but did not run tests.'"
- "If validation fails, continue by fixing the issue or root-causing it before stopping."
- "Unless there is a real external blocker, keep working."

## QA-specific rewrites

Replace patterns like:
- "Only blockers fail the gate"
- "Non-blocking findings are advisory"

With:
- "Aggressively pursue quality violations and do not normalize them away."
- "Blocking findings fail the gate, but non-blocking findings should still be remediated when reasonable."
- "Do not use severity labels to justify avoidable carry-forward defects."
- "Do NOT dismiss violations as 'pre-existing' or 'not worsened.' Every violation found is a finding regardless of whether it predates this sprint. List each finding with file:line and a remediation note. The pre-existing/new distinction is informational only. It does not change severity or blocking status."

## Orchestration-specific rewrites

Replace patterns like:
- "Summarize findings and wait for direction"
- "Collect debt items for later"

With:
- "Route findings toward closure and keep working until a real decision is required."
- "Do not convert ordinary fixable findings into backlog without a concrete scope or risk rationale."
- "Do NOT dismiss quality findings as 'pre-existing' or 'not worsened.' Treat findings as work that should move toward closure, not as metadata to classify and drop."
- "The expectation is that quality findings are fixed unless a real scope, architecture, or approval boundary prevents it."
- "Require executed validation after code changes, not just a statement of intent."
- "Do not allow the workflow to stop with unresolved regression unless the root cause and exact blocker are stated."

## Quick audit checklist

When reviewing a prompt, search for wording around:
- only
- blocker
- important
- minor
- defer
- technical debt
- pre-existing
- ask user
- stop and ask
- not worsened
- backlog

If those terms appear, verify they do not create a permissive escape hatch.
