---
name: managing-sc-packages
description: List, install, or uninstall Synaptic Canvas packages (sc-manage). Use when the user wants /sc-manage, /managing-sc-packages, or to install package skills and scripts for Claude, Codex, Cursor, or Hermes.
version: 0.14.2
---

# Managing Synaptic Canvas Packages

Use this skill to manage Synaptic Canvas packages on this machine or in the current repo.
Packages are more than a `SKILL.md` file: many skills need their scripts. Use the
native plugin manager or the artifact installer below, not hand-copied skill files.

## Native Codex plugins

On Codex, prefer its native plugin commands for marketplace discovery and
profile-level plugin installation unless the user explicitly requests artifact
copying, project scope, or other hosts. No Claude session or source checkout is
required for this route. Check `codex plugin --help` if these commands are absent;
report the unsupported CLI rather than silently switching installation models.

```bash
codex plugin marketplace list --json
codex plugin list --available --marketplace synaptic-canvas --json
codex plugin add sc-gh-stack@synaptic-canvas --json
codex plugin remove sc-gh-stack@synaptic-canvas --json
```

Register `codex plugin marketplace add randlee/synaptic-canvas --ref develop`
only if the marketplace is missing and installation/setup is requested. Preserve
an existing source/ref; refresh it with `codex plugin marketplace upgrade
synaptic-canvas` when requested. During review, use the feature ref supplied by
the user instead of develop. Do not upgrade, install or remove during a status query.
The Codex catalog mirrors every existing marketplace plugin, including forwarded
sources. Prefer inclusion: unverified host-specific workflows are caveats, not
grounds to hide a plugin or block a requested install. Report concrete missing
dependencies or execution errors without claiming an untested workflow is broken.
Catalog presence and successful installation do not certify end-to-end behavior.
For package docs, read the bundled README relative to this skill's plugin root.

These are native installed/enabled plugins in the current `CODEX_HOME`, not loose
artifact installations. Do not use dispatcher status to describe native plugin
state or dispatcher uninstall to remove a native plugin. Native installation
does not run this repository's Python install hooks. For cross-host or project
artifact installs from a native cached plugin, set `SC_REPO_PATH` to a full
Synaptic Canvas checkout containing `tools/sc-install.py` first.

## Execution

Resolve `../../scripts/sc_manage_dispatch.py` relative to this skill directory
and run it with the user's flags unchanged. Use the absolute path; do not assume
`.claude`. This is the artifact installer on every host, not Codex's native
plugin manager. The following flags and scope conventions apply to that route.

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
