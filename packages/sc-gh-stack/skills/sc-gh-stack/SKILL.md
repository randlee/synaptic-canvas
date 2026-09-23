---
name: sc-gh-stack
version: 0.1.0
description: Run stacked PRs with the gh stack extension the way that lands (append-only frozen layers on a named trunk, one stack writer, QA/CI on the top, one atomic merge). Use for any stack, stacked/dependent PRs, gh stack link/unstack/merge, landing, a red layer, or /sc-gh-stack. Supersedes /gh-stack.
entry_point: /sc-gh-stack
---

# sc-gh-stack

Supersedes the generic `/gh-stack` skill; its command guide lives in
`references/commands.md`. A stack exists so CI completes once, on the landing head, and the merge
happens once. Every rule here was paid for in production: the "why" lines
cite the incident. This file is the table of contents; read the reference a
step points to before acting, and nothing else.

## Step 1 — Verify gh, the gh-stack extension, git, python3

```bash
which gh && gh --version
gh extension list | grep -i stack && gh stack --version
which git && git --version
which python3 && python3 --version
```

If any is missing, probe the usual off-PATH locations (Claude Code's bash may
not share PATH with the interactive shell):

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && echo "$cli found at: $d/$cli" && break
  done
done
```

Found off-PATH: `export PATH="<dir>:$PATH"` for this session. Still missing,
below the floors (git < 2.38, gh < 2.0, python3 < 3.9, no gh-stack
extension), or `gh auth status` fails: read `references/installation-and-troubleshooting.md`
and stop. Never continue with degraded behavior.

## Step 2 — Status first, and after every write

`/sc-gh-stack-view` (skill `sc-gh-stack-view`, script
`.claude/scripts/gh_stack_view.py`) is THE status call. Run it before any
`gh stack` write command, after every link, unstack, rebase or merge, and
before dispatching anyone to a layer. Paste its output verbatim. Never fan out
`gh pr view` per branch, never text-parse `gh pr checks`, never use bare
`gh stack view` (it opens a TUI; the script uses `--json`).

## The model (read `references/model.md` once)

- **Trunk** is the branch the stack lands on: `develop`, an integration branch
  such as `integrate/phase-N`, or whatever the user names. Never assume the
  repository default branch.
- **Append-only and linear.** Every unit of work is a new worktree cut from the
  current pushed top. A layer is **frozen** the moment its task closes; nothing
  below the top is edited again. Findings on layer K are fixed on a new layer
  above the top, never on K.
- **One writer per branch, one stack writer.** Only the stack writer (the lead
  or orchestrator) runs `link`, `unstack`, `sync`, `rebase`, `merge`. Everyone
  else pushes commits to their own layer only.
- **QA and CI gate the top only.** Red on a lower layer is informational unless
  that layer is to be merged alone.
- **Small fixes do not get a stack.** One owner, well under a few hundred
  lines, fix and tests together: one PR off trunk, no stack.

## What to do (pick the row, open the reference)

| Situation | Reference |
|-----------|-----------|
| Starting a new sprint, fix round, docs or evidence layer | `references/recipe-cut-layer.md` |
| First push of a layer landed; it needs a PR and a stack link | `references/recipe-link.md` |
| Several open PRs on one trunk depend on each other | `references/recipe-link.md` (full ordered link) |
| Fixing a finding on a frozen layer, or on any layer that has children | `references/recipe-cut-layer.md` (new layer on top; never edit below the top) |
| Starting a task on the live top layer (no children, not frozen) | `references/workflow.md` step 4 (rebase at task start) |
| Insert a layer mid-stack, remove a red layer whose fix is above, collapse a passing bottom | `references/recipe-restack.md` |
| Everything frozen, top green and QA PASS: land it | `references/recipe-land.md` |
| `gh stack merge` refused, `gh pr merge` refused, non-linear stack | `references/recipe-land.md` (fallbacks A and B) |
| View shows 🔄, or NOT COHERENT with `-` rows after an unstack | `references/recipe-stale-tracking.md` |
| Deciding layer boundaries, naming, what belongs where | `references/stack-design.md` |
| Any `gh stack` command, flag, exit code, `--json` schema | `references/commands.md` |
| An error message you do not recognise | `references/troubleshooting.md` |
| How a whole phase runs on one stack (worked example) | `references/phase-model-example.md` |

Every recipe ends the same way: run `/sc-gh-stack-view`, paste it, and record
the current stack number (each unstack mints a new one).

## Hard preconditions (details and incidents in `references/preconditions.md`)

1. Creating or re-creating a stack is ONE `gh stack link --base <trunk>
   <bottom-pr#> ... <top-pr#>`: the full ordered list, from a worktree on a
   stack branch. Without `--base` the bottom PR is retargeted to the default
   branch and locked there. Appending one PR to an existing stack may use
   `gh stack link <stack#> <pr#>`, which appends on top only and cannot
   insert. Either way, verify every base with `/sc-gh-stack-view` afterwards.
