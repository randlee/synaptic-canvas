# Adoption Workflow

Use this sequence when applying a starter profile to a repo.

## 1. Inspect Before Copying

Look for:
- existing `Justfile` or `.just/`
- current automation surfaces: `Makefile`, `package.json`, `pyproject.toml`, `Cargo.toml`
- checked-in scripts under `scripts/`, `tools/`, or `.github/workflows/`

Preserve repo conventions. The `just` layer should unify existing commands, not
fight them.

## 2. Choose the Narrowest Useful Template

- Start with `rust` for Cargo-first repos.
- Start with `python` for Python repos that already use or can adopt `ruff` and `pytest`.
- Start with `go` for Go repos where `go build ./...` and `go test ./...` from
  repo root are already correct.
- Start with `dotnet` for .NET repos where `dotnet build` and `dotnet test` from
  repo root are already correct.
- Start with `minimal` when the stack is mixed or the commands still need discovery.

Avoid copying more helper files than the repo needs.

## 3. Adapt the Command Surface

Prefer these recipe names when relevant unless the repo has a strong existing standard:
- `help`
- `fmt`
- `lint`
- `test`
- `build`
- `clean`
- `ci`

Keep `ci` as a composition recipe such as `ci: lint test`.

If the repo already has stable entry points, call them:
- `cargo test --workspace`
- `go build ./...`
- `go test ./...`
- `dotnet build <solution-or-project>`
- `dotnet test <solution-or-project>`
- `python -m pytest -q`
- `npm test`
- `pnpm lint`

## 4. Keep Logic Out of the Justfile

Follow the `atm-core` pattern when recipes start accumulating:
- argument validation
- target dispatch
- cross-platform branching
- repeated subprocess orchestration

Move that logic into `.just/*.py` helpers and let recipes stay declarative.
Keep repo-specific commands, aliases, and discovery settings in
`.just/config.toml` so the helpers stay generic.

## 5. Verify Safely

Run the safest commands first:
- `just --version`
- `just help`
- `just fmt check` or the repo-safe equivalent
- `just lint`
- `just test`

If a template command fails because the tool is wrong for the repo, change the
`.just/config.toml` first instead of documenting the failure away. Only change
helper code when the config layer is no longer sufficient. If the verification
surface still fails after adaptation, stop and report the failing command rather
than leaving a broken template behind.

## 6. Document Only When the Repo Already Documents Local Tooling

If the repo has a contributor guide or README section for local development,
update it to mention the new `just` entry points. Do not add redundant docs when
the repo does not already maintain that surface.
