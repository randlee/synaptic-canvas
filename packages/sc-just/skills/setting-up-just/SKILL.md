---
name: setting-up-just
version: 0.1.0
description: >
  Set up a repo-local just task runner with a root Justfile, optional .just/
  helper scripts, and curated help, build, fmt, lint, test, and ci recipes. Use
  when a repo needs just, a Justfile, .just helpers, or when the user mentions
  task automation, "just build", "just lint", "just fmt", or dropping in a just
  system.
---

# Setting Up Just

Use this skill when a repository needs a consistent `just` command surface.
Prefer the `atm-core` pattern: keep the root `Justfile` readable and move
non-trivial orchestration into `.just/*.py` helpers.

Within this package, the helpers are intentionally generic. Repo-specific
commands, aliases, and discovery knobs belong in `.just/config.toml`.

## Scope

Use this skill for:
- adding a new root `Justfile`
- introducing a `.just/` helper directory
- standardizing `help`, `build`, `fmt`, `lint`, `test`, and `ci` recipes
- replacing ad hoc shell snippets with small Python helpers when recipes get noisy

Do not use this skill for:
- one-off shell aliases
- large build-system migrations that should stay in an existing framework
- repos that already have a strong task-runner standard the user wants preserved

## Step 1 - Verify Dependencies

Before editing files:
1. Verify `just >= 1.0` is installed:
   - `command -v just || which just`
   - `just --version`
2. Verify `python3 >= 3.11` is available:
   - `command -v python3 || command -v python`
   - `python3 -c "import sys; print(sys.version)" || python -c "import sys; print(sys.version)"`
3. If either command is missing from `PATH`, check common install locations before
   assuming the tool is absent:
   - `~/.cargo/bin`
   - `/opt/homebrew/bin`
   - `$HOME/.local/bin`
4. Enforce the version floor before continuing:
   - stop if `just --version` reports lower than `1.0`
   - stop if the resolved Python interpreter reports lower than `3.11`
5. If dependency discovery or version checks fail, read
   `references/installation-and-troubleshooting.md` and do not continue until the
   tool is both discoverable and new enough.
6. Inspect the repo for existing task surfaces such as `Makefile`, `package.json`,
   `pyproject.toml`, `Cargo.toml`, `scripts/`, or CI workflows.
7. If a `Justfile` already exists, merge carefully instead of replacing it.

## Template Selection

Read `references/template-catalog.md` and choose the closest profile:
- `minimal` for a generic starter with placeholder command lists
- `python` for Python repos that can use `ruff` + `pytest`
- `go` for Go repos where `go build ./...` and `go test ./...` from repo root
  are the correct default
- `dotnet` for .NET repos where root-level `dotnet build` and `dotnet test`
  are the correct default
- `rust` for Cargo workspaces that want the `atm-core` shape

Then read `references/adoption-workflow.md` and adapt the copied files to the
repo's real toolchain. If dependency setup is failing, also read
`references/installation-and-troubleshooting.md`.

## Workflow

When applying this skill:

1. Detect the repo shape and choose the closest template profile.
2. Copy the selected template files into the repo root.
3. Update `.just/config.toml` so all repo-specific commands and aliases match the
   target repo.
4. Keep the top-level `Justfile` concise; prefer delegating branching logic to `.just/*.py`.
5. If the repo already has scripts or package-manager entry points, call those from
   `just` instead of re-implementing their behavior.
6. Verify the final surface with non-destructive checks first:
   - `just help`
   - `just build` when the template exposes it
   - `just fmt check` or the repo-safe equivalent
   - `just lint`
   - `just test`
7. If a verification command fails, do not leave the template in a knowingly
   broken state:
   - change `.just/config.toml` first when the repo uses different commands
   - only add or change helper scripts when direct config updates are no longer
     adequate
   - if the repo surface is still unresolved, report the failure clearly and stop
     instead of claiming the setup is complete

## Output Expectations

When using this skill, report:
- which template profile you selected and why
- what commands were wired into `fmt`, `lint`, `test`, and `ci`
- any repo-specific deviations from the starter template
- whether `.just/config.toml` stayed sufficient or whether helper code had to change
- which verification commands passed and which were not run

## References

- `references/template-catalog.md`
- `references/adoption-workflow.md`
- `references/installation-and-troubleshooting.md`

## Agent Delegation

This skill operates directly in the main session. It does not require background
agents or Task-tool delegation.
