---
name: sc-gh-stack-view
version: 0.1.0
description: One-call coherence, mergeability, CI and LANDING table for every open gh stack. Use for any stacked-PR status question, before and after every link, unstack, rebase or merge, or /sc-gh-stack-view. Never check layers one branch at a time.
entry_point: /sc-gh-stack-view
---

# sc-gh-stack-view

Read-only stack status. One command replaces the "one `gh pr view` per branch"
habit, which never shows the two things that actually break stacks:

1. **Base coherence** - is each layer's base SHA the head SHA of the layer
   below (and the bottom layer's base the trunk head)? Only
   `gh stack view --json` exposes `head` and `base`; `gh pr view` does not.
2. **Rebase / mergeability** - `needsRebase` from gh stack plus GitHub's
   `mergeable` and `mergeStateStatus` (`CONFLICTING`, `BEHIND`, `DIRTY`,
   `BLOCKED`, `CLEAN`). `gh pr list` and `gh pr checks` do not return
   `needsRebase`, and `gh pr checks` output must never be text-parsed.

The script also compares every local head against `origin/<branch>` and the
PR's `headRefOid`, so stale local tracking (someone else rebased the stack) is
caught before anyone runs `gh stack sync` on top of it.

## Step 1 — Verify gh, gh-stack extension, git, python3

Before running the script, confirm the toolchain is present:

```bash
which gh && gh --version            # >= 2.0
gh extension list | grep -i stack && gh stack --version   # github/gh-stack v0.1.0
which git && git --version          # >= 2.38
python3 --version                   # >= 3.9
gh auth status                      # needed unless --no-pr
```

If any is missing, probe the usual off-PATH locations first (Claude Code's
bash may not share PATH with the interactive shell):

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && echo "$cli found at: $d/$cli" && break
  done
done
```

Found off-PATH: `export PATH="<dir>:$PATH"` for this session. Still missing,
below the floors (git < 2.38, gh < 2.0, python3 < 3.9), or no gh-stack
extension: read `references/installation-and-troubleshooting.md` and stop;
do not work around a missing `gh`, `gh-stack` or `git`.

## Usage

```
/sc-gh-stack-view [--trunk <branch> | --phase aw] [--all] [--no-fetch] [--no-pr] [--json]
```

Run from anywhere in the repo, normally the main checkout on `develop` or
`main`. The script discovers every stack by running `gh stack view --json` in
each worktree from `git worktree list` (concurrently), keeps the longest view
of each stack (a lower-layer worktree only sees the layers linked from it),
and joins them into one report. The default view shows every stack that still
has an open layer, on any trunk. `--trunk`/`--phase` narrows to one trunk
(`--phase` is shorthand for `--trunk integrate/phase-<x>`); `--all` also shows
merged/closed stacks. Hidden stacks are counted on a `hidden:` line.

```bash
python3 .claude/scripts/gh_stack_view.py --trunk develop
```

Under a plugin install the script is at `$CLAUDE_PLUGIN_ROOT/scripts/gh_stack_view.py`.
If it is at neither path, locate it with `find .claude ~/.claude -name gh_stack_view.py`
and use the newest match.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | every shown stack coherent |
| 1 | problems listed under a VERDICT |
| 2 | nothing to show or the environment failed; stderr says which (see Errors) |

## Errors

Every failure is one `gh-stack-view: ...` line on stderr with the next action,
never a traceback. Exit 2 covers all of these, so read the line:

- `git`/`gh` not on PATH, gh-stack extension missing (`gh extension install github/gh-stack`), not inside a git repository.
- `gh repo view` / `gh api graphql` failure: run `gh auth status`; `--no-pr` gives a local-only view meanwhile.
- GraphQL errors, null data or non-JSON output: same, with the PR numbers named.
- `gh stack view --json` returning an unexpected shape: upgrade gh-stack.
- No open stack found: the line reports how many merged/closed/other-trunk stacks were hidden; use `--trunk`, `--phase` or `--all`.

Non-fatal: a failed `git fetch origin` is warned once and the rebase column
shows ❓ instead of comparing against stale refs. Pruned or unreadable
worktrees are skipped silently (`git worktree prune` cleans them up).

## Output

The script renders everything. **Paste its output verbatim and unfenced**
(no ``` around it) so the markdown table renders in the terminal. The agent
makes no rendering decisions: no reformatting, no re-summarising, no
substituting its own per-branch lookups. Example (as it should appear):

stack: fix/aw-pool-read-migration -> integrate/phase-aw @ 0e640b20a

| L | PR | rebase | merge | CI |
|---|---|---|---|---|
| 1/2 | #1242 | ✅ | 🚧 | 🌀 |
| 2/2 | #1244 | ✅ | 🚧 | 🌀 |

VERDICT: ✅ COHERENT - every base == parent head, every head pushed and on its PR

| Column | Source | Icons |
|--------|--------|-------|
| L | layer / stack depth, bottom first | |
| rebase | `gh stack view --json` `head`/`base`/`needsRebase`, `origin/<branch>` after one fetch, PR `headRefOid` | ✅ not needed (base==parent head and local==origin==PR) · ⚠️ needed · 🔄 local tracking stale, fetch+reset before any sync · ❓ unknown (`--no-fetch`) · 🏁 merged |
| merge | one GraphQL query: `mergeable`, `mergeStateStatus`, `isDraft`; gh stack `isMerged`/`isQueued` | ✅ mergeable now · 🚧 blocked (conflicting, behind, draft, queued, required checks, still computing) · 🏁 merged |
| CI | same query, `statusCheckRollup.state` of the head commit | ✅ green · 🌀 running · ⛔ failed, do not enter · — none |

`VERDICT` names the branch and the owner action for every problem (SHAs
appear there, not in the table). The lowest OPEN layer (layer 1, or the first
layer above already-merged ones) merely behind trunk is a note, not a problem:
do not rebase a layer whose CI could go green just to catch up with trunk. The legend is printed once at the end. `--json` emits
`stacks[].rows[]`, `problems[]`, `notes[]`, `coherent` for agents that need to
branch on the result.

If you see stale local tracking (🔄, or a false `NOT COHERENT` with `-` rows
right after an `unstack`), that is fixed by the recipe in
`../sc-gh-stack/references/recipe-stale-tracking.md`, not by re-running this
script harder.

## Rules the skill enforces by convention

- This is **the** status call for stacks. Do not fan out `gh pr view` per
  branch; that costs N calls and still misses base coherence and needsRebase.
- The script is read-only. `gh stack sync` and `gh stack rebase` rewrite and
  force-push every layer; only the stack writer runs them, and only after this
  rebase column shows ✅ on every layer (otherwise sync re-rebases stale local
  heads over someone else's push and turns PRs CONFLICTING).
- After ANY merge or rebase on a stack, run this again and reconcile before
  dispatching dev or QA against a layer.
- Draft PRs block `gh stack merge`; the table flags them.

## Related

The `sc-gh-stack` skill (`../sc-gh-stack/SKILL.md`) owns the stacked-PR model,
preconditions, and the create/sync/rebase/merge recipes; this skill only
reports status.
