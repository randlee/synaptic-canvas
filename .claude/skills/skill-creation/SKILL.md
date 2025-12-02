---
name: skill-creation
description: Plan and review Claude Code skills/commands/agents with guided wizards and background agents aligned to v0.4 guidelines.
---

# Skill Creation (planning + review)

This skill runs two flows: planning (`/skill-plan`) and review (`/skill-review`). Keep the main conversation clean; heavy work runs in agents via Agent Runner with registry-based resolution.

## Planning Flow (wizard)
1) Confirm goal: new skill package vs update/version bump (capture desired version target if known).
2) Capture responsibilities + success criteria; list primary use cases.
3) Command UX: required args, options, `--help` text; defaults for `--name`, behavior of `--from` (seed from existing skill/plan), and `--template` (plan skeleton file).
4) Agents: propose candidate agents, inputs/outputs, fenced JSON envelopes, and registry versions.
5) File layout: commands under `.claude/commands`, skills under `.claude/skills/<name>/SKILL.md`, agents under `.claude/agents`, references/templates under `.claude/references` (if needed) for easy testing before packaging.
6) Statusing: mark plan as Preliminary, then Proposed after user confirms; generate 40–80 line overview with full plan path when user approves (Approved).

### Implementation notes
- Use Agent Runner; resolve agents by name+version from `.claude/agents/registry.yaml`.
- Store plans by default in `plans/<name>.md`; allow override when user supplies a path or `--template`.
- If `--from` is set, load referenced artifact(s) and summarize key facts into the plan.
- Maintain concise outputs; omit tool traces.

### Agent delegation (planning)
- Invoke `skill-planning-agent` with collected inputs. Require fenced JSON output with minimal envelope:
```
```json
{ "success": true, "data": { "summary": "...", "actions": [] }, "error": null }
```
```
- If plan incomplete, include open questions and next actions in the overview; otherwise provide summary + full plan path.

## Review Flow
1) Identify target (name/path) and scope (command|skill|agent|all; default all).
2) Ask user where to write the report (default `reports/skill-reviews/<target>-report.md`; if unavailable, offer `.tmp/skill-reviews/`).
3) Ensure the chosen report directory exists (create it if missing) before writing.
4) Invoke `skill-review-agent` to evaluate against `docs/claude-code-skills-agents-guidelines-0.4.md` and registry/version rules.
5) Present concise findings; if `--fix`, include suggested edits/snippets but do not write files.

### Agent delegation (review)
- Require fenced JSON output:
```
```json
{ "success": true, "data": { "issues": [{ "severity": "error", "path": "...", "rule": "..." }], "summary": "..." }, "error": null }
```
```
- Ensure checks: version frontmatter present, registry alignment, fenced JSON outputs, minimal envelopes, safety/approval notes, progressive disclosure (SKILL body lean with references).

## Safety
- Creation of plan/review files is allowed; avoid destructive repo changes.
- Explicitly ask before writing reports to a user-provided location; default to temp path to avoid clutter.
- Keep outputs concise; no tool traces in main conversation.
