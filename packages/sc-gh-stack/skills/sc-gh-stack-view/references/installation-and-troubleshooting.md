# Installation and troubleshooting

Read this when `gh`, the `gh-stack` extension, `git`, or `python3` might be missing or too old before any `sc-gh-stack` workflow runs — it is the CLI-dependency doc this skill's SKILL.md Step 1 points to, per the repo's skill guidelines (`docs/claude-code-skills-agents-guidelines.md`).

This skill depends on:
- `gh` (GitHub CLI), authenticated
- the `gh-stack` extension (`github/gh-stack`), v0.1.0
- `git`
- `python3` (for any accompanying stdlib-only scripts)
- stacked pull requests enabled on the target GitHub repository

## Check First

```bash
which gh && gh --version
gh extension list | grep stack
gh stack --version
which git && git --version
python3 --version
```

Skip installation for anything already present. `gh stack --version` (not `gh stack version`) reports the installed extension version, e.g. `gh stack version 0.1.0`.

## Find Existing Install

If `which`/`command -v` fails for any dependency, probe common locations before concluding it is absent:

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && "$d/$cli" --version && break
  done
done
```

If a binary exists off-PATH, `export PATH="<dir>:$PATH"` for the session, or call it by absolute path.

## Install

- macOS: `brew install gh`
- Linux: distribution package, or see https://github.com/cli/cli#installation
- Windows: `winget install GitHub.cli`

Then:

```bash
gh auth login
gh extension install github/gh-stack
gh extension upgrade stack
gh stack --version
```

## Minimum Version

- `gh >= 2.0`
- `gh-stack` v0.1.0 (this reference is field-verified against v0.1.0; re-check flags with `--help` if a newer extension version is installed)
- `git >= 2.38` — needed for `git merge-tree --write-tree`, used in conflict pre-checks (see `troubleshooting.md`)
- `python3 >= 3.9`

## PATH Troubleshooting

Claude Code's bash inherits a minimal PATH that may omit directories populated by `.zshrc`/`.bashrc` init (Homebrew, pyenv shims, user-local bin dirs). A `gh` that works in an interactive shell can be silently absent in the agent's shell. Use the probe loop above and export the directory for the session rather than assuming the CLI is missing.

## Validation

```bash
gh stack view --json    # in a worktree that is on a stack branch; exits 0
python3 .claude/scripts/gh_stack_view.py --help
```

`gh stack view --json` exits 0 and prints the stack payload when run from a branch that is part of a tracked stack; run it from trunk or a non-stack branch and it exits **2** (not in a stack) instead — that is expected, not a failure of the tool itself.

## Known Issues

### `gh stack submit` exits 9

Stacked pull requests are not enabled on the repository. This cannot be fixed from the CLI — a repository admin must enable the feature on GitHub. Stop and tell the user.

### `git config rerere.enabled true` prompt on first `init`

The first `gh stack init` in a repo may prompt under a TTY to enable `git rerere`. Pre-set `git config rerere.enabled true` before running `init` to skip the prompt entirely.

### Multiple remotes

`gh stack` commands that push or fetch need a single default remote. If more than one remote is configured: `git config remote.pushDefault origin`. Note `checkout`, `modify`, and `trunk` have no `--remote` flag at all and always rely on `remote.pushDefault`.

### View script needs a checked-out layer

Any wrapper script that shells out to `gh stack view --json` reads the *current* worktree's stack state — it needs at least one stack branch checked out in that worktree. Running it from trunk, or in a worktree that was never part of a stack, returns "not in a stack" (exit 2), not stack data.

### `gh stack help <cmd>` doesn't work

Only the top-level `gh stack --help` / `gh stack help` prints subcommand help. To see a subcommand's own flags, use `gh stack <cmd> --help` (not `gh stack help <cmd>`).

### Commands re-verified against v0.1.0

All flags and behavior in `commands.md` and `troubleshooting.md` were re-confirmed against `gh stack <cmd> --help` output for extension v0.1.0. If the installed extension has moved to a newer version, re-run `gh stack <cmd> --help` for any command before trusting a specific flag name.
