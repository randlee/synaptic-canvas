# CI Automation Commands & Detection

## Stack Detection Heuristics
- **.NET**: Presence of `.sln` or `.csproj`; build: `dotnet build`; test: `dotnet test`; warnings: `warning CS\d+`, `warning NU\d+`.
- **Python**: `pyproject.toml`, `setup.py`, or `requirements.txt`; build/install: `pip install -e .` or `poetry install`; test: `pytest`; warnings: `DeprecationWarning`, `FutureWarning`.
- **Node.js**: `package.json`; build: `npm run build` or `npm install`; test: `npm test`; warnings: `npm WARN`, `eslint` warnings.
- **Rust**: `Cargo.toml`; build: `cargo build`; test: `cargo test`; warnings: `warning:` lines.

## Suggested Commands
- `build_command`: detected or prompted (stack-specific as above).
- `test_command`: detected or prompted.
- `warn_patterns`: stack-specific regexes to flag warnings.
- `validate_command` (optional): e.g., format/lint check (`dotnet format --verify-no-changes`, `npm run lint`, `ruff`, `eslint`).

## Flag Precedence
- `--build` and `--test` are mutually exclusive; if both provided, exit with an error and show help.
- `--yolo` only meaningful when gates are clean; otherwise fall back to conservative path.

## Protected Branch Guidance
- Dest inferred from tracking; `--dest` overrides. Confirm before PR to main/master.
