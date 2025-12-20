---
name: sc-ci-automation
version: 0.1.0
description: Run CI quality gates (pull → build → test) with optional auto-fix and PR.
---

# /sc-ci-automation command

Unified CI automation entrypoint. Delegates to the `sc-ci-automation` skill and agents; keeps logic thin.

## Flags
- `--build`: Pull + build only (skip tests/commit/push/PR)
- `--test`: Pull + build + test (skip commit/push/PR)
- `--dest <branch>`: Override inferred upstream/target branch
- `--src <branch>`: Override inferred source branch/worktree
- `--allow-warnings`: Allow warnings to pass gates (default: block)
- `--yolo`: Auto-commit/push/PR after gates pass
- `--patch`: Increment patch version before building (optional)
- `--help`: Show usage and examples, then exit

**Flag precedence**: `--build` and `--test` are mutually exclusive; if both are provided, exit with an error and show help.

## Behavior
- Defaults: Pull → build → test → (optional) fix → (optional) PR. Conservative mode stops before commit/push/PR unless clean and confirmed; `--yolo` performs commit/push/PR once gates are satisfied.
- Honors inferred branches: source from current branch; dest from tracking/upstream. `--src`/`--dest` override.
- Calls Agent Runner for all agent invocations (registry-enforced, audited).
- Reads config from `.claude/ci-automation.yaml` (preferred) or `.claude/config.yaml` (fallback) for `upstream_branch`, `build_command`, `test_command`, `warn_patterns`, `allow_warnings`, `auto_fix_enabled`, `pr_template_path`.

## Help Output (example)
```
/sc-ci-automation - Run end-to-end CI quality gates

Usage:
  /sc-ci-automation [flags]

Flags:
  --build              Run pull + build only (skip tests/PR)
  --test               Run pull + build + test (skip commit/push/PR)
  --dest <branch>      Override target branch for PR (default: inferred)
  --src <branch>       Override source branch/worktree (default: current branch)
  --allow-warnings     Allow warnings to pass quality gates
  --patch              Increment patch version before building
  --yolo               Enable auto-commit/push/PR (requires clean gates)
  --help               Show this help message

Examples:
  /sc-ci-automation --test
  /sc-ci-automation --dest main --patch
  /sc-ci-automation --yolo
```
