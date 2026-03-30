---
name: coding-agent-hardening
version: 0.1.0
description: Harden coding, QA, and orchestration agent prompts so they fix issues autonomously instead of letting findings pass through as minor, pre-existing, non-blocking, or technical debt. Use when editing existing agent prompts, review instructions, or orchestration workflows to remove permissive issue-handling behavior and tighten escalation criteria.
---

# Coding Agent Hardening

This skill is for editing existing agent prompts and orchestration instructions so they stop normalizing avoidable defects. It is not a general review skill. It is a prompt-hardening skill for agent behavior.

## Scope

Use this skill when modifying prompts for:
- coding or implementation agents
- QA or review agents
- orchestration, triage, planning, or fix-routing agents

The goal is to eliminate default behaviors that allow issues to survive under labels like:
- minor
- non-blocking
- pre-existing
- technical debt
- needs direction, when no real decision exists
- changed code without validation
- regression reported without fix or root cause

## Core Policy

Harden prompts toward a fix-first default:
- simple findings should be fixed, not escalated
- non-blocking findings should still be fixed when reasonable in the current pass
- pre-existing issues should not be ignored just because they predate the current change
- minor findings should not disappear into backlog language by default
- agents should exhaust reasonable alternatives before stopping for user direction
- technical debt should not be created as an escape hatch for small or moderate fixes
- code changes should be followed by relevant validation before the agent stops
- regressions should be fixed or root-caused before the agent stops

Human escalation is still allowed, but only for real decisions:
- major architectural trade-offs
- mutually exclusive product choices
- destructive or irreversible operations
- broad refactors whose blast radius materially changes schedule or scope

## References

- `references/hardening-policy.md` — normative rewrite policy for issue handling and escalation
- `references/prompt-rewrite-patterns.md` — concrete rewrite patterns to remove permissive wording
- `references/agent-category-guidance.md` — category-specific hardening rules for coding, QA, and orchestration agents
- `references/repo-target-map.md` — likely current repo targets by agent category

Read `hardening-policy.md` first. Then read `agent-category-guidance.md` for the target agent type. Use `prompt-rewrite-patterns.md` while editing the actual prompt text. Read `repo-target-map.md` only when you need help identifying likely target agents in this repository.

## Workflow

When hardening an existing agent prompt:

1. Identify the agent category:
   - coding
   - QA/review
   - orchestration/planning

2. Read the applicable sections in:
   - `references/hardening-policy.md`
   - `references/agent-category-guidance.md`

3. Scan the target prompt for permissive patterns such as:
   - blocker-only language
   - confidence thresholds that suppress too many real findings
   - wording that asks before fixing obvious issues
   - "pre-existing" dismissal language
   - automatic deferral to technical debt or backlog
   - escalation on false decisions where a reasonable fix path exists

4. Rewrite the prompt so the agent:
   - fixes straightforward issues autonomously
   - reports all meaningful findings instead of filtering to a tiny subset
   - treats QA findings as remediation input, not merely triage metadata
   - keeps working until it hits a true decision or a real boundary
   - does not stop after code changes without running relevant validation
   - does not report regression without fixing it or root-causing it first

5. Preserve legitimate constraints:
   - safety boundaries
   - destructive-operation confirmations
   - scope limits that prevent major unplanned refactors

6. Re-read the final prompt and ask:
   - would this agent still stop on a fake decision?
   - would it still treat "minor" as "ignore"?
   - would it still create technical debt instead of fixing an issue now?

## Category Guidance

### Coding agents

Default expectation:
- fix small and medium issues directly while already in the code
- do not ask whether to fix trivial adjacent defects
- do not suggest backlog/technical debt for reasonable fixes
- do not stop after edits without running relevant tests or validation
- if validation regresses, keep working until the regression is fixed or root-caused

### QA and review agents

Default expectation:
- surface all real findings, not just blockers and "important" ones
- do not down-rank issues into irrelevance if they are cheap to fix now
- do not tolerate "pre-existing" dismissal

### Orchestration agents

Default expectation:
- treat findings as work to close, not merely classify
- prefer "fix now" over "defer" unless there is a genuine project-level trade-off
- stop only when the remaining path requires a real decision or approval
- require executed validation after code changes, not just claimed intent to validate
- require regression to be resolved or root-caused before allowing the workflow to stop

## Output Expectations

When using this skill to update an agent prompt:
- state which permissive behaviors were removed
- state which replacement behaviors were added
- note any remaining escalation points and why they are real

Do not describe the prompt as hardened unless the old defer/ignore behaviors were explicitly removed.
