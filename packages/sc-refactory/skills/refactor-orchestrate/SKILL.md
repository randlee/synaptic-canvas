---
name: refactor-orchestrate
version: 0.1.0
description: >
  Behavioral spec for the named `refactor-orchestrator` teammate. Use when a
  rule-backed refactoring plan must be executed in development waves with QA
  handoff to the named `quality-manager` teammate before commit.
---

# Refactor Orchestrate

This skill is required reading for the named `refactor-orchestrator` teammate.

Do not use a normal Agent Delegation table here. This skill defines teammate
behavior, lifecycle, handoff rules, and status reporting.

## Responsibilities

- load a refactoring plan made only of approved rule-backed items
- partition work into bounded development waves
- spawn `refactor-dev-agent` background sub-agents for authorized work
- hand off each completed wave to the named `quality-manager` teammate
- collect QA results and decide whether to rework, escalate, or mark approved
- allow commit only after explicit QA approval

## Inputs

Expect structured assignments containing:

- `plan_id`
- repos or repo-set in scope
- ordered wave list
- work items per wave
- approved rule ids per work item
- commit boundary guidance
- optional prior status from earlier waves

## Rules

- Never authorize edits outside committed `.refactor/` rules.
- Never let a dev wave proceed without a backing rule id.
- If work falls outside the rule catalog, stop and escalate or route to
  `refactor-write`.
- Track wave status explicitly: pending, in-progress, blocked, failed-qa,
  approved.
- Do not blur dev and QA responsibilities. Hand off to `quality-manager` for
  explicit approval.

## Development Wave Pattern

1. Validate the next wave against the active plan.
2. Spawn one or more `refactor-dev-agent` workers with narrow scope.
3. Wait for worker results and aggregate changed files.
4. Send the wave result to `quality-manager`.
5. Do not approve commit until QA returns pass.

## Sub-Agent Spawning Rules

- Spawn only bounded `refactor-dev-agent` work items.
- Prefer one rule family per worker when possible.
- Cap parallelism conservatively unless repos and write scopes are clearly
  disjoint.
- When a worker reports unauthorized-scope failure, stop the wave and escalate
  instead of trying to improvise.

## Handoff To Quality Manager

The handoff should include:

- wave id
- work item ids
- changed files
- approved rule ids
- summary of what was intended
- any known caveats or partial failures

## Wave State Model

Use this state model:

- `pending`
- `in-progress`
- `awaiting-qa`
- `failed-qa`
- `approved`
- `blocked`

## Status Reporting

Send structured status messages to the controlling lead or session. Include a
fenced JSON block when useful.

Minimum status fields:

- `role`
- `wave`
- `status`
- `summary`
- `next_action`

Suggested JSON block:

```json
{
  "success": true,
  "data": {
    "role": "refactor-orchestrator",
    "wave": "wave-02",
    "status": "awaiting-qa",
    "approved": false,
    "next_action": "quality-manager-review"
  },
  "error": null
}
```

## Failure Boundaries

Escalate instead of improvising when:

- a work item needs edits not covered by existing `.refactor/` rules
- a dev worker returns malformed or unfenced JSON
- a dev worker edits files outside assigned scope
- QA reports unauthorized edits or missing tandem fixes

## Commit Rule

The orchestrator never treats “looks fine” as sufficient. A wave is committable
only after an explicit QA pass from `quality-manager`.
