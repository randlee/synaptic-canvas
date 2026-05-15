# Template Catalog

This skill ships three starter profiles under `assets/templates/`.

## `minimal`

Use for generic repos where the task surface is not yet known or the repo uses a
custom toolchain.

Included files:
- `Justfile`
- `.just/config.toml`
- `.just/print_help.py`
- `.just/task_runner.py`
- `.just/run_fmt.py`
- `.just/run_lint.py`
- `.just/run_tests.py`

Characteristics:
- keeps a thin root `Justfile`
- routes execution through Python helpers
- keeps all repo-specific commands in `.just/config.toml`
- intentionally ships placeholder command arrays in config that must be customized

Choose this when the repo is unusual, mixed-language, or you want a neutral
starting point.

## `python`

Use for Python repos that can adopt a `ruff` + `pytest` baseline.

Included files:
- `Justfile`
- `.just/config.toml`
- `.just/print_help.py`
- `.just/task_runner.py`
- `.just/run_fmt.py`
- `.just/run_lint.py`
- `.just/run_tests.py`

Characteristics:
- `fmt check` runs `ruff format --check` then `ruff check`
- `fmt write` runs `ruff format` then `ruff check --fix`
- `lint` runs `ruff check`
- `test` runs `pytest -q`
- repo-specific command variants should be edited in `.just/config.toml`, not the
  Python helpers

Adjust command prefixes if the repo uses `uv run`, `poetry run`, `pipenv run`,
or a checked-in venv path.

## `go`

Use for Go repos where running `go build ./...` and `go test ./...` from repo
root is the right default.

Included files:
- `Justfile`
- `.just/config.toml`
- `.just/print_help.py`

Characteristics:
- `just build` runs `go build ./...`
- `just test` runs `go test ./...`
- `just fmt` runs `gofmt -w .`
- `just lint` runs `go vet ./...`
- `.just/config.toml` carries help text and lightweight repo metadata for the
  default template

For repos that need custom package targeting, generation steps, or nonstandard
build/test orchestration, start from this template and add repo-specific scripts
 only when the direct root commands stop being adequate.

## `dotnet`

Use for .NET repos where running `dotnet build` and `dotnet test` from repo
root is the right default.

Included files:
- `Justfile`
- `.just/config.toml`
- `.just/print_help.py`

Characteristics:
- `just build` runs `dotnet build`
- `just test` runs `dotnet test`
- `just ci` runs `build` then `test`
- `.just/config.toml` only carries help text and lightweight repo metadata for
  the default template

For multi-solution or highly customized repos, start from this template and add
repo-specific scripts only when the direct root commands stop being adequate.

Choose this when the immediate requirement is a clean help/build/test surface and
the repo does not yet need extra lint or formatting recipes.

## `rust`

Use for Cargo workspaces or single-crate repos that want the same general shape
as `atm-core`: a readable `Justfile` plus `.just/` Python orchestration.

Included files:
- `Justfile`
- `.just/config.toml`
- `.just/print_help.py`
- `.just/run_fmt.py`
- `.just/run_lint.py`

Characteristics:
- `fmt` delegates to Python helpers that call `just _fmt-check` or `just _fmt-write`
- `lint all` runs `fmt` then `clippy`
- `build` and `test` stay as direct Cargo recipes
- Windows-aware shell and `clippy` target selection match the `atm-core` style
- repo-specific command surfaces stay in `.just/config.toml`

Use this when the repo already centers on Cargo and you want the `Justfile`
structure to stay close to `atm-core` without copying its repo-specific lints.
