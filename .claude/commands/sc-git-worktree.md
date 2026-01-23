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

Use this command to manage worktrees following the repo's layout and tracking rules.
- Repo root: current directory.
- Default worktree path: `../synaptic-canvas-worktrees/<branch>` (override in skill/agent config if needed).
- Default tracking doc: `../synaptic-canvas-worktrees/worktree-tracking.md` (toggle off or override if the repo doesn't track worktrees).
- Branch strategy: configure per repo (e.g., master for release, develop/integration, feature off integration, hotfix off master).
- Safety: never alter dirty worktrees without explicit approval; respect branch protections/hooks (no direct commits to protected branches).

## Protected Branches Configuration

Protected branches (main, develop, master) require special handling to prevent accidental deletion. Configure using:

```yaml
git_flow:
  enabled: true  # boolean: whether git-flow workflow is used
  main_branch: "main"  # or "master" - the primary production branch
  develop_branch: "develop"  # only if git_flow.enabled = true

protected_branches:
  - "main"
  - "develop"
  - "master"
```

**Protected Branch Rules:**
- Cleanup/abort operations NEVER delete protected branches (local or remote)
- Protected branches can only be removed from worktrees, never deleted
- Use `--update` to safely pull changes for protected branches in worktrees
- If git_flow.enabled is false, only main_branch is protected (default: "main")
- If git_flow.enabled is true, both main_branch and develop_branch are protected
- **Required**: All operations involving branch deletion must provide protected_branches list; operations fail if missing

If run with no options or `--help`: print a concise list of options (no git status) and prompt with a numbered choice for list/status, create, cleanup, or abort; then gather required inputs.

## Behavior

### Common steps
- Ensure scaffolding: `<worktree_base>` exists; create if missing. Ensure tracking doc exists with headers if tracking is enabled.
- `git fetch --all --prune` before create/cleanup decisions.
- Keep tracking doc in sync on every operation when enabled.

### --list / --status
- `git worktree list --porcelain`.
- Cross-check tracking doc; report missing/stale entries and dirty states via `git -C <path> status --short`.
- Agent option: call `sc-worktree-scan` and render its JSON as a table and bullet recommendations.

### --create
- Inputs: branch, base.
- Path: `../synaptic-canvas-worktrees/<branch>` by default.
- If branch exists: `git worktree add <path> <branch>`; else `git worktree add -b <branch> <path> <base>`.
- Verify hooks/branch protections apply; confirm `git status` clean.
- Update tracking row (branch, path, base, purpose, owner, created, status, last checked, notes) when tracking is enabled.
- Agent option: call `sc-worktree-create`; render as a table plus warnings/errors.

### --update
- **Protected branches only** - verify branch is in protected_branches list before proceeding.
- Inputs: branch name (required). Must be a protected branch (main, develop, master, etc.).
- Derive protected_branches list from git_flow config (main_branch + develop_branch if enabled) or fail with clear error if config missing.
- Check if worktree exists for the branch; error if missing.
- Check `git -C <path> status`; if dirty, stop and report uncommitted changes.
- Fetch and pull: `git fetch origin <branch>` then `git pull origin <branch>`.
- **If merge conflicts occur:**
  - Report conflicted files to user
  - Return control to main session for user to resolve conflicts
  - User navigates to worktree, resolves conflicts, and commits
  - After resolution, user can re-run --update to verify
- **If clean pull succeeds:**
  - Report commits pulled count
  - Update tracking with last_checked timestamp when tracking is enabled
- Agent option: call `sc-worktree-update`; render success or handle conflicts interactively.

### --cleanup
- **Check if branch is protected first** - derive protected_branches list from git_flow config or fail if missing.
- If branch is in protected_branches list, ONLY remove worktree, NEVER delete the branch.
- Check `git -C <path> status`; if dirty, stop and request explicit approval/coordination.
- Confirm branch merged/approved for removal.
- `git worktree remove <path>` (force only with approval).
- For **non-protected branches**: If merged and has no unique commits, delete the branch locally (`git branch -d <branch>`) and remotely (`git push origin --delete <branch>`) by default. Only retain the branch if the user explicitly opts out. If the remote branch is already gone, continue without error. If not merged, only delete branches (local/remote) with explicit approval.
- For **protected branches**: Only remove worktree, preserve branch locally and remotely. Update tracking to note "worktree removed, branch preserved (protected)".
- Update tracking (remove or mark cleaned with merge SHA/date) when tracking is enabled.
- Agent option: call `sc-worktree-cleanup` with protected_branches list; render its JSON as a short summary list.

### --abort
- **Check if branch is protected first** - derive protected_branches list from git_flow config or fail if missing.
- If branch is in protected_branches list, ONLY remove worktree, NEVER delete the branch.
- Check `git -C <path> status`; if dirty, stop and request explicit approval/coordination.
- `git worktree remove <path>` (force only with approval).
- For **non-protected branches**: If requested, delete branch locally (`git branch -D <branch>`) and remotely (`git push origin --delete <branch>`).
- For **protected branches**: Only remove worktree, preserve branch locally and remotely. Require confirmation: "Branch is protected. Remove worktree but preserve branch?"
- Update tracking to remove the entry and note abandonment when tracking is enabled.
- Agent option: call `sc-worktree-abort` with protected_branches list; render its JSON as a short summary list.

### --help
- Show options and remind about base branches, paths, tracking toggles, and dirty-worktree safeguards. Keep output concise (no tool traces).
