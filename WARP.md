# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

Synaptic Canvas is a small Python-backed repo that packages “Claude Code” artifacts (commands, skills, agents) into installable bundles under `packages/`. Developers use the provided installer (`tools/sc-install.sh` or `tools/sc-install.py`) to copy a package’s artifacts into a target repository’s `.claude/` directory, optionally performing token substitution (e.g., `{{REPO_NAME}}`).

Key components:
- `packages/<name>/` contains a `manifest.yaml` plus artifacts:
  - `commands/*.md` — user-facing slash commands
  - `skills/*/SKILL.md` — orchestration/workflows
  - `agents/*.md` — isolated executors with structured outputs
  - `scripts/*` — helper scripts copied into `.claude/scripts`
- `tools/` contains the installer entry points:
  - `sc-install.sh` — Bash installer used directly or via curl piping
  - `sc-install.py` — Python wrapper that forwards to `scpy.sc_install`
- `scpy/` contains Python utilities used by scripts and tests:
  - `sc_install.py` — reads `manifest.yaml`, lists/info, installs/uninstalls artifacts, performs token substitution, and sets executable bits for `scripts/*`
  - `delay_run.py` — the Python implementation of the delay/poll helper used by the `delay-tasks` package
- `tests/` uses `pytest` to validate the installer, token expansion, and delay behavior
- `.github/workflows/tests.yml` runs CI across major OSes on Python 3.12

Representative packages:
- `packages/git-worktree/` (Tier 1): installs commands/skills/agents to manage Git worktrees; uses `{{REPO_NAME}}` tokens resolved from the Git toplevel
- `packages/delay-tasks/` (Tier 0): installs delay commands/skills/agents and a helper script; no token substitution

## Dev environment and prerequisites

- Python 3.12+
- Git (required by tests and for resolving `REPO_NAME` in the installer)

Quick setup:

- macOS/Linux
  - Create and activate a venv, then install dev deps
    - `python3 -m venv .venv && source .venv/bin/activate`
    - `pip install -r requirements-dev.txt`
- Windows (PowerShell)
  - `py -m venv .venv; .\.venv\Scripts\Activate.ps1`
  - `pip install -r requirements-dev.txt`

## Common commands

Testing (pytest):
- Run all tests (matches CI): `pytest -q`
- Run a single test file: `pytest -q tests/test_sc_install.py`
- Run a single test: `pytest -q tests/test_sc_install.py::test_install_and_uninstall_delay_tasks`
- Filter by keyword: `pytest -q -k delay_run`

Installer usage (from repo root):
- List available packages:
  - Bash: `./tools/sc-install.sh list`
  - Python: `python3 tools/sc-install.py list`
- Show package manifest:
  - `python3 tools/sc-install.py info git-worktree`
- Install to another repo’s `.claude/` directory (token substitution if defined in manifest):
  - `python3 tools/sc-install.py install git-worktree --dest /path/to/your-repo/.claude`
- Uninstall from `.claude/`:
  - `python3 tools/sc-install.py uninstall git-worktree --dest /path/to/your-repo/.claude`

Delay helper (local runs without installing):
- Python module: `python3 -m scpy.delay_run --minutes 2 --action "go"`
- Script (as installed by `delay-tasks`): `.claude/scripts/delay-run.py --every 60 --for 5m --action "done"`

Lint/build:
- Linting is not configured in this repository.
- No build/package step is defined; the installer copies artifacts to the consumer repo’s `.claude/`.

## Big-picture architecture

1) Packages and manifests
- Each package has a `manifest.yaml` that declares `artifacts` to copy into a target `.claude/` directory. Optional `variables` allow token substitution during install. In Tier 1 packages (e.g., `git-worktree`), `REPO_NAME` is auto-resolved from the Git toplevel of the destination repo.

2) Installer flow (Bash or Python)
- list/info: enumerates packages and prints `manifest.yaml`
- install:
  - Validates `--dest` points to a `.claude` directory
  - Copies all declared artifacts, preserving relative paths (e.g., `agents/*.md`, `skills/*/SKILL.md`, `commands/*.md`, `scripts/*`)
  - Makes any `scripts/*` artifacts executable
  - Performs best-effort token substitution (e.g., replacing `{{REPO_NAME}}`) when defined in `manifest.yaml`
- uninstall: removes previously installed artifact paths for that package from the destination `.claude/`

3) Delay/poll utilities
- `packages/delay-tasks` supplies `.claude/scripts/delay-run.*` used by its agents
- `scpy/delay_run.py` mirrors the shell script logic for one-shot delays (`--seconds|--minutes|--until`) and bounded polling (`--every` with `--for` or `--attempts`), emitting periodic heartbeats and a single final `Action: ...` line (unless suppressed)

4) Tests and CI
- `pytest` is used; `tests/conftest.py` adds the repo root to `sys.path` so `scpy` can be imported without installing a package
- `tests/test_sc_install.py` initializes a temporary Git repo to exercise token expansion and artifact copying; it expects Git to be available
- GitHub Actions run `pip install -r requirements-dev.txt` followed by `pytest -q` on Python 3.12 across Linux/macOS/Windows

## Notes for agents operating in this repo
- Prefer `python3 tools/sc-install.py ...` for cross-platform behavior (the Bash script is also supported and used in README examples)
- When installing to a destination, ensure `--dest` is a `.claude` directory under a valid Git repo root if token substitution is desired
- Avoid long sleeps in tests: the test suite passes mocks for `sleep`/`print` where appropriate; real sleeping is not required
