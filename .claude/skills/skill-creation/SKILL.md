---
name: skill-creation
version: 0.8.0
description: Plan and create Claude Code skills/commands/agents with guided wizards and background agents aligned to v0.5 guidelines.
  Use when user says "create a skill", "plan a new agent", "skill wizard", or "command generator".
---

# Skill Creation (planning + creation)

This skill runs two flows: planning (`/skill-plan`) and creation (`/skill-create`). Review is handled separately by the `skill-reviewing` skill. Keep the main conversation clean; heavy work runs in agents via Agent Runner with registry-based resolution.

## Planning Flow (wizard)
1) Confirm goal: new skill package vs update/version bump (capture desired version target if known).
2) Capture responsibilities + success criteria; list primary use cases.
3) Command UX: required args, options, `--help` text; defaults for `--name`, behavior of `--from` (seed from existing skill/plan), and `--template` (plan skeleton file). Enforce naming convention: file path `.claude/commands/<name>.md`, frontmatter `name: <name>` (no slash), user invocation `/name` (slash added by system), default version 0.1.0.
4) Agents: propose candidate agents, inputs/outputs, fenced JSON envelopes, and registry versions.
5) File layout: commands under `.claude/commands`, skills under `.claude/skills/<name>/SKILL.md`, agents under `.claude/agents`, references/templates under `.claude/references` (if needed) for easy testing before packaging. Default versions for commands/skills/agents: 0.1.0 unless explicitly overridden.
6) Keep agent set minimal by default; only add extra agents when scope justifies it. Prefer clear roles (e.g., intake, fix, PR) over many micro-agents.
7) Statusing: mark plan as Preliminary, then Proposed after user confirms; generate 40–80 line overview with full plan path when user approves (Approved). Planning **must not** create artifacts—only write/update a plan file. Creation happens only via `/skill-create`.

### Implementation notes
- Use Agent Runner; resolve agents by name+version from `.claude/agents/registry.yaml`.
- Store plans by default in `plans/<name>.md`; allow override when user supplies a path or `--template`. Do not overwrite request/input files—write to a new plan file/path when invoked with a request doc.
- If `--from` is set, load referenced artifact(s) and summarize key facts into the plan.
- Maintain concise outputs; omit tool traces.

### Agent Runner invocation (v0.5 contract)

```yaml
agent: "skill-planning-agent"
params:
  goal: "new|update"
  target_name: "<skill name>"
  plan_path: "<plans/path.md>"
  from_paths: ["<paths from --from if any>"]
  template_path: "<template if provided>"
version_constraint: "0.x"
timeout_s: 120
```

### Agent output (fenced JSON, minimal envelope)

```json
{
  "success": true,
  "data": {
    "summary": "Concise overview",
    "plan": { "path": "<dest>", "status": "Preliminary|Proposed|Approved" },
    "actions": ["next step", "next step"],
    "open_questions": ["q1", "q2"]
  },
  "error": null
}
```

If plan incomplete, include open questions and next actions; otherwise provide summary + full plan path.

## Creation Flow
1) Input: approved plan path.
2) Generate stubs for command/skill/agents/references at version 0.1.0 using naming convention:
   - File path: `.claude/commands/<name>.md`
   - Frontmatter name: `<name>` (no slash)
   - User invocation: `/name` (slash added by system)
3) Populate references listed in the plan (e.g., required reference files).
4) Update registry with new agents and skill dependency constraints (including manage-worktree when git ops are needed).

## Storage

| Purpose | Location |
|---------|----------|
| Plans | `plans/<name>.md` |
| Scratch | `.claude/.prompts/` (transient)

## Safety
- Creation of plan files is allowed; avoid destructive repo changes.
- Keep outputs concise; no tool traces in main conversation.
- Base branch/worktree defaults: honor `.claude/config.yaml` if present (`base_branch`, `worktree_root`); otherwise default to `main` and a repo-named worktree root. For git operations, instruct reuse of manage-worktree skill.
- Registry expectations: include manage-worktree dependency when git ops are needed; use constraints like `manage-worktree: "0.x"`. Ensure new agents/skills are added with version 0.1.0 by default.
