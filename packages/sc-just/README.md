# sc-just

Repo-local `just` setup skill for Synaptic Canvas. Provides a single skill plus
starter templates for adding a root `Justfile` and `.just/` helper scripts to a
repository.

## Skill

### setting-up-just
Choose a starter profile, copy the matching template files into the target repo,
adapt the commands to the repo's actual toolchain, and verify the final `just`
surface.

Each template also ships a `.just/config.toml`. The helpers are intended to stay
generic; repo-specific commands, aliases, and discovery settings live in that
config file.
The helper scripts require `python3 >= 3.11` because they use `tomllib`.
Installed package payload is declared in `manifest.yaml`; `.claude-plugin/plugin.json`
is metadata for marketplace registration and discovery.

## Included Template Profiles

- `minimal` for generic repos that need a thin `just` shell with placeholders
- `python` for Python repos using `ruff` and `pytest`
- `go` for Go repos that want root-level `go build ./...` and `go test ./...`
- `dotnet` for .NET repos that want `just help`, `just build`, and `just test`
  mapped directly to `dotnet build` and `dotnet test` from repo root
- `rust` for Cargo workspaces that want the `atm-core` pattern of a lean
  `Justfile` backed by `.just/*.py` helpers

## Requirements

- `just`
- `python3 >= 3.11`

The Python template assumes `ruff` and `pytest`. The Go template assumes `go`.
The Rust template assumes `cargo` and `clippy`. The `.NET` template assumes
`dotnet` and a repo where root-level `dotnet build` / `dotnet test` are the
right default.

## Storage

This package installs into `.claude/` only. It does not create persistent state
at runtime. The copied `Justfile` and `.just/` helpers live in the target repo.
