---
name: sc-git-worktree
description: Manage git worktrees for this repo (create, list/status, update, cleanup, abort) while enforcing the repo's worktree/tracking rules and protected branch safeguards.
version: 0.8.0
options:
  - name: --list
    description: List worktrees and show status/notes.
  - name: --status
    description: Alias for --list (show worktree status and tracking sync).
  - name: --create
    args:
      - name: branch
        description: Branch name to create/use for the worktree.
      - name: base
        description: Base branch to start from (e.g., master, develop, release/x.y, hotfix/...).
    description: Create a worktree (and branch if needed) using the mandated layout and update tracking.
  - name: --update
    args:
      - name: branch
        description: Protected branch name to update (e.g., main, develop).
    description: Pull latest changes for protected branches in their worktrees. If a branch is specified, update only that branch; if omitted, update all protected branches. Handle merge conflicts interactively by notifying user and coordinating resolution.
  - name: --cleanup
    args:
      - name: branch
        description: Branch/worktree name to clean up (post-merge or finished work).
    description: Remove a worktree; for non-protected branches, delete local and remote branch by default if merged/no unique commits (only keep if user opts out); for protected branches, only remove worktree and preserve branch; update tracking.
  - name: --abort
    args:
      - name: branch
        description: Branch/worktree name to abandon (discard work).
    description: Abandon a worktree (delete worktree, optionally delete branch for non-protected branches) with explicit approval if dirty. Protected branches are never deleted.
  - name: --help
    description: Show available options and guidance.
---

# /sc-git-worktree command

Use this command to manage worktrees following the repo's layout and tracking rules. You MUST invoke the appropriate subagent via the Task tool; do not run manual git commands in the primary session.

Defaults:
- Repo root: current directory.
- Worktree base: `../{{REPO_NAME}}-worktrees/<branch>`.
- Tracking file: `../{{REPO_NAME}}-worktrees/worktree-tracking.jsonl` (disable or override if tracking is not used).

## Protected Branches Configuration

Protected branches (main, develop, master) require special handling to prevent accidental deletion. Configure using:

```yaml
git:
  protected_branches:
    - "main"
    - "develop"
    - "master"
```

**Protected Branch Rules:**
- Cleanup/abort operations NEVER delete protected branches (local or remote)
- Protected branches can only be removed from worktrees, never deleted
- Use `--update` to safely pull changes for protected branches in worktrees
- Protected branches are read from `.sc/shared-settings.yaml` (`git.protected_branches`)
- If not configured, protected branches are auto-detected from git-flow and cached to `.sc/shared-settings.yaml`
- **Required**: Operations fail if protected branches cannot be determined

If run with no options or `--help`: print a concise list of options (no git status) and prompt with a numbered choice for list/status, create, cleanup, or abort; then gather required inputs.

## Behavior

## Task Tool Invocation (Required)

Use the Task tool with `<input_json>` and consume `<output_json>` from the subagent response. No manual git commands in the primary session.

### Template

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

### --list / --status
MUST invoke `sc-worktree-scan` and render its `<output_json>` summary and recommendations.

### --create
MUST invoke `sc-worktree-create` with `branch`, `base`, `purpose`, `owner`, and optional tracking inputs. Render the `<output_json>` summary.

### --update
MUST invoke `sc-worktree-update` for protected branches only. Render conflicts or success from `<output_json>`.

### --cleanup
MUST invoke `sc-worktree-cleanup`. Batch cleanup reconciles JSONL first, captures untracked local worktrees, then cleans tracked worktrees only. Render the `<output_json>` summary.

### --abort
MUST invoke `sc-worktree-abort` and render the `<output_json>` summary.

### --help
Show options and remind about base branches, paths, tracking toggles, and dirty-worktree safeguards. Keep output concise (no tool traces).
