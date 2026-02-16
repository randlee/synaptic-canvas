# sc-git-worktree

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](CHANGELOG.md)

Scope: Local-only
Requires: git ≥ 2.20

Manage git worktrees with a standard sibling-folder layout and optional tracking documents. Provides a user-facing command `/sc-git-worktree` and a managing skill that delegates to focused agents.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary
Create, scan, clean up, and abort worktrees using predictable paths and safe defaults. Designed for multi-branch workflows and parallel development.

## Quick Start (Local-only)
1) Install into a repo's `.claude` directory:
   ```bash
   python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude
   ```
2) In your repo, run:
   ```
   /sc-git-worktree --status
   ```
3) Create a worktree:
   ```
   /sc-git-worktree --create feature-x main
   ```

## Usage
- `/sc-git-worktree --list` or `--status`
- `/sc-git-worktree --create <branch> <base>`
- `/sc-git-worktree --cleanup <branch>`
- `/sc-git-worktree --abort <branch>`

Defaults
- Worktree base: `../{{REPO_NAME}}-worktrees/<branch>`
- Tracking file: `../{{REPO_NAME}}-worktrees/worktree-tracking.jsonl`

Safety
- Never delete unmerged branches without explicit approval
- Never delete remote branches that are ahead of local (unpulled commits)
- Never delete protected branches (main, master, develop)
- Never modify dirty worktrees without explicit approval

Shared Settings
- Protected branches are read from `.sc/shared-settings.yaml` (`git.protected_branches`)
- If missing, protected branches are auto-detected from git-flow and cached to `.sc/shared-settings.yaml`
- Use `--no-cache` with scan to avoid writing shared settings in dry-run contexts

## Design
See [DESIGN.md](DESIGN.md) for detailed requirements including:
- JSONL tracking schema and lifecycle
- Safety guards (protected branches, remote-ahead check)
- Scan reconciliation logic

## Install / Uninstall
- Install (local-only):
  ```bash
  python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude
  ```
- Uninstall:
  ```bash
  python3 tools/sc-install.py uninstall sc-git-worktree --dest /path/to/your-repo/.claude
  ```

## Troubleshooting
- "Path exists": Ensure `../<repo>-worktrees/<branch>` is not present (or choose a different branch)
- "Dirty worktree": Commit or stash before cleanup/abort
- Token expansion: `{{REPO_NAME}}` is auto-detected from the repo toplevel (via git)

## Components
- Command: `commands/sc-git-worktree.md`
- Skill: `skills/sc-managing-worktrees/SKILL.md`
- Agents: `sc-worktree-create`, `sc-worktree-scan`, `sc-worktree-cleanup`, `sc-worktree-abort`

## Version & Changelog
- 0.4.0 — Initial v0.x publication

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues
