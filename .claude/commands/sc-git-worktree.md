---
name: /sc-git-worktree
description: Manage git worktrees for this repo (create, list/status, cleanup, abort) while enforcing the repo’s worktree/tracking rules.
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
  - name: --cleanup
    args:
      - name: branch
        description: Branch/worktree name to clean up (post-merge or finished work).
    description: Remove a worktree; if merged/no unique commits, delete local and remote branch by default (only keep if user opts out); update tracking.
  - name: --abort
    args:
      - name: branch
        description: Branch/worktree name to abandon (discard work).
    description: Abandon a worktree (delete worktree, optionally delete branch) with explicit approval if dirty.
  - name: --help
    description: Show available options and guidance.
---

# /sc-git-worktree command

Use this command to manage worktrees following the repo’s layout and tracking rules.
- Repo root: current directory.
- Default worktree path: `../synaptic-canvas-worktrees/<branch>` (override in skill/agent config if needed).
- Default tracking doc: `../synaptic-canvas-worktrees/worktree-tracking.md` (toggle off or override if the repo doesn’t track worktrees).
- Branch strategy: configure per repo (e.g., master for release, develop/integration, feature off integration, hotfix off master).
- Safety: never alter dirty worktrees without explicit approval; respect branch protections/hooks (no direct commits to protected branches).

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

### --cleanup
- Check `git -C <path> status`; if dirty, stop and request explicit approval/coordination.
- Confirm branch merged/approved for removal.
- `git worktree remove <path>` (force only with approval).
- If merged and has no unique commits, delete the branch locally (`git branch -d <branch>`) and remotely (`git push origin --delete <branch>`) by default. Only retain the branch if the user explicitly opts out. If the remote branch is already gone, continue without error.
- If not merged, only delete branches (local/remote) with explicit approval.
- Update tracking (remove or mark cleaned with merge SHA/date) when tracking is enabled.
- Agent option: call `sc-worktree-cleanup`; render its JSON as a short summary list.

### --abort
- Check `git -C <path> status`; if dirty, stop and request explicit approval/coordination.
- `git worktree remove <path>` (force only with approval).
- If requested, delete branch locally (`git branch -D <branch>`) and remotely (`git push origin --delete <branch>`).
- Update tracking to remove the entry and note abandonment when tracking is enabled.
- Agent option: call `sc-worktree-abort`; render its JSON as a short summary list.

### --help
- Show options and remind about base branches, paths, tracking toggles, and dirty-worktree safeguards. Keep output concise (no tool traces).
