# Repo Target Map

This file lists likely current targets in this repository for prompt hardening. It is a convenience map, not a source of truth. Re-check the actual files before editing.

## Coding and implementation agents

Likely targets:
- `packages/sc-rust/agents/rust-developer.md`
- `.claude/agents/issue-fix-agent.md`
- `packages/sc-github-issue/agents/sc-github-issue-fix.md`
- `.claude/agents/ci-fix-agent.md`
- `packages/sc-ci-automation/agents/ci-fix-agent.md`

Look for:
- ask-before-fix wording
- test-failure prompts that stop too early
- technical-debt or TODO escape hatches
- uncertainty language that escalates before exhausting reasonable fixes

## QA and review agents

Likely targets:
- `packages/sc-rust/agents/rust-code-reviewer.md`
- `packages/sc-rust/agents/rust-qa-agent.md`
- `.claude/agents/skill-architecture-review.md`
- `.claude/agents/skill-implementation-review.md`
- `.claude/agents/skill-metadata-storage-review.md`
- `.claude/agents/ci-test-agent.md`
- `.claude/agents/ci-validate-agent.md`
- `packages/sc-ci-automation/agents/ci-test-agent.md`
- `packages/sc-ci-automation/agents/ci-validate-agent.md`

Look for:
- blocker-only framing
- high-confidence filters that suppress real issues
- "only report issues that matter" language
- pre-existing dismissal
- advisory wording that normalizes avoidable carry-forward defects

## Orchestration and routing agents

Likely targets:
- `.claude/agents/ci-root-cause-agent.md`
- `.claude/agents/issue-intake-agent.md`
- `.claude/agents/skill-planning-agent.md`
- `packages/sc-ci-automation/agents/ci-root-cause-agent.md`
- `packages/sc-github-issue/agents/sc-github-issue-intake.md`

Look for:
- summarize-and-wait behavior
- backlog or follow-up creation as a default response
- unnecessary human escalation
- language that stops once blockers are cleared instead of closing all reasonable findings

## Notes

- Some agents may span more than one category.
- When in doubt, classify by behavior, not file name.
- If the repo adds new agents later, extend this map rather than treating it as exhaustive.
