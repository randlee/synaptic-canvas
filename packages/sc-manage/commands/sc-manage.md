---
allowed-tools: Bash(python3 scripts/sc_manage_dispatch.py*)
name: sc-manage
description: List, install, or uninstall Synaptic Canvas packages for Claude, Codex, Cursor, or Hermes.
version: 0.14.1
options:
  - name: --list
    description: List available packages and show install status (no/global/local) with a summary table.
  - name: --install
    args:
      - name: package
        description: "Package name to install (e.g., sc-delay-tasks, sc-git-worktree)."
    description: Install a package. Use --local/--project or --global/--user to choose scope.
  - name: --uninstall
    args:
      - name: package
        description: Package name to uninstall.
    description: Uninstall a package from the chosen scope.
  - name: --docs
    args:
      - name: package
        description: "Package name whose documentation to display (alias: --doc)."
    description: Show package documentation (README) for review and Q&A.
  - name: --local
    description: Use the current repository's selected target directories.
  - name: --project
    description: Alias for --local.
  - name: --global
    description: Use the selected targets' global/profile directories.
  - name: --user
    description: Use the selected targets' user/profile directories.
  - name: --claude
    description: Select Claude (the default when no target flag is supplied).
  - name: --codex
    description: Select Codex skills, scripts, and assets.
  - name: --cursor
    description: Select Cursor skills, scripts, and assets. sc-manage also installs a Cursor-native /sc-manage command.
  - name: --hermes
    description: Select Hermes skills, scripts, and assets; project skills require explicit Hermes trust.
---

# /sc-manage

Manage Synaptic Canvas packages:
- Use `--list` to see available packages and whether they are installed locally or globally.
- Use `--install <package>` with `--local`/`--project` or `--global`/`--user` to install.
- Use `--uninstall <package>` with `--local`/`--project` or `--global`/`--user` to remove.
- Add any combination of `--claude`, `--codex`, `--cursor`, `--hermes` to install,
  uninstall, or list. With no target flag, only Claude is selected. Unknown or
  conflicting flags fail before installation; scopes and targets are separate.
  A Cursor install of this package also provides `/sc-manage` as a Cursor command.

Notes:
- Some packages are local-only (e.g., sc-git-worktree). The manager will block global installation for those.
- Listing includes: Package | Installed | Description.

## Context

- Package status and actions: !`python3 scripts/sc_manage_dispatch.py $ARGUMENTS`
