---
name: refactory-install
version: 0.1.0
description: >
  Use this skill to materialize the refactory runtime into a repo by creating
  `.refactor/` and `.startup/`, copying the runtime scripts, writing the local
  install/troubleshooting guide, and verifying startup output and preflight.
---

# Refactory Install

Use this skill after the policy design is stable enough to bootstrap a repo.

## What This Installs

- `.refactor/docs/`
- `.refactor/rules/`
- `.refactor/profiles/`
- `.refactor/scripts/`
- `.refactor/reports/`
- `.refactor/db/`
- `.refactor/logs/`
- `.refactor/temp/`
- `.startup/team-lead`

The runtime scripts are copied from the installed package scripts into the
repo-local `.refactor/scripts/` folder.

## Installation Preconditions

Before running the installer, confirm:

- the repo root is known
- the rule design is stable enough to define runtime layout
- `oxigraph` is installed from crates.io or the user accepts installer guidance
- the repo should receive a local-only install

## How To Invoke

Resolve the installed package script from the local repo first, then fall back
to the global install if needed.

Local-first pattern:

```bash
repo_root="$(git rev-parse --show-toplevel)"

if [ -f "$repo_root/.claude/scripts/install_refactory.py" ]; then
  python3 "$repo_root/.claude/scripts/install_refactory.py" --repo-root "$repo_root"
else
  python3 "$HOME/.claude/scripts/install_refactory.py" --repo-root "$repo_root"
fi
```

Optional flags:

- `--force` to refresh runtime-managed files
- `--seed empty` for runtime only
- `--seed templates` to include starter rule templates

## What The Installer Must Do

1. Resolve the target repo root.
2. Create `.refactor/` directories.
3. Create `.startup/team-lead`.
4. Copy runtime scripts into `.refactor/scripts/`.
5. Write `.refactor/.gitignore`.
6. Write `.refactor/docs/install-and-troubleshooting.md`.
7. Optionally install starter templates.
8. Render a startup preview.

## Expected Result

- `.refactor/.gitignore` ignores `db/`, `logs/`, and `temp/`
- `.startup/team-lead` exists
- `.refactor/scripts/session_start.py` exists
- `.refactor/docs/install-and-troubleshooting.md` exists
- `python3 .refactor/scripts/preflight.py --skill refactor-lookup` prints
  `oxigraph v ... checks pass` when the environment is healthy

## Verification Checklist

After installation, verify:

1. `.startup/team-lead` executes without traceback
2. `python3 .refactor/scripts/session_start.py --mode startup` prints a trigger
   block or `(no triggers registered yet)`
3. `python3 .refactor/scripts/preflight.py --skill refactor-lookup` succeeds
   when the runtime is healthy
4. `.refactor/db/`, `.refactor/logs/`, and `.refactor/temp/` are ignored by
   `.refactor/.gitignore`

## Failure Handling

- If `oxigraph` is missing, surface the install guidance and stop.
- If the repo already contains user-authored rules or docs, do not overwrite
  them unless `--force` or explicit approval says to do so.
- If startup preview fails, keep the installed files but report the exact stage
  that failed.

## Safety

- Do not overwrite existing rule docs or TTL files unless the user asked for it.
- Runtime scripts may be refreshed during reinstall.
- The installer should be deterministic and low freedom.
- Treat `.refactor/docs/` and `.refactor/rules/` as user-owned content.
