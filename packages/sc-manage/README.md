# sc-manage

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](CHANGELOG.md)

Scope: Global (recommended)
Requires: python3, git

Manage Synaptic Canvas packages: list installed packages and install or uninstall packages in local or global scopes.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

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