---
name: managing-sc-packages
description: List, install, or uninstall Synaptic Canvas packages. Use with the `/sc-manage` command.
version: 0.14.0
---

# Managing Synaptic Canvas Packages

Use this skill to manage Synaptic Canvas packages on this machine or in the current repo.

## Agent Delegation

When Claude's Task tool and these agents are available, delegate using this table.
On other hosts, or without Task, run `sc_manage_dispatch.py` from `../../scripts/`
relative to this skill's directory with the requested flags. Resolve an absolute
script path; do not assume `.claude`. Installed helpers remember their source
checkout. If it moved or cannot be found, set `SC_REPO_PATH` to the Synaptic
Canvas checkout providing the source packages and `tools/sc-install.py`.

| Operation | Agent | Returns |
|-----------|-------|---------|
| List      | `sc-packages-list`       | JSON: packages [{ name, description, installable_scopes, installed }] |
| Install   | `sc-package-install`     | JSON: success, scope, dest |
| Uninstall | `sc-package-uninstall`   | JSON: success, scope, dest |
| Docs      | `sc-package-docs`        | JSON: readme_path, size_bytes |

## Inputs / Flags

- `--list` → call `sc-packages-list`.
- `--install <package>` → require `--local`/`--project` or `--global`/`--user`; if missing, ask the user. If the package is local-only, force `--local`.
- `--uninstall <package>` → same scope logic as install.
- `--docs <package>` (alias `--doc`) → call `sc-package-docs` to load and present the package README.
- `--claude`, `--codex`, `--cursor`, `--hermes` select targets for install,
  uninstall or list. Flags can be combined; omitted targets mean Claude only.
  Forward the selected names as `targets: ["codex", "hermes"]` to agents/scripts.
  Never silently drop an unsupported flag or substitute another target.

## Conventions

- Local scope: the current repository's `.<target>` directory.
- Project scope: alias for local.
- User scope: `~/.claude` unless `USER_CLAUDE_DIR` is set.
- Global scope: `~/.claude` unless `GLOBAL_CLAUDE_DIR` is set.
- The agents will detect the repo toplevel via `git rev-parse --show-toplevel`.
- The agents call the Synaptic Canvas installer at `<SC_REPO_PATH>/tools/sc-install.py` (default resolved from `SC_REPO_PATH` or the repo root).
- Other targets use `~/.codex`, `~/.cursor`, or `~/.hermes`; Codex and Hermes
  honor `CODEX_HOME` and `HERMES_HOME` for user/global profiles, not project scope.
  `GLOBAL_<TARGET>_DIR` and `USER_<TARGET>_DIR` override the corresponding roots.
- Non-Claude installs copy skills, scripts and assets only, not Claude commands,
  agents, plugin manifests or agent registries. Installation does not translate
  arbitrary Claude-specific workflows into another host's tool interfaces.
- Install/uninstall return `targets` and `destinations`; `dest` remains a string
  for one target and is null for multiple. On failure, report completed targets;
  do not claim rollback. Listing exposes `installed_by_target`; `installed` is
  `mixed` when selected targets differ. Use the mapping for per-target decisions.
- Hermes project skills require `hermes skills trust` inside the repository.
  Tell the user about that step; never grant trust or edit Hermes config silently.

## Safety

- Respect package metadata: if a package manifest declares `install.scope: local-only`, block global installation.
- Return only fenced JSON from agents; present tables and prompts in this skill.
