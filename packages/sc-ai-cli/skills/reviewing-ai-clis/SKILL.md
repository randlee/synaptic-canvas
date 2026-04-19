---
name: reviewing-ai-clis
version: 0.10.0
description: Critically review an existing CLI, MCP wrapper, or CLI plan for AI-first contract quality. Use when evaluating whether a CLI is JSON-first, has an MCP-ready contract seam without JSON reshaping, auditably models state changes, uses stateful simulator-backed testing for external integrations, and returns typed actionable errors. Do not use for general style review or human-first shell UX review.
---

# Reviewing AI CLIs

Use this skill for critical review of existing CLIs, MCP wrappers, or plans for AI-facing CLIs. The goal is to find contract weaknesses that make the tool unreliable for agents and automation.

## Scope

Use this skill when reviewing:
- an implemented CLI
- an MCP wrapper around a CLI or shared operation layer
- a design or plan for a new CLI
- test strategy for a CLI that integrates with external systems

Do not use this skill for:
- general code style review
- package ecosystem review unrelated to the CLI contract
- human-first usability review unless it interferes with the machine contract

## Review Priorities

Review in this order:
1. JSON contract completeness and stability
2. Error contract quality, including typed or discriminated-union style results
3. MCP compatibility without request or response reshaping
4. Auditability of mutating commands through corresponding read commands
5. Simulator-backed testing for external integrations
6. Human-readable mode only as a secondary concern

## References

- `references/review-checklist.md` — critical review checklist for implemented CLIs
- `references/error-review.md` — deep review rubric for typed, actionable errors
- `references/plan-review.md` — how to review CLI designs before implementation
- `../creating-ai-clis/references/example-repos.md` — example patterns and non-patterns
  This is a deliberate cross-skill dependency; if `creating-ai-clis` moves or is renamed, this reference must be updated.

If the target is implemented code, read `review-checklist.md` first and then `error-review.md`. If the target is a plan or architecture document, read `plan-review.md` first and then use relevant checklist items as design commitments. Use `../creating-ai-clis/references/example-repos.md` to calibrate the bar, not to excuse weaker designs. Review at the contract level first; do not load language-specific references unless a concrete implementation detail requires it.

## Agent Delegation

This skill operates directly in the main session on the target CLI, wrapper, or plan. It does not delegate to background agents or sub-agents.

## Workflow

1. Determine whether the target is:
   - implemented CLI
   - MCP wrapper
   - CLI design or plan
2. Review the machine contract before reviewing human-readable output.
3. Identify whether every command exposes a usable JSON contract and whether structured request models are defined where commands accept structured input.
4. Identify whether success and error results are typed, stable, and actionable.
5. Verify that human-readable mode is not richer than JSON mode for machine-significant data.
6. For any mutating command, verify that a corresponding read command exists to confirm resulting state.
7. If the tool integrates with external systems, check whether realistic stateful simulator-backed tests exist below the CLI layer, including seeded data and negative-path controls. Load `designing-cli-simulators` only when the simulator design itself needs deeper review.
8. If an MCP wrapper exists or is planned, verify that it reuses the same request and response models without reshaping the business payload.
9. Report findings first, ordered by severity, with file references when reviewing code and section references when reviewing plans.

## Output Expectations

The review output should:
- list findings first, ordered by severity
- call out missing or weak JSON contracts
- call out weak error contracts separately from general validation concerns
- identify whether MCP compatibility is real or only claimed
- identify whether mutation auditability is present or absent
- identify whether simulation is realistic or only mock-deep
- extract reusable patterns for the CLI creation skill when present
