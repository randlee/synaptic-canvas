---
name: sc-worktree-abort
version: 0.7.0
description: Abandon a worktree and discard work with protected branch safeguards. Remove worktree; for non-protected branches, delete branch (local/remote) only with explicit approval; for protected branches, never delete branch. Update tracking when enabled.
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
- allow_delete_branch: explicit approval required (local and remote). **Ignored for protected branches**.
- allow_force: explicit approval to force-remove a dirty worktree.
- protected_branches: list of protected branch names (e.g., ["main", "develop", "master"]). Required.
- tracking_enabled: true/false (default true).
- tracking_path (optional): defaults to `<worktree_base>/worktree-tracking.md` when tracking is enabled.

## Rules
- **Protected branches:** Remote branch must never be deleted. Remove worktree; local branch may be removed only if explicitly approved for abort. Default is preserve.
- If dirty and no approval, stop and report.
- For **non-protected branches**: Only delete branches (local/remote) with explicit approval. If remote delete fails because it doesn't exist, note and continue.
- Always update tracking when enabled.

## Steps
1) **Validate protected_branches input**:
   - If protected_branches is missing or empty, return error: "protected_branches list required but not provided"
   - Suggest: Derive from git_flow config (main_branch + develop_branch if enabled) or provide explicit list
2) **Check if branch is protected**: if branch is in protected_branches list, set is_protected = true.
3) `git -C <path> status --short`; if dirty and no allow_force, stop.
4) Remove worktree: `git worktree remove <path>` (use `--force` only with approval).
5) **If branch is protected**:
   - Remote deletion: NEVER delete remote protected branches.
   - Local deletion: only if explicitly approved (allow_delete_branch) and caller confirms; otherwise preserve local branch.
   - If tracking enabled, update tracking to note whether local branch was preserved or removed (protected).
6) **If branch is non-protected and allow_delete_branch is true**:
   - `git branch -D <branch>` (or `-d` if merged and clean).
   - `git push origin --delete <branch>` (ignore if remote absent).
7) If tracking enabled, update tracking row to remove/mark abandoned with date and note.

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
    "is_protected": false,
    "worktree_removed": true,
    "branch_deleted_local": false,
    "branch_deleted_remote": false,
    "tracking_update": "removed"
  },
  "error": null
}
```
````

Protected branch abort (worktree only):

````markdown
```json
{
  "success": true,
  "data": {
    "action": "abort",
    "branch": "main",
    "path": "../repo-worktrees/main",
    "is_protected": true,
    "worktree_removed": true,
    "branch_deleted_local": false,
    "branch_deleted_remote": false,
    "tracking_update": "worktree removed, branch preserved (protected)"
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
