# PR 77 Skills Writeup

## Summary

This branch brings PR 77 onto the `develop` line and packages the resulting skill-facing changes for promotion to `main`.

The work is primarily about two things:

1. documenting and scoping the planned `claude-lint` skill
2. expanding the install surface for `sc-rust` so its guideline references resolve to packaged reference notes instead of repository-only files

## New Skill Work

### `claude-lint` Skill Plan

`[claude-lint-skill-plan.md](claude-lint-skill-plan.md)` defines the first-pass architecture for a new `claude-lint` skill.

The planned skill is intended to audit Claude/Codex prompt surfaces for:

- broken file references
- missing installed dependencies
- drift between package source and installed `.claude` copies
- malformed or incomplete fenced JSON contracts
- missing registry wiring or stale agent names
- stale `sc-compose` examples and template variables

The document also captures an explicit audit workflow, expected outputs, proposed package layout, and validation criteria. It is not the package implementation yet; it is the design and review baseline for building that package cleanly.

## `sc-rust` Skill Surface Additions

`[packages/sc-rust/manifest.yaml](../packages/sc-rust/manifest.yaml)` now ships additional reference-note files that were previously implied by `rust-development/guidelines.txt` but not installed with the package.

New packaged reference-note surfaces:

- `[packages/sc-rust/skills/docs/README.md](../packages/sc-rust/skills/docs/README.md)`
- `[packages/sc-rust/skills/universal/README.md](../packages/sc-rust/skills/universal/README.md)`
- `[packages/sc-rust/skills/ux/README.md](../packages/sc-rust/skills/ux/README.md)`
- `[packages/sc-rust/skills/resilience/README.md](../packages/sc-rust/skills/resilience/README.md)`
- `[packages/sc-rust/skills/libs/ux/README.md](../packages/sc-rust/skills/libs/ux/README.md)`
- `[packages/sc-rust/skills/libs/resilience/README.md](../packages/sc-rust/skills/libs/resilience/README.md)`

These files provide anchor targets for guidance referenced by `[packages/sc-rust/skills/rust-development/guidelines.txt](../packages/sc-rust/skills/rust-development/guidelines.txt)`, including:

- canonical documentation structure
- module documentation expectations
- panic boundaries
- runtime abstraction guidance
- mockable I/O boundaries
- explicit public re-export discipline
- canonical library error types and builder usage

The net effect is that `sc-rust` now installs a self-contained set of note files for the guidelines it asks users and agents to follow.

## Additional Test Hardening

`[tests/test_sc_ai_cli_templates.py](../tests/test_sc_ai_cli_templates.py)` was hardened so generated .NET template fixture projects write a local `global.json` pinned to an installed SDK.

Reason:

- the repository root uses a strict `.NET` SDK pin in `[global.json](../global.json)`
- generated fixture projects are created under the repository tree
- without a local override, `dotnet build` for the generated fixture inherits the repository root SDK lock and fails on machines that do not have that exact SDK patch version installed

This change isolates the generated template test from the repository root SDK lock while preserving the root pin for CI and repository builds.

## Validation Results

The following commands were run against the integrated branch:

- `python3 scripts/validate-all.py`
- `pytest tests/ -v`
- `pytest packages/sc-git-worktree/tests -v`
- `pytest test-packages/harness/tests -v`
- `SC_TEST_HARNESS_PATH=/Users/randlee/Documents/github/sc-test-harness pytest test-packages/fixtures/sc-startup -v`

Observed results:

- `validate-all.py`: passed
- `pytest tests/ -v`: `1300 passed`
- `pytest packages/sc-git-worktree/tests -v`: `132 passed`
- `pytest test-packages/harness/tests -v`: `651 passed`
- `pytest test-packages/fixtures/sc-startup -v`: `7 passed, 2 failed`

Current known `sc-startup` fixture failures:

1. `sc-startup-init-001`
   - expected a `SubagentStart` event for `sc-startup-init`
   - actual run completed with no subagent events collected

2. `sc-startup-missing-001`
   - timed out after 45 seconds when invoking `/sc-startup` without config

These two failures appear to be fixture or behavior mismatches in `sc-startup` rather than regressions introduced by PR 77.

## Why This Release Matters

For `claude-lint`, this branch creates a concrete implementation plan instead of leaving the audit workflow tribal or ad hoc.

For `sc-rust`, it closes a packaging gap: the main Rust guideline skill now installs the reference notes it points at, which reduces broken links, improves portability of the package surface, and makes the package more self-contained when installed into consumer repositories.
