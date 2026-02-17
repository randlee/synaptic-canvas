---
name: sc-managing-worktrees
description:
  Create, manage, scan, update, and clean up git worktrees for parallel development with protected branch safeguards.
  Use when working on multiple branches simultaneously, isolating experiments, updating protected branches (main/develop),
  or when user mentions "worktree", "parallel branches", "feature isolation", "branch cleanup", "worktree status", or "update main/develop".
version: 0.9.0
entry_point: /sc-git-worktree
---

# Managing Git Worktrees

Use this skill to manage worktrees with a standard structure and tracking. Use the `/sc-git-worktree` command to invoke this skill.

## Agent Delegation (Required)

This skill delegates all execution to specialized agents via the **Task tool** (no manual git commands in the primary session).
Always pass inputs via `<input_json>` and render `<output_json>` from the subagent response.

**Task tool template:**

```xml
<invoke name="Task">
<parameter name="subagent_type">$SUBAGENT</parameter>
<parameter name="description">$DESCRIPTION</parameter>
<parameter name="prompt">Run $SUBAGENT with this input:

<input_json>
```json
$INPUT_JSON
```
</input_json>
</parameter>
</invoke>
```

| Operation | Agent | Returns |
|-----------|-------|---------|
| Create | `sc-worktree-create` | JSON: success, path, branch, tracking_entry |
| Scan | `sc-worktree-scan` | JSON: success, worktrees list, recommendations |
| Cleanup | `sc-worktree-cleanup` | JSON: success, branch_deleted, tracking_update |
| Abort | `sc-worktree-abort` | JSON: success, worktree_removed, tracking_update |
| Update | `sc-worktree-update` | JSON: success, commits_pulled, conflicts (if any) |

To invoke an agent, use the Task tool with the agent prompt and pass parameters exactly as documented in the agent Inputs section.

## Standards and Paths
- Repo root: current directory.
- Default worktree base: `../{{REPO_NAME}}-worktrees`.
- Worktrees live in `<worktree_base>/<branch>`.
- Tracking file (if used): `<worktree_base>/worktree-tracking.jsonl` must be updated on create/scan/cleanup/abandon. Allow a toggle to disable tracking for repos that don't use it.
- Naming: worktree directory = branch name; branch naming follows repo policy.
- Branch protections/hooks: no direct commits to protected branches.

## Protected Branch Configuration

Protected branches (main, develop, master, etc.) require special handling to prevent accidental deletion:

```yaml
# .sc/shared-settings.yaml
git:
  protected_branches:
    - "main"
    - "develop"
    - "master"
```

**Protected Branch Rules:**
- Protected branches are read from `.sc/shared-settings.yaml` (`git.protected_branches`)
- If missing, protected branches are auto-detected from git-flow and cached to `.sc/shared-settings.yaml`
- **Cleanup/abort agents NEVER delete protected branches** (local or remote)
- Protected branches can only be removed from worktrees, never deleted
- Use `--update` to safely pull changes for protected branches in worktrees

## Safety and reminders
- **NEVER delete protected branches** (main, develop, master) under any circumstances.
- Protected branches can only be removed from worktrees; the branch itself must always be preserved.
- Never delete branches or force-remove worktrees without explicit approval.
- Never clean/abandon a worktree with uncommitted changes unless explicitly approved.
- Keep tracking JSONL in sync on every operation when enabled.
- Respect branch protections and hooks; no direct commits to protected branches.
- Use background agents for worktree operations; keep the main context focused on decisions and summaries.
