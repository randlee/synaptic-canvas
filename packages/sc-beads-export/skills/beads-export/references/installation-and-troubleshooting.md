# Installation And Troubleshooting

This package depends on:

- `bd` for reading the live beads board
- `python3` for running the export scripts
- Python package `markdown` for optional HTML site generation
- `zip` only when packaging the export archive

## Check First

```bash
which bd && bd --version
which python3 && python3 --version
python3 -m pip show markdown 2>/dev/null | grep -E "^(Name|Version)"
which zip || true
```

If `bd` or `python3` is missing, do not proceed with the export.

## Find Existing Install

Claude Code's bash environment may not share the same PATH as your interactive shell. Check likely locations before reinstalling:

```bash
for candidate in \
  "$(which bd 2>/dev/null)" \
  "$HOME/.local/bin/bd" \
  "$HOME/.venvs/beads/bin/bd" \
  "$(python3 -m site --user-base 2>/dev/null)/bin/bd" \
  "/opt/homebrew/bin/bd" \
  "/usr/local/bin/bd"; do
  [ -x "$candidate" ] && echo "Found bd at: $candidate" && break
done

for candidate in \
  "$(command -v python3 2>/dev/null)" \
  "/opt/homebrew/bin/python3" \
  "/usr/local/bin/python3"; do
  [ -x "$candidate" ] && echo "Found python3 at: $candidate" && break
done
```

If you find a non-PATH install, either use the full path or export the containing directory:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Adjust the directory to match the path you found.

## Install

### `bd`

Install `bd` using your team's standard beads installation flow. If this repository already documents a preferred install path for beads tooling, follow that first.

If you already have a Python-distributed `bd` package or virtualenv-based install, ensure the executable is on PATH for the shell Claude Code uses.

### `python3`

Most systems already have Python 3 installed. If not:

#### macOS

```bash
brew install python
```

#### Linux

Use your distro package manager, for example:

```bash
sudo apt-get install python3 python3-pip
```

#### Windows

Install Python 3 from `python.org` or the Microsoft Store, then reopen the shell.

### `markdown`

Install the HTML-generation dependency into the Python environment you will use to run the export scripts:

```bash
python3 -m pip install -U markdown
```

### `zip`

`zip` is only needed for `--package`.

#### macOS

`zip` is usually preinstalled.

#### Linux

```bash
sudo apt-get install zip
```

#### Windows

Use Git Bash, WSL, or another environment that provides `zip`, or skip `--package`.

## Minimum Version

- `python3 >= 3.10`
- `bd` must support `bd list --json --all --limit 0`
- `markdown` must be importable from the chosen Python interpreter

## PATH Troubleshooting

If a tool works in your interactive shell but not in Claude Code, add its install directory explicitly before running the export:

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
```

Then re-run the **Check First** commands.

## Validation

Validate the full export runtime:

```bash
bd --version
python3 --version
python3 -c "import markdown; print(markdown.__version__)"
python3 .claude/scripts/beads_export.py --help
```

Validate packaging support only if you need archives:

```bash
zip -v
```

## Known Issues

- Claude Code PATH can be narrower than your login shell PATH.
- `markdown` may be installed for one Python interpreter but not the `python3` used by the skill.
- `zip` may be absent on minimal Linux images and some Windows shells.
- If `bd` is installed in a virtualenv, activate that environment or export its `bin/` directory into PATH first.
