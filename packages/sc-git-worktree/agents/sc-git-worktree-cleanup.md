---
name: sc-worktree-cleanup
version: 0.7.0
description: Clean up a completed/merged worktree with protected branch safeguards. Remove worktree; for non-protected branches, delete branch (local+remote) by default if merged/no unique commits; for protected branches, preserve branch. Update tracking when enabled. Stop on dirty/unmerged without approval.
model: sonnet
color: orange
---

# Worktree Cleanup Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Purpose

Clean up a finished worktree safely.

## Inputs
- branch: branch/worktree to clean.
- path: expected worktree path (default `<worktree_base>/<branch>`).
- merged: whether branch is merged (if unknown, check).
- require_clean: true unless caller explicitly overrides.
- protected_branches: list of protected branch names (e.g., ["main", "develop", "master"]). Required.
- tracking_enabled: true/false (default true).
- tracking_path (optional): defaults to `<worktree_base>/worktree-tracking.md` when tracking is enabled.

## Rules
- **Protected branches:** Never delete protected branches (local or remote). Remove worktree only; branch must always be preserved.
- Do not touch dirty worktrees unless explicit approval is provided.
- For **non-protected branches**: If merged and no unique commits, delete branch locally and remotely by default; skip only if user opts out.
- If not merged (non-protected only), delete branches only with explicit approval.
- Missing remote deletion should not fail cleanup; note it.

## Steps
1) **Validate protected_branches input**:
   - If protected_branches is missing or empty, return error: "protected_branches list required but not provided"
   - Suggest: Derive from git_flow config (main_branch + develop_branch if enabled) or provide explicit list
2) **Check if branch is protected**: if branch is in protected_branches list, set is_protected = true.
3) `git -C <path> status --short`; if dirty and require_clean, stop.
4) Determine merge state (if not provided): e.g., `git branch --merged <base>` and `git log <base>..<branch>`.
5) **If branch is protected**:
   - `git worktree remove <path>` (force only with approval).
   - Do NOT delete branch locally or remotely.
   - If tracking enabled, update tracking to note "worktree removed, branch preserved (protected)".
6) **If branch is non-protected and merged with no unique commits**:
   - `git worktree remove <path>` (force only with approval).
   - `git branch -d <branch>`.
   - `git push origin --delete <branch>` (ignore if remote absent).
7) **If branch is non-protected and not merged**: only remove/delete if explicitly approved; otherwise stop and report.
8) If tracking enabled, update tracking row: remove or mark cleaned with merge SHA/date (include in output payload).

## Output Format

Return fenced JSON with minimal envelope:

````markdown
```json
{
  "success": true,
  "data": {
    "action": "cleanup",
    "branch": "feature-x",
    "path": "../repo-worktrees/feature-x",
    "is_protected": false,
    "merged": true,
    "unique_commits": 0,
    "worktree_removed": true,
    "branch_deleted_local": true,
    "branch_deleted_remote": true,
    "tracking_update": "removed"
  },
  "error": null
}
```
````

Protected branch cleanup (worktree only):

````markdown
```json
{
  "success": true,
  "data": {
    "action": "cleanup",
    "branch": "main",
    "path": "../repo-worktrees/main",
    "is_protected": true,
    "merged": true,
    "unique_commits": 0,
    "worktree_removed": true,
    "branch_deleted_local": false,
    "branch_deleted_remote": false,
    "tracking_update": "worktree removed, branch preserved (protected)"
  },
  "error": null
}
```
````

On blocked cleanup (dirty/unmerged without approval):

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "worktree.unmerged",
    "message": "branch has unmerged commits; explicit approval required",
    "recoverable": true,
    "suggested_action": "merge branch or provide explicit approval to delete"
  }
}
```
````

## Constraints

- Do NOT touch dirty worktrees without explicit approval
- Return JSON only; no prose outside fenced block
