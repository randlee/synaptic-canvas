# Installation and troubleshooting (sc-gh-stack-view)

## Check First

```bash
which gh && gh --version            # >= 2.0
gh extension list | grep -i stack   # github/gh-stack v0.1.0
which git && git --version          # >= 2.38 (merge-tree --write-tree)
python3 --version                   # >= 3.9
gh auth status
```

All present and above the floors: nothing to install. Otherwise the full
guide (Find Existing Install, Install, Minimum Version, PATH Troubleshooting,
Validation, Known Issues) is shared with the sibling skill:
`../../sc-gh-stack/references/installation-and-troubleshooting.md`.

## Validation

```bash
python3 .claude/scripts/gh_stack_view.py --help
python3 .claude/scripts/gh_stack_view.py --no-fetch --no-pr   # local-only view, exit 0/1/2
```

## Known issues specific to this script

- "no open gh stack found": stacks are discovered through `git worktree list`;
  at least one layer must be checked out in a worktree.
- 🔄 or a false NOT COHERENT with `-` rows after an unstack: stale
  per-worktree tracking; `../../sc-gh-stack/references/recipe-stale-tracking.md`.
- Exit 2 with a GraphQL error: `gh auth status`; `--no-pr` gives a local-only
  view meanwhile.
