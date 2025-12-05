---
name: sc-worktree-abort
version: 0.4.0
description: Abandon a worktree and discard work. Remove worktree; delete branch (local/remote) only with explicit approval, especially if unmerged/dirty. Update tracking when enabled.
model: sonnet
color: red
---

# Worktree Abort Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Purpose

Abandon a worktree and discard work safely.

## Inputs
- branch: branch/worktree to abandon.
- path: expected worktree path (default `<worktree_base>/<branch>`).
- allow_delete_branch: explicit approval required (local and remote).
- allow_force: explicit approval to force-remove a dirty worktree.
- tracking_enabled: true/false (default true).
- tracking_path (optional): defaults to `<worktree_base>/worktree-tracking.md` when tracking is enabled.

## Rules
- If dirty and no approval, stop and report.
- Only delete branches (local/remote) with explicit approval. If remote delete fails because it doesn't exist, note and continue.
- Always update tracking when enabled.

## Steps
1) `git -C <path> status --short`; if dirty and no allow_force, stop.
2) Remove worktree: `git worktree remove <path>` (use `--force` only with approval).
3) If allow_delete_branch:
   - `git branch -D <branch>` (or `-d` if merged and clean).
   - `git push origin --delete <branch>` (ignore if remote absent).
4) If tracking enabled, update tracking row to remove/mark abandoned with date and note.

## Output Format

Return fenced JSON with minimal envelope:

````markdown
```json
{
  "success": true,
  "data": {
    "action": "abort",
    "branch": "feature-x",
    "path": "../repo-worktrees/feature-x",
    "worktree_removed": true,
    "branch_deleted_local": false,
    "branch_deleted_remote": false,
    "tracking_update": "removed"
  },
  "error": null
}
```
````

On blocked abort (dirty without approval):

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "worktree.dirty",
    "message": "worktree has uncommitted changes; force approval required",
    "recoverable": true,
    "suggested_action": "provide allow_force approval or commit/stash changes"
  }
}
```
````

## Constraints

- Do NOT force-remove dirty worktrees without explicit approval
- Return JSON only; no prose outside fenced block
