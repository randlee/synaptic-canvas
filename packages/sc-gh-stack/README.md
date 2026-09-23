# sc-gh-stack

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)

Scope: Local or global
Requires: `gh` >= 2.0 with the `gh-stack` extension (v0.1.0), `git` >= 2.38, `python3` >= 3.9; `jq` optional (documented one-liners only)

Stacked pull requests with the `gh stack` GitHub CLI extension, run the way
that actually lands: an append-only, linear stack of frozen layers above a
named trunk, one stack writer, QA and CI on the top only, one atomic merge.
Two skills: `sc-gh-stack` (the model, preconditions, recipes and the full
command guide) and `sc-gh-stack-view` (the one-call status table). This
package supersedes the generic `gh-stack` skill; uninstall that one to avoid
duplicate guidance.

Security: See [SECURITY.md](../../SECURITY.md) for security policy and practices.

## Summary

Every rule in this package was paid for during five production phases of
stacked development (stacks of 2 to 21 PRs). The skill is a table of
contents that points to one reference per situation:

| Situation | Reference |
|-----------|-----------|
| The model and vocabulary | `references/model.md` |
| Lifecycle of a layer | `references/workflow.md` |
| Checks before every write | `references/preconditions.md` |
| Cut a layer, link, restack, land, stale tracking | `references/recipe-*.md` |
| Layer boundaries and naming | `references/stack-design.md` |
| Every `gh stack` command, flag, exit code, JSON schema | `references/commands.md` |
| Error signatures and fixes | `references/troubleshooting.md` |
| A whole phase on one stack | `references/phase-model-example.md` |

## Quick Start

1. Install into a repo:
   ```bash
   python3 tools/sc-install.py install sc-gh-stack --dest /path/to/your-repo/.claude
   ```
2. Make sure the extension is present:
   ```bash
   gh extension install github/gh-stack
   ```
3. Status of every open stack (read-only, paste verbatim):
   ```
   /sc-gh-stack-view
   ```
4. Before linking a proposed order:
   ```
   /sc-gh-stack --check develop fix/a fix/b docs/c
   ```

## Usage

- `/sc-gh-stack-view [--trunk <branch>] [--all] [--json]`
- `/sc-gh-stack --status | --check <trunk> <layers...> | --cut <layer> | --link | --restack | --land`

Scripts (installed under `.claude/scripts/`). Both are read-only apart from one `git fetch origin` (skip it with `--no-fetch`); neither runs a `gh stack` write command:

| Script | Purpose | Exit codes |
|--------|---------|-----------|
| `gh_stack_view.py` | Coherence (base == parent head), origin vs local vs PR head, `needsRebase`, `mergeStateStatus`, CI rollup, LANDING verdict | 0 coherent, 1 problems, 2 environment |
| `gh_stack_chain_check.py --trunk <t> <bottom> ... <top>` | Pre-link check: pushed heads, linear ancestry, PR state and bases, clean merge into trunk; prints the exact link command | 0 linkable, 1 problems, 2 environment |

## The model in one paragraph

Trunk is the branch the stack lands on (`develop`, `integrate/phase-N`,
whatever you name). Every unit of work is a new worktree cut from the current
pushed top; its PR opens on the first push with base = the layer below and is
linked at once with `gh stack link --base <trunk> ...`. A layer is frozen when
its task closes; findings on it are fixed on a new layer above the top. One
writer per branch, one stack writer for every `gh stack` write. QA and CI gate
the top only. The stack lands once with `gh stack merge --yes --merge`. Small
fixes with one owner do not get a stack at all.

## Safety

- The scripts never run a `gh stack` write command.
- The skill confirms landing, closing PRs and unstacking with the user unless
  the user directed that exact action.
- Never `--squash`, never `gh pr merge --admin`, never edit rulesets.

## Storage

Installs into `.claude/` only (commands, skills, scripts). Writes no logs, settings, state or output under `.claude/state/` or `.sc/`. Stack tracking is gh-stack's own per-worktree state; see `references/recipe-stale-tracking.md`.

## Install / Uninstall

```bash
python3 tools/sc-install.py install sc-gh-stack --dest /path/to/your-repo/.claude
python3 tools/sc-install.py uninstall sc-gh-stack --dest /path/to/your-repo/.claude
```

## Tests

```bash
python3 -m pytest packages/sc-gh-stack/tests -q
```

## Troubleshooting

- "no open gh stack found": a stack is discovered through `git worktree list`
  and needs at least one layer checked out in a worktree.
- 🔄 or a false NOT COHERENT with `-` rows after an unstack: stale per-worktree
  tracking; see `references/recipe-stale-tracking.md`.
- Anything else: `references/troubleshooting.md` and
  `references/installation-and-troubleshooting.md`.

## Components

- Commands: `commands/sc-gh-stack.md`, `commands/sc-gh-stack-view.md`
- Skills: `skills/sc-gh-stack/SKILL.md` (+ `references/`), `skills/sc-gh-stack-view/SKILL.md`
- Scripts: `scripts/gh_stack_view.py`, `scripts/gh_stack_chain_check.py`
