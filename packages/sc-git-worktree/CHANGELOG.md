# Changelog

All notable changes to the **sc-git-worktree** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shared protected-branches settings via `.sc/shared-settings.yaml` (`git.protected_branches`), with git-flow auto-detection and caching.
- `--no-cache` flag for scan to avoid writing shared settings in dry-run contexts.
- Clean-all now reconciles JSONL before cleanup and captures untracked local worktrees as `discovered`.

### Changed
- Merge detection now uses a protected merge base (not `HEAD`) and fails closed if no protected branch is configured.
- Tracking entries are preserved until both local worktree and remote branch are gone.

### Breaking
- Cleanup/scan/update/abort now fail if protected branches are not configured and git-flow detection is unavailable.

### Planned
- Interactive branch selection and auto-completion
- Graphical worktree status dashboard
- Automatic worktree pruning with age-based cleanup
- Integration with GitHub/GitLab branch protection rules
- Support for worktree templates and shared configurations

## [0.7.0] - 2025-12-21

### Changed
- Version synchronized with marketplace v0.7.0 release
- Part of coordinated marketplace release

### Notes
- No functional changes from v0.6.0
- Synchronized versioning for consistency across all packages

## [0.4.0] - 2025-12-02

### Status
Beta release - initial v0.x publication. Local-only scope (repo-level installation only).

### Added
- **sc-worktree-create** agent: Create new git worktrees with safe defaults
  - Standard sibling-folder layout: `../{{REPO_NAME}}-worktrees/<branch>`
  - Automatic base branch resolution
  - Validation before creation
  - Tracking document integration (optional)
- **sc-worktree-scan** agent: List and inspect all worktrees in the repo
  - Detailed status for each worktree (clean/dirty, branch, head commit)
  - Hierarchical worktree structure display
  - Optional tracking document reference
- **sc-worktree-cleanup** agent: Safe removal of worktrees
  - Checks for uncommitted changes before cleanup
  - Respects branch protection rules
  - Graceful error handling for protected branches
  - Optional dry-run mode
- **sc-worktree-abort** agent: Force-abort worktrees with explicit approval
  - Requires confirmation for destructive operations
  - Discards uncommitted changes with user acknowledgment
  - Useful for orphaned or damaged worktrees
- `/sc-git-worktree` command: User-facing command for worktree management
  - `--list` or `--status`: Show worktree inventory
  - `--create <branch> <base>`: Create a new worktree
  - `--cleanup <branch>`: Remove a worktree safely
  - `--abort <branch>`: Force-remove a worktree
- **Worktree tracking document** (optional): Auto-generated markdown at `../{{REPO_NAME}}-worktrees/worktree-tracking.md`
  - Documents active worktrees and their purposes
  - Optional feature (disable with `no-tracking` option)

### Components
- Command: `commands/sc-git-worktree.md`
- Skill: `skills/sc-managing-worktrees/SKILL.md`
- Agents:
  - `agents/sc-worktree-create.md` (v0.4.0)
  - `agents/sc-worktree-scan.md` (v0.4.0)
  - `agents/sc-worktree-cleanup.md` (v0.4.0)
  - `agents/sc-worktree-abort.md` (v0.4.0)

### Dependencies
- **git** >= 2.20 (git worktree support and `git rev-parse` for repo detection)

### Scope
- **Local-only**: Can only be installed in a repository's `.claude` directory
- Not available for global installation

### Features
- **Token Substitution (Tier 1 Package)**: Uses `{{REPO_NAME}}` token auto-detected from git repository basename
  - Default worktree location: `../<repo-name>-worktrees/<branch>`
  - Tracking document location: `../<repo-name>-worktrees/worktree-tracking.md`
- **Safety First**:
  - Never modifies dirty worktrees without explicit approval
  - Respects git branch protections
  - Validates worktree paths before operations
  - Prevents accidental data loss

### Known Limitations
- Worktree sibling folder layout is fixed to `../<repo>-worktrees/` (not customizable in v0.4.0)
- No support for cross-filesystem worktrees
- Tracking document is read-only from agent perspective (manual edits required)
- Branch protection validation depends on git hooks (not API-based)
- No GUI support; command-line only

### Installation
```bash
# Local installation (inside a git repository)
python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude

# Optional: disable tracking document generation
python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude --no-tracking
```

### Uninstallation
```bash
python3 tools/sc-install.py uninstall sc-git-worktree --dest /path/to/your-repo/.claude
```

### Troubleshooting
- **"Path exists: ../my-repo-worktrees/feature-x"**: Worktree already exists or directory is not empty
  - Solution: Choose a different branch name or remove the existing worktree
- **"Dirty worktree" error**: Worktree has uncommitted changes
  - Solution: Commit or stash changes before cleanup/abort
- **"Token expansion failed: {{REPO_NAME}}"**: Repository is not a valid git repository
  - Solution: Ensure you're running from within a git repository root
- **Git version warning**: `git --version` shows < 2.20
  - Solution: Upgrade git to 2.20 or later

### Requirements
- **git** >= 2.20 (for worktree subcommand and robust status detection)
- Repository must be a valid git repository (worktree-local installation only)

### Usage Examples
```bash
# Check current worktree status
/sc-git-worktree --status

# Create a new worktree for feature development
/sc-git-worktree --create feature-auth main

# Inspect all worktrees and their status
/sc-git-worktree --list

# Clean up a completed feature worktree
/sc-git-worktree --cleanup feature-auth

# Force-abort an orphaned worktree
/sc-git-worktree --abort stale-branch
```

### Future Roadmap
- v0.5.0: Add customizable worktree path templates
- v0.6.0: Integrate with GitHub/GitLab branch protection APIs
- v1.0.0: Stable API with full backward compatibility
- Interactive branch selection and fuzzy search
- Automatic pruning with configurable retention policy
- Dashboard for visual worktree management
- Worktree templates for project-specific setups

### Contributing
When updating this changelog:
1. Add entries under **[Unreleased]** for new features, bug fixes, or breaking changes
2. Use standard changelog categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**
3. Link issue/PR numbers when available
4. Create a new section with version and date when releasing
5. Maintain chronological order with newest versions at the top
6. Note any token substitution changes if applicable

---

## Repository
- **Repository**: [synaptic-canvas](https://github.com/randlee/synaptic-canvas)
- **Issues**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- **Package Registry**: [docs/registries/nuget/registry.json](https://github.com/randlee/synaptic-canvas/blob/main/docs/registries/nuget/registry.json)
