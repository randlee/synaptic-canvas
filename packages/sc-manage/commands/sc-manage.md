---
name: /sc-manage
description: List, install, or uninstall Synaptic Canvas Claude packages for the current machine or this repo.
options:
  - name: --list
    description: List available packages and show install status (no/global/local) with a summary table.
  - name: --install
    args:
      - name: package
        description: Package name to install (e.g., delay-tasks, git-worktree).
    description: Install a package. Use --local or --global to choose scope.
  - name: --uninstall
    args:
      - name: package
        description: Package name to uninstall.
    description: Uninstall a package from the chosen scope.
  - name: --docs
    args:
      - name: package
        description: Package name whose documentation to display (alias: --doc).
    description: Show package documentation (README) for review and Q&A.
  - name: --local
    description: Target the current repository's .claude directory.
  - name: --global
    description: Target the global .claude directory.
---

# /sc-manage

Manage Synaptic Canvas packages:
- Use `--list` to see available packages and whether they are installed locally or globally.
- Use `--install <package>` with `--local` or `--global` to install.
- Use `--uninstall <package>` with `--local` or `--global` to remove.

Notes:
- Some packages are local-only (e.g., git-worktree). The manager will block global installation for those.
- Listing includes: Package | Installed | Description.
