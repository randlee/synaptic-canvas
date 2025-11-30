# git-worktree

Scope: Local-only  
Requires: git ≥ 2.20

Manage git worktrees with a standard sibling-folder layout and optional tracking documents. Provides a user-facing command `/git-worktree` and a managing skill that delegates to focused agents.

## Summary
Create, scan, clean up, and abort worktrees using predictable paths and safe defaults. Designed for multi-branch workflows and parallel development.

## Quick Start (Local-only)
1) Install into a repo's `.claude` directory:
   ```bash
   python3 tools/sc-install.py install git-worktree --dest /path/to/your-repo/.claude
   ```
2) In your repo, run:
   ```
   /git-worktree --status
   ```
3) Create a worktree:
   ```
   /git-worktree --create feature-x main
   ```

## Usage
- `/git-worktree --list` or `--status`
- `/git-worktree --create <branch> <base>`
- `/git-worktree --cleanup <branch>`
- `/git-worktree --abort <branch>`

Defaults
- Worktree base: `../{{REPO_NAME}}-worktrees/<branch>`
- Tracking doc (optional): `../{{REPO_NAME}}-worktrees/worktree-tracking.md`

Safety
- Never modify dirty worktrees without explicit approval
- Respect branch protections/hooks (no direct commits to protected branches)

## Install / Uninstall
- Install (local-only):
  ```bash
  python3 tools/sc-install.py install git-worktree --dest /path/to/your-repo/.claude
  ```
- Uninstall:
  ```bash
  python3 tools/sc-install.py uninstall git-worktree --dest /path/to/your-repo/.claude
  ```

## Troubleshooting
- "Path exists": Ensure `../<repo>-worktrees/<branch>` is not present (or choose a different branch)
- "Dirty worktree": Commit or stash before cleanup/abort
- Token expansion: `{{REPO_NAME}}` is auto-detected from the repo toplevel (via git)

## Components
- Command: `commands/git-worktree.md`
- Skill: `skills/managing-worktrees/SKILL.md`
- Agents: `worktree-create`, `worktree-scan`, `worktree-cleanup`, `worktree-abort`

## Version & Changelog
- 0.4.0 — Initial v0.x publication

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues
