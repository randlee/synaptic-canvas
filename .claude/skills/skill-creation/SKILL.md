---
name: skill-creation
version: 0.1.0
description: Plan, create, and review Claude Code skills/commands/agents with guided wizards and background agents aligned to v0.4 guidelines.
---

# Skill Creation (planning + creation + review)

This skill runs three flows: planning (`/skill-plan`), creation (`/skill-create`), and review (`/skill-review`). Keep the main conversation clean; heavy work runs in agents via Agent Runner with registry-based resolution.

## Planning Flow (wizard)
1) Confirm goal: new skill package vs update/version bump (capture desired version target if known).
2) Capture responsibilities + success criteria; list primary use cases.
3) Command UX: required args, options, `--help` text; defaults for `--name`, behavior of `--from` (seed from existing skill/plan), and `--template` (plan skeleton file). Enforce naming convention: file path `.claude/commands/<name>.md`, frontmatter `name: <name>` (no slash), user invocation `/name` (slash added by system), default version 0.1.0.
4) Agents: propose candidate agents, inputs/outputs, fenced JSON envelopes, and registry versions.
5) File layout: commands under `.claude/commands`, skills under `.claude/skills/<name>/SKILL.md`, agents under `.claude/agents`, references/templates under `.claude/references` (if needed) for easy testing before packaging. Default versions for commands/skills/agents: 0.1.0 unless explicitly overridden.
6) Keep agent set minimal by default; only add extra agents when scope justifies it. Prefer clear roles (e.g., intake, fix, PR) over many micro-agents.
6) Statusing: mark plan as Preliminary, then Proposed after user confirms; generate 40–80 line overview with full plan path when user approves (Approved). Planning **must not** create artifacts—only write/update a plan file. Creation happens only via `/skill-create`.

### Implementation notes
- Use Agent Runner; resolve agents by name+version from `.claude/agents/registry.yaml`.
- Store plans by default in `plans/<name>.md`; allow override when user supplies a path or `--template`. Do not overwrite request/input files—write to a new plan file/path when invoked with a request doc.
- If `--from` is set, load referenced artifact(s) and summarize key facts into the plan.
- Maintain concise outputs; omit tool traces.

### Agent Runner prompt snippets (planning)
- Planning call template:
```
Invoke Agent Runner with:
  agent: "skill-planning-agent"
  registry: .claude/agents/registry.yaml
  params:
    goal: "new|update"
    target_name: "<skill name>"
    plan_path: "<plans/path.md>"
    from_paths: [<paths from --from if any>]
    template_path: "<template if provided>"
```
- Ensure response is fenced JSON with the minimal envelope; include `summary`, `actions`, `open_questions`, `plan.path`, `plan.status`.

### Agent delegation (planning)
- Invoke `skill-planning-agent` with collected inputs. Require fenced JSON output with minimal envelope:
```
```json
{ "success": true, "data": { "summary": "...", "actions": [] }, "error": null }
```
```
- If plan incomplete, include open questions and next actions in the overview; otherwise provide summary + full plan path.

## Creation Flow
1) Input: approved plan path.
2) Generate stubs for command/skill/agents/references at version 0.1.0 using naming convention:
   - File path: `.claude/commands/<name>.md`
   - Frontmatter name: `<name>` (no slash)
   - User invocation: `/name` (slash added by system)
3) Populate references listed in the plan (e.g., required reference files).
4) Update registry with new agents and skill dependency constraints (including manage-worktree when git ops are needed).
5) Prepare report/temp directories if absent: `.claude/reports/skill-reviews/`, `.claude/.tmp/skill-reviews/`, `.claude/.prompts/`.

## Review Flow
1) Identify target (name/path) and scope (command|skill|agent|all; default all).
2) Ask user where to write the report (default `.claude/reports/skill-reviews/<target>-report.md`; if unavailable, offer `.claude/.tmp/skill-reviews/`).
3) Ensure the chosen report directory exists (create it if missing) before writing.
4) Invoke `skill-review-agent` to evaluate against `docs/claude-code-skills-agents-guidelines-0.4.md` and registry/version rules.
5) Present concise findings; if `--fix`, include suggested edits/snippets but do not write files.

### Agent delegation (review)
- Agent Runner call template:
```
Invoke Agent Runner with:
  agent: "skill-review-agent"
  registry: .claude/agents/registry.yaml
  params:
    target: "<name or path>"
    scope: "command|skill|agent|all"
    report_path: "<.claude/reports/skill-reviews/... or .claude/.tmp fallback>"
    fix: true|false
```
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
- Base branch/worktree defaults: honor `.claude/config.yaml` if present (`base_branch`, `worktree_root`); otherwise default to `main` and a repo-named worktree root. For git operations, instruct reuse of manage-worktree skill.
- Registry expectations: include manage-worktree dependency when git ops are needed; use constraints like `manage-worktree: "0.x"`. Ensure new agents/skills are added with version 0.1.0 by default.
