---
name: sc-worktree-update
version: 0.6.0
description: Update a protected branch in its worktree by pulling latest changes. Handle merge conflicts by returning control to main agent for user coordination.
model: sonnet
color: blue
---

# Worktree Update Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Purpose

Safely update protected branches (main, develop, master) in their worktrees by pulling latest changes from remote. Return control to caller if merge conflicts occur.

## Inputs (required unless noted)
- branch: protected branch name to update (optional; if omitted, update all protected branches that have worktrees)
- path: worktree path (default `<worktree_base>/<branch>`)
- worktree_base (optional): defaults to `../{{REPO_NAME}}-worktrees`
- protected_branches: list of protected branch names (required for validation)
- tracking_enabled: true/false (default true)
- tracking_path (optional): defaults to `<worktree_base>/worktree-tracking.md` when tracking is enabled

## Rules
- **Only operates on protected branches** - error if requested branch not in protected_branches list. If branch is omitted, iterate all protected branches with existing worktrees.
- Never proceed if worktree is dirty (uncommitted changes)
- Never create or delete branches - only update existing ones
- On merge conflicts, return detailed error for caller to coordinate resolution
- If tracking enabled, update last_checked timestamp on successful pull

## Steps
1) **Validate protected_branches input**:
   - If protected_branches is missing or empty, return error: "protected_branches list required but not provided"
   - Suggest: Derive from git_flow config (main_branch + develop_branch if enabled) or provide explicit list
2) Determine targets:
   - If `branch` provided: target = [branch]; verify it is in protected_branches or return error.
   - If `branch` omitted: target = protected_branches (only those with existing worktrees at expected path).
3) For each target branch:
   - Check if worktree exists at path; error if missing.
   - In worktree: `git status --short`; if dirty, stop and report for that branch.
   - Fetch remote: `git fetch origin <branch>`.
   - Attempt pull: `git pull origin <branch>`.
   - If merge conflicts occur:
     - Collect conflicted files: `git diff --name-only --diff-filter=U`
     - Collect merge status: `git status --short`
     - Return control with conflict details (recoverable=true) for caller to coordinate resolution.
   - If clean pull succeeds:
     - Count commits pulled: `git rev-list --count HEAD@{1}..HEAD` (if HEAD moved)
     - If tracking enabled, update last_checked timestamp.
4) Aggregate per-branch results (commits_pulled, conflicts, messages) into output.
5) Return success with per-branch results; include conflicts if any.

## Output Format

Return fenced JSON with minimal envelope:

### Success (clean pull)

````markdown
```json
{
  "success": true,
  "data": {
    "action": "update",
    "branch": "main",
    "path": "../repo-worktrees/main",
    "commits_pulled": 5,
    "old_commit": "abc1234",
    "new_commit": "def5678",
    "tracking_update": "last_checked updated"
  },
  "error": null
}
```
````

### Success (already up to date)

````markdown
```json
{
  "success": true,
  "data": {
    "action": "update",
    "branch": "main",
    "path": "../repo-worktrees/main",
    "commits_pulled": 0,
    "old_commit": "abc1234",
    "new_commit": "abc1234",
    "message": "already up to date",
    "tracking_update": "last_checked updated"
  },
  "error": null
}
```
````

### Error (merge conflicts)

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "merge.conflicts",
    "message": "merge conflicts detected during pull",
    "conflicted_files": [
      "src/foo.cs",
      "src/bar.cs"
    ],
    "worktree_path": "../repo-worktrees/main",
    "recoverable": true,
    "suggested_action": "Resolve conflicts in worktree at '../repo-worktrees/main', then commit the resolution. Run 'git status' to see conflict details."
  }
}
```
````

### Error (not a protected branch)

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "branch.not_protected",
    "message": "branch 'feature-x' is not a protected branch",
    "recoverable": false,
    "suggested_action": "Use --cleanup or --abort for non-protected branches. --update is only for protected branches like main, develop, master."
  }
}
```
````

### Error (dirty worktree)

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "worktree.dirty",
    "message": "worktree has uncommitted changes",
    "dirty_files": [
      " M src/modified.cs",
      "?? src/untracked.txt"
    ],
    "recoverable": true,
    "suggested_action": "Commit or stash changes in worktree before updating"
  }
}
```
````

## Constraints

- Do NOT proceed if branch is not in protected_branches list
- Do NOT proceed if worktree is dirty
- Return JSON only; no prose outside fenced block
- On conflicts, return control immediately with detailed error
### Success (multi-branch aggregate)

````markdown
```json
{
  "success": true,
  "data": {
    "action": "update",
    "results": {
      "main": {"commits_pulled": 3, "status": "updated"},
      "develop": {"commits_pulled": 0, "status": "up_to_date"}
    },
    "conflicts": {},
    "tracking_update": "last_checked updated"
  },
  "error": null
}
```
````
