---
name: sc-worktree-abort
version: 0.8.0
description: Abandon a worktree and discard work with protected branch safeguards. Remove worktree; for non-protected branches, delete branch (local/remote) only with explicit approval; for protected branches, never delete branch. Update tracking when enabled.
model: haiku
color: red
---

# Worktree Abort Agent

## Invocation

This agent is invoked via the Claude Task tool by a skill or command. Do not invoke directly.

## Input Protocol

Read inputs from `<input_json>` (JSON object). If omitted, treat as `{}`.

## Purpose

Abandon a worktree and discard work safely.

## Inputs
- branch: branch/worktree to abandon.
- path: expected worktree path (default `<worktree_base>/<branch>`).
- allow_delete_branch: explicit approval required (local and remote). **Ignored for protected branches**.
- allow_force: explicit approval to force-remove a dirty worktree.
- protected_branches: list of protected branch names (e.g., ["main", "develop", "master"]). Required.
- tracking_enabled: true/false (default true).
- tracking_path (optional): defaults to `<worktree_base>/worktree-tracking.jsonl` when tracking is enabled.
- cache_protected_branches (optional): defaults to `true`. When `false`, do not write `.sc/shared-settings.yaml`.

## Rules
- **Protected branches:** Remote branch must never be deleted. Remove worktree; local branch may be removed only if explicitly approved for abort. Default is preserve.
- If dirty and no approval, stop and report.
- For **non-protected branches**: Only delete branches (local/remote) with explicit approval. If remote delete fails because it doesn't exist, note and continue.
- Always update tracking when enabled.

## Execution

Run the abort script once with the input JSON:

```bash
python3 .claude/scripts/worktree_abort.py '<input_json>'
```

The script handles protected branch safeguards, dirty checks, and tracking updates.

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

## Output Protocol

Wrap the script output in `<output_json>` tags with a fenced JSON block. Do not add prose outside the tags.

## Constraints

- Do NOT force-remove dirty worktrees without explicit approval
- Do NOT run manual git commands; use the script only
