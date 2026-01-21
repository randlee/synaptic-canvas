# Script Dependency Standards

These standards keep package scripts portable and predictable across machines and CI.

## Requirements Declaration

- Every package must declare runtime dependencies in `manifest.yaml` under `requires`.
- Use a structured `requires` object:
  - `cli`: command-line tools (e.g., `python3`, `codex`, `git`)
  - `python`: pip-installable packages required by scripts (e.g., `pydantic`, `pyyaml`)
- If a script imports a package, it must be listed in `requires.python`.
- If a script calls a CLI tool, it must be listed in `requires.cli`.
- Package README should mention any non-obvious dependencies and why they are needed.

Example:

```yaml
requires:
  cli:
    - python3
    - codex
  python:
    - pydantic
    - pyyaml
```

## Installation Behavior

- `sc-manage` installs `requires.python` during package install.
- Prefer a virtualenv; otherwise `pip --user` is used.
- If dependency installation fails, the install should fail with a clear error.

## Script Hygiene

- Avoid hidden dependencies (no implicit `pip install` in scripts).
- Do not assume global site-packages availability.
- Keep imports minimal and standard-library when possible.
