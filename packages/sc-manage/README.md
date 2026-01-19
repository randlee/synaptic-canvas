# sc-manage

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](CHANGELOG.md)

Scope: User (recommended) or Project
Requires: python3, git

Manage Synaptic Canvas packages: list installed packages and install or uninstall packages in project, user, or global scopes.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary
- List packages with install status (no/local/global/both)
- Install packages into a repo's `.claude` (project) or a user/global `.claude`
- Uninstall packages from selected scope
- Enforces package policy (e.g., sc-git-worktree is local-only)

## Quick Start (Global install)
```bash
python3 tools/sc-install.py install sc-manage --dest ~/.claude
```

## Usage
- `/sc-manage --list`
- `/sc-manage --install <package> --local|--project|--global|--user`
- `/sc-manage --uninstall <package> --local|--project|--global|--user`
- `/sc-manage --docs <package>` (preview README and related docs; ask questions)

## Components
- Command: `commands/sc-manage.md`
- Skill: `skills/managing-sc-packages/SKILL.md`
- Agents: `sc-packages-list`, `sc-package-install`, `sc-package-uninstall`, `sc-package-docs`
- Scripts: `scripts/sc_manage_*.py` (JSON in/out; validated by a PreToolUse hook)

## Notes
- Project scope (`--local`/`--project`) requires being inside a Git repo (used to resolve `REPO_NAME` for token expansion).
- User scope (`--user`) defaults to `~/.claude` unless overridden by `USER_CLAUDE_DIR`.
- Global scope (`--global`) defaults to `~/.claude` unless overridden by `GLOBAL_CLAUDE_DIR`.
- `SC_REPO_PATH` can override the Synaptic Canvas repo root used for package discovery.

## Version & Changelog
- 0.4.0 — Initial v0.x publication

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues
