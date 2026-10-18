# sc-manage

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.14.1](https://img.shields.io/badge/version-0.14.1-blue)](CHANGELOG.md)

Scope: User (recommended) or Project
Requires: python3, git

Manage Synaptic Canvas packages: list installed packages and install or uninstall packages in project, user, or global scopes.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary
- List packages with install status (no/local/global/both)
- Install packages for Claude, Codex, Cursor, or Hermes at project or user/global scope
- Uninstall packages from selected scope
- Enforces package policy (e.g., sc-git-worktree is local-only)

## Quick Start (Global install)

For native Codex plugins (no Claude or Python bootstrap), use:

```bash
codex plugin marketplace add randlee/synaptic-canvas --ref develop
codex plugin add sc-manage@synaptic-canvas
codex plugin add sc-gh-stack@synaptic-canvas
```

Select `sc-manage:managing-sc-packages` in Codex's skill picker. This route uses `codex plugin` for
installation status, installation and removal, not the artifact dispatcher.
See [native Codex marketplace guidance](../../docs/CODEX-MARKETPLACE.md) for
review refs, updates and the distinction from the copying route below.

`sc-manage` is the package/plugin name and the installer other packages need:
many skills ship scripts (and some `install.py` hooks) rather than a standalone
`SKILL.md`. Its skill is **`managing-sc-packages`**. `/sc-manage` is the Claude
slash command and, after a Cursor install, the Cursor command at
`.cursor/commands/sc-manage.md` (or `~/.cursor/commands/sc-manage.md`). Finding
the package in a repository or cache is not proof that a host has loaded it.

From a Synaptic Canvas checkout, install its artifacts for selected hosts:

```bash
python3 tools/sc-install.py install sc-manage --global --claude --codex --cursor --hermes
```

Use only the target flags you need. This copies artifacts; it does not register
a Claude marketplace plugin in `installed_plugins.json` or edit enabled plugins.
The installed helpers remember the source checkout in nonsecret metadata, so
`SC_REPO_PATH` is optional unless that checkout moves. Claude marketplace plugin
installs can discover their source through the local marketplace record.

## Usage
- `/sc-manage --list`
- `/sc-manage --install <package> --local|--project|--global|--user`
- `/sc-manage --uninstall <package> --local|--project|--global|--user`
- `/sc-manage --docs <package>` (preview README and related docs; ask questions)

Choose any combination of `--claude`, `--codex`, `--cursor`, `--hermes` for
install, uninstall, or list. No target flags means **Claude only**, preserving
existing manager behavior. Unknown flags and conflicting scopes are errors.

```text
/sc-manage --install sc-gh-stack --global --codex
/sc-manage --install sc-gh-stack --local --cursor --hermes
/sc-manage --list --claude --codex --cursor --hermes
/sc-manage --uninstall sc-gh-stack --global --codex
```

| Target | Project root | Default user/global root |
|---|---|---|
| Claude | `.claude` | `~/.claude` |
| Codex | `.codex` | `$CODEX_HOME` or `~/.codex` |
| Cursor | `.cursor` | `~/.cursor` |
| Hermes | `.hermes` | `$HERMES_HOME` or `~/.hermes` |

`GLOBAL_<TARGET>_DIR` / `USER_<TARGET>_DIR` override user/global roots.
Project installs stay under the repository root regardless of profile settings.
The agent JSON interface also accepts `global_<target>_dir` and `user_<target>_dir`.

Non-Claude targets receive skills, scripts, and assets. Claude Task agents,
plugin manifests and `agents/registry.yaml` are not installed there. Cursor
also has native [commands](https://cursor.com/docs/reference/plugins) and
[subagents](https://cursor.com/docs/subagents); Claude's command bang-syntax
and Task-agent files are not drop-in, so other packages are invoked as skills
(`/skill-name`). sc-manage additionally writes a Cursor-native `/sc-manage`
command because its skill folder is `managing-sc-packages`.
[Cursor loads `.cursor/skills/` and `~/.cursor/skills/`](https://cursor.com/docs/skills),
and for compatibility also `.claude/skills/` and `.codex/skills/`. Dual Claude
and Cursor project installs can therefore list the same skill twice.
User-level Cursor skills reach Cloud Agents only with Sync Skills; `~/.cursor/scripts/`
does not sync, so prefer `--local --cursor` when Cloud Agents must run the installer.
[Hermes project skills require explicit trust](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills):
run `hermes skills trust` from the repository after reviewing its skills.
The installer never grants trust or modifies Hermes configuration automatically.

On Cursor, Codex, and Hermes, run `sc_manage_dispatch.py` from the installed
target's `scripts/` directory (from the skill, `../../scripts/`; from the Cursor
command, `../scripts/`). Do not use Claude Task agents. If the remembered source
is unavailable, set `SC_REPO_PATH` to the checkout containing the source packages
and installer.

Install/uninstall JSON includes `targets` and `destinations`. The legacy `dest`
field is a string for a single target and null for multiple. Failure output
identifies `completed_targets` and `failed_target`; multi-target actions are not
transactional. List output includes authoritative `installed_by_target` states;
the summary `installed` becomes `mixed` when selected targets differ.

The underlying CLI also supports all four flags. `--dest PATH` accepts exactly
one explicit target, allowing profile roots, while bare `--dest` remains Claude.
Its existing no-target scoped default remains Claude+Codex; the manager always
passes an explicit target choice and therefore retains its Claude-only default.

## Components
- Command: `commands/sc-manage.md` (Claude); `cursor/sc-manage.md` is written to `.cursor/commands/sc-manage.md` on Cursor installs
- Skill: `skills/managing-sc-packages/SKILL.md`
- Agents: `sc-packages-list`, `sc-package-install`, `sc-package-uninstall`, `sc-package-docs` (Claude Task only)
- Scripts: `scripts/sc_manage_*.py` (JSON in/out; the Cursor/Codex/Hermes execution path)

## Notes
- Project scope (`--local`/`--project`) requires being inside a Git repo (used to resolve `REPO_NAME` for token expansion).
- User scope (`--user`) defaults to `~/.claude` unless overridden by `USER_CLAUDE_DIR`.
- Global scope (`--global`) defaults to `~/.claude` unless overridden by `GLOBAL_CLAUDE_DIR`.
- `SC_REPO_PATH` can override the Synaptic Canvas repo root used for package discovery.

## Version & Changelog
- 0.14.0 — Explicit Claude, Codex, Cursor and Hermes targets for install/list/uninstall
- 0.4.0 — Initial v0.x publication

## Support
- Repository: https://github.com/…/synaptic-canvas
- Issues: https://github.com/…/synaptic-canvas/issues
