---
allowed-tools: Bash(python3 scripts/sc_manage_dispatch.py*)
name: sc-manage
description: List, install, or uninstall Synaptic Canvas Claude packages for the current machine or this repo.
version: 0.7.0
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
    description: Target the current repository's .claude directory.
  - name: --project
    description: Alias for --local.
  - name: --global
    description: Target the global .claude directory.
  - name: --user
    description: "Alias for --global (defaults to ~/.claude)."
---

# /sc-manage

Manage Synaptic Canvas packages:
- Use `--list` to see available packages and whether they are installed locally or globally.
- Use `--install <package>` with `--local`/`--project` or `--global`/`--user` to install.
- Use `--uninstall <package>` with `--local`/`--project` or `--global`/`--user` to remove.

Notes:
- Some packages are local-only (e.g., sc-git-worktree). The manager will block global installation for those.
- Listing includes: Package | Installed | Description.

## Context

- Package status and actions: !`python3 scripts/sc_manage_dispatch.py $ARGUMENTS`
