---
name: managing-sc-packages
description: List, install, or uninstall Synaptic Canvas packages (sc-manage). Use when the user wants /sc-manage, /managing-sc-packages, or to install package skills and scripts for Claude, Codex, Cursor, or Hermes.
version: 0.14.0
---

# Managing Synaptic Canvas Packages

Use this skill to manage Synaptic Canvas packages on this machine or in the current repo.
Packages are more than a `SKILL.md` file: many skills need their scripts, and some
run `install.py` at install time. Always go through this installer rather than
copying skill files by hand.

## Execution

Resolve `../../scripts/sc_manage_dispatch.py` relative to this skill directory
and run it with the user's flags unchanged. Use the absolute path; do not assume
`.claude`. This is the installer on every host.

Do not delegate to Task/subagents named `sc-package-list`, `sc-package-install`,
`sc-package-uninstall`, or `sc-package-docs` unless those Claude agent files are
present in this install. Cursor, Codex, and Hermes installs do not include them.
Cursor's Task tool is unrelated; using it here will fail.

Installed helpers remember their source checkout. If it moved or cannot be found,
set `SC_REPO_PATH` to the Synaptic Canvas checkout that provides the source
packages and `tools/sc-install.py`.

On Cursor, `/sc-manage` is the command at `../../commands/sc-manage.md`
relative to this skill (project `.cursor/commands/` or user
`~/.cursor/commands/`). `/managing-sc-packages` invokes this skill. Both must
run the dispatcher.

| Operation | Dispatcher flags | Returns |
|-----------|------------------|---------|
| List      | `--list` | JSON: packages [{ name, description, installable_scopes, installed, installed_by_target }] |
| Install   | `--install <package> --local|--project|--global|--user` | JSON: success, scope, dest, targets, destinations |
| Uninstall | `--uninstall <package> --local|--project|--global|--user` | JSON: success, scope, dest, targets, destinations |
| Docs      | `--docs <package>` | JSON: readme_path, size_bytes |

Claude installs may instead delegate through the Task tool to `sc-packages-list`,
`sc-package-install`, `sc-package-uninstall`, or `sc-package-docs` when those
agent files exist. Those agents still run the same scripts.

## Inputs / Flags

- `--list` → run the dispatcher with `--list`.
- `--install <package>` → require `--local`/`--project` or `--global`/`--user`; if missing, ask the user. If the package is local-only, force `--local`.
- `--uninstall <package>` → same scope logic as install.
- `--docs <package>` (alias `--doc`) → run the dispatcher with `--docs`.
- `--claude`, `--codex`, `--cursor`, `--hermes` select targets for install,
  uninstall or list. Flags can be combined; omitted targets mean Claude only.
  Forward the selected names as `targets: ["codex", "hermes"]` to agents/scripts.
  Never silently drop an unsupported flag or substitute another target.

## Conventions

- Local scope: the current repository's `.<target>` directory.
- Project scope: alias for local.
- User scope: `~/.claude` unless `USER_CLAUDE_DIR` is set.
- Global scope: `~/.claude` unless `GLOBAL_CLAUDE_DIR` is set.
- Detect the repo toplevel via `git rev-parse --show-toplevel`.
- The dispatcher calls `<SC_REPO_PATH>/tools/sc-install.py` (default resolved from `SC_REPO_PATH` or the remembered checkout).
- Other targets use `~/.codex`, `~/.cursor`, or `~/.hermes`; Codex and Hermes
  honor `CODEX_HOME` and `HERMES_HOME` for user/global profiles, not project scope.
  Cursor has no `CURSOR_HOME`; user/global is `~/.cursor` unless
  `GLOBAL_CURSOR_DIR` / `USER_CURSOR_DIR` override it.
- Cursor loads project skills from `.cursor/skills/` and user skills from
  `~/.cursor/skills/`. It also reads `.claude/skills/` and `.codex/skills/` for
  compatibility, so installing the same package for Claude and Cursor in one
  repo can surface the skill twice. `--cursor` is still the native destination
  and is required when Claude is not installed.
- Cursor Cloud Agents see project `.cursor/` files from the repo. User-level
  `~/.cursor/skills/` reaches Cloud Agents only with Sync Skills; sibling
  `~/.cursor/scripts/` does not sync. Prefer `--local --cursor` when Cloud
  Agents must run this installer.
- Non-Claude installs copy skills, scripts and assets. Claude commands, Task
  agents, plugin manifests and agent registries are not copied. sc-manage is
  the exception on Cursor: it also writes a Cursor-native `/sc-manage` command.
  Installation does not translate arbitrary Claude-specific workflows.
- Install/uninstall return `targets` and `destinations`; `dest` remains a string
  for one target and is null for multiple. On failure, report completed targets;
  do not claim rollback. Listing exposes `installed_by_target`; `installed` is
  `mixed` when selected targets differ. Use the mapping for per-target decisions.
- Hermes project skills require `hermes skills trust` inside the repository.
  Tell the user about that step; never grant trust or edit Hermes config silently.

## Safety

- Respect package metadata: if a package manifest declares `install.scope: local-only`, block global installation.
- Return only fenced JSON from the dispatcher; present tables and prompts in this skill.
