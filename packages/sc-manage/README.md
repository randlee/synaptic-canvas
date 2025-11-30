# sc-manage

Scope: Global (recommended)  
Requires: python3, git

Manage Synaptic Canvas packages: list installed packages and install or uninstall packages in local or global scopes.

## Summary
- List packages with install status (no/local/global/both)
- Install packages into a repo's `.claude` (local) or the global `.claude`
- Uninstall packages from selected scope
- Enforces package policy (e.g., git-worktree is local-only)

## Quick Start (Global install)
```bash
python3 tools/sc-install.py install sc-manage --dest /Users/<you>/Documents/.claude
```

## Usage
- `/sc-manage --list`
- `/sc-manage --install <package> --local|--global`
- `/sc-manage --uninstall <package> --local|--global`
- `/sc-manage --docs <package>` (preview README and related docs; ask questions)

## Components
- Command: `commands/sc-manage.md`
- Skill: `skills/managing-sc-packages/SKILL.md`
- Agents: `sc-packages-list`, `sc-package-install`, `sc-package-uninstall`, `sc-package-docs`

## Notes
- Local scope requires being inside a Git repo (used to resolve `REPO_NAME` for token expansion)
- Global scope installs to `/Users/<you>/Documents/.claude`

## Version & Changelog
- 0.4.0 — Initial v0.x publication

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues