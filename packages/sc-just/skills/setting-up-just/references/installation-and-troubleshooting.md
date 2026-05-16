# Installation And Troubleshooting

This skill depends on:
- `just >= 1.0`
- `python3 >= 3.11`

## Verify Installed Versions

Check `just`:

```bash
command -v just || which just
just --version
```

Check Python:

```bash
command -v python3 || command -v python
python3 -c "import sys; print(sys.version)" || python -c "import sys; print(sys.version)"
```

The shipped helper scripts use the standard-library `tomllib` module, so Python
must be `3.11+`.

Do not continue with template installation if either version check is below the
declared floor.

## Find Existing Install

If `command -v` does not find `just` or `python3`, check common user-local
install locations before concluding the dependency is missing:

- `~/.cargo/bin`
- `/opt/homebrew/bin`
- `$HOME/.local/bin`

Useful checks:

```bash
[ -x "$HOME/.cargo/bin/just" ] && "$HOME/.cargo/bin/just" --version
[ -x "/opt/homebrew/bin/just" ] && "/opt/homebrew/bin/just" --version
[ -x "$HOME/.local/bin/just" ] && "$HOME/.local/bin/just" --version
[ -x "/opt/homebrew/bin/python3" ] && "/opt/homebrew/bin/python3" -c "import sys; print(sys.version)"
[ -x "$HOME/.local/bin/python3" ] && "$HOME/.local/bin/python3" -c "import sys; print(sys.version)"
```

If the binary exists but is not on `PATH`, either invoke it with its absolute
path for verification or update the shell environment before proceeding.

## Common Failures

### `just: command not found`

- Check the locations in `Find Existing Install`
- Install `just` if it is not already present
- Verify the selected binary is on `PATH`
- Re-run `just --version`

### `ModuleNotFoundError: No module named 'tomllib'`

- You are running Python older than `3.11`
- Upgrade `python3` and confirm with `python3 --version`

### Version command succeeds but the version is too old

- `just` older than `1.0`: upgrade `just` before continuing
- `python3` older than `3.11`: upgrade Python before continuing
- Do not copy templates that rely on unsupported tool versions

### `missing config file: .../.just/config.toml`

- The template copy is incomplete
- Re-copy the selected profile or restore `.just/config.toml`

### Template command uses the wrong Python binary

The Python template uses a runtime token in `config.toml`:

```toml
["{{python_cmd}}", "-m", "pytest", "-q"]
```

The helper expands that token to the current interpreter path, which avoids
assuming `python` or `python3` resolves correctly on every machine.

### `just lint` or `just test` succeeds with no real work

That should not happen for the shipped `minimal` or `python` helper flows.
Empty command lists are treated as configuration errors and return exit code `2`.
