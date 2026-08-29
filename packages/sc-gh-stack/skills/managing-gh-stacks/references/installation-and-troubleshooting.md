# Installation And Troubleshooting

This skill depends on:
- `gh` (GitHub CLI), authenticated
- the `gh-stack` extension (`github/gh-stack`)
- `git >= 2.23`
- `python3 >= 3.9` (scripts are stdlib-only)
- stacked pull requests enabled on the target GitHub repository

## Check First

```bash
which gh && gh --version
gh extension list | grep gh-stack
gh auth status
git --version
python3 --version
```

Skip installation for anything already present.

## Find Existing Install

If `which` fails for any dependency, probe common locations before concluding it is absent
(pyenv shims matter for `python3`):

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && "$d/$cli" --version && break
  done
done
```

If a binary exists off-PATH, `export PATH="<dir>:$PATH"` for the session or call it by
absolute path.

## Install

- macOS: `brew install gh`
- Linux: distribution package or https://github.com/cli/cli#installation
- Windows: `winget install GitHub.cli`

Then:

```bash
gh auth login
gh extension install github/gh-stack
gh stack version
```

## Minimum Version

- `git >= 2.23`. Upgrade via the platform package manager.
- `python3 >= 3.9`. macOS: `brew install python3`; Linux: distribution package.
- `gh-stack`: use the latest; `gh extension upgrade gh-stack`.

## PATH Troubleshooting

Claude Code's bash inherits a minimal PATH that may omit Homebrew or user-local bin dirs
populated by `.zshrc`/`.bashrc`. A `gh` that works interactively can be absent in the agent
shell. Use the probe loop above and export the directory for the session.

## Validation

```bash
python3 .claude/scripts/gh_stack_preflight.py
```

Expect `success: true`; two `warn` entries are normal — `stacked_prs_enabled` (no direct
probe exists) and `rerere_enabled` (`gh_stack_convert.py` enables it on first run).

## Known Issues

### `gh stack submit` exits 9

Stacked pull requests are not enabled on the repository. This cannot be fixed from the CLI;
a repository admin must enable the feature on GitHub. Stop and tell the user.

### `gh stack` commands hang

A bare `view`, `submit`, `init`, `add`, `checkout`, `switch`, or `modify` opened a prompt or
TUI. Kill it and re-run with the non-interactive form (`--json`, `--auto`, explicit args).
`modify` has no non-interactive form; use `unstack` + `git rebase --onto` + `init` instead.

### "Remote not configured" / wrong remote

More than one git remote and `remote.pushDefault` is unset:
`git config remote.pushDefault origin`. `checkout` and `trunk` have no `--remote` flag.

### Conflicts repeat on every rebase

`rerere` is disabled. `git config rerere.enabled true`; `gh_stack_convert.py` sets this
automatically, but a stack created some other way may not have it.

### `gh stack add` exits 5

`add` only appends above the current top. `gh stack top` first, or use
`gh stack init` to adopt an existing branch set.
