---
name: sc-refactory-install
version: 0.1.0
description: Install the refactory runtime into the current repository.
options:
  - name: --force
    description: Overwrite existing runtime files managed by the installer.
  - name: --seed
    args:
      - name: mode
        description: "Seed mode: empty or templates."
    description: Control whether starter templates are installed.
---

# /sc-refactory-install

Thin entrypoint for the `refactory-install` skill and installer script.

Expected result:

- `.refactor/` runtime layout exists
- `.startup/team-lead` exists
- local install/troubleshooting guide exists
- startup preview can be rendered
