---
name: sc-git-worktree
description:
  Create, manage, scan, update, and clean up git worktrees for parallel development with protected branch safeguards.
  Use when working on multiple branches simultaneously, isolating experiments, updating protected branches (main/develop),
  cutting a gh-stack layer as a worktree (top or mid-stack insert), or when user mentions "worktree", "parallel branches",
  "feature isolation", "branch cleanup", "worktree status", "update main/develop", "stack layer worktree", or "stacked worktree".
version: 0.14.0
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
| Create stack layer | `sc-worktree-create-stacked` | JSON: success, path, branch, stack, stack_handoff |
| Scan | `sc-worktree-scan` | JSON: success, worktrees list, recommendations |
| Cleanup | `sc-worktree-cleanup` | JSON: success, branch_deleted, tracking_update |
| Abort | `sc-worktree-abort` | JSON: success, worktree_removed, tracking_update |
| Update | `sc-worktree-update` | JSON: success, commits_pulled, conflicts (if any) |

To invoke an agent, use the Task tool with the agent prompt and pass parameters exactly as documented in the agent Inputs section.

**Routing rule:** a worktree that is a gh-stack layer (the user says "stack", "layer", "on top of <branch>", "insert under", or the branch will be linked with `gh stack`) goes to `sc-worktree-create-stacked`. Everything else goes to `sc-worktree-create`.

## Stack Layers (gh-stack)

A stack layer is a worktree whose branch will be a PR in a `gh stack`. The plain create is wrong for it: it branches from the **local** base ref (possibly stale or another writer's unpushed state) and, from a remote ref, would leave the parent as upstream. `sc-worktree-create-stacked` cuts from `origin/<parent>` with `--no-track`, refuses bad cuts before touching anything (parent not pushed, already landed, insert target not stacked on the parent), records the parent SHA in tracking, and returns a `stack_handoff` block.

- `stack_handoff.writer` goes verbatim to the agent that will work in the worktree (WIP commit, first push with `-u`, at most one rebase at task start, no edits to lower layers, no gh stack write commands). `stack_handoff.stack_writer` goes to the stack writer only (PR with base = parent, `gh stack checkout` in the new worktree, link on top, or the insert sequence: merge-forward by every layer above, unstack, `gh pr edit --base`, full relink).
- Cleanup refuses to delete a branch that live layers sit on unless git shows a merge-commit landing in the trunk (`STACK.HAS_CHILDREN`; batch cleanup reports `stack_blocked`, and never sweeps a fresh layer with no commits). Abort always refuses. Both read the tracking file.
- Scan reports `stack_parent_advanced` (layer no longer contains the parent's head) and `stack_parent_landed` (PR should now target the trunk) on layer rows.

Details and the handoff contract: `references/stack-layers.md`. The stack model, recipes and the view tool live in the `sc-gh-stack` package (`/sc-gh-stack`, `/sc-gh-stack-view`); this skill only makes the worktree side of that model safe.

## Standards and Paths
- Repo root: current directory.
- Default worktree base: `../<repo-name>-worktrees` where `<repo-name>` is the basename of the repo root directory, derived at runtime via `basename $(git rev-parse --show-toplevel)` (e.g. repo `my-project` → `../my-project-worktrees`).
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