2. Cut a new layer only from a **pushed** head that contains every lower
   layer's head (`git merge-base --is-ancestor`). Two layers cut from the same
   head must declare at cut time which one merges the other forward.
3. Never rewrite a layer that has children. Never rebase a frozen layer to
   "catch up" with trunk. Never force-push under a live agent.
4. Freeze the trunk from the final sync until the landing is confirmed:
   explicit FREEZE to every trunk writer, acked. One stray push restarts every
   layer's CI.
5. Never merge a red layer, and never merge a red bottom layer alone when its
   fix lives above (that puts the red on the trunk). Remove the red layer from
   the stack so the fixing layer above carries its commits
   (`recipe-restack.md`, section 2).
6. Before any scoped `gh stack merge <pr>`, read the full `branches[]` from
   `gh stack view --json`; an upper empty draft gets swept in and its branch
   deleted.
7. Land with `gh stack merge <stack#> --yes --merge` (merge commits only, by
   stack number so stale local tracking cannot pick the wrong stack). Never
   `--squash`.
8. Mergeability is `git merge-tree --write-tree A B` (exit code) or a real
   `git merge --no-commit` in a scratch worktree. Never the legacy 3-arg
   `merge-tree`; it prints diff3 hunks on clean merges.
9. Every push to a PR head restarts its CI. No cosmetic or metadata pushes to
   a green or running head; batch follow-ups into one validated push.
10. Landing, closing PRs and unstacking are outward-facing. Confirm with the
    user before `gh stack merge`, `gh pr close` or `gh stack unstack` unless the
    user already directed that exact action.

## Deterministic helpers

| Script (installed under `.claude/scripts/`) | Purpose | Mutates |
|---|---|---|
| `gh_stack_view.py` | Coherence, mergeability, CI and LANDING table for every open stack | no |
| `gh_stack_chain_check.py --trunk <trunk> <bottom> ... <top>` | Pre-link check: every head pushed, linear ancestry, PR bases as expected, top merges clean into trunk | no |

If `CLAUDE_PLUGIN_ROOT` is set (plugin install), the scripts are at
`$CLAUDE_PLUGIN_ROOT/scripts/`. Otherwise, if a script is not at
`.claude/scripts/`, locate it with `find .claude ~/.claude -name 'gh_stack_*.py'`
and use the newest match. Never reproduce the checks by hand.

## Storage

No state under `.claude/` or `.sc/`. The skill runs `git`, `gh` and `gh stack`
in the target repository and its worktrees. Stack tracking is gh-stack's own,
per worktree (`recipe-stale-tracking.md` explains the consequence).

## Related

- `../sc-gh-stack-view/SKILL.md` — the status tool this skill depends on.
- `sc-git-worktree` (if installed) creates the layer worktrees; the recipes
  show the plain `git worktree add` equivalent.
