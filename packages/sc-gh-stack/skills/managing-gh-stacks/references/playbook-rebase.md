# Playbook: rebasing a stack (`gh stack rebase`)

Use when `gh stack view --json` shows `needsRebase: true` on any layer, when GitHub or a PR
page reports the branch needs a rebase/update, or when `sync` exited 3 and left a conflict
to drive.

## Rule zero: believe the report

`needsRebase` is computed against the **remote and parent** state, not your checkout. Local
inspection — `git log`, a local `git merge-base --is-ancestor`, "the diff looks fine" — can
look perfectly clean while the parent moved, because your local refs are stale or the drift
is in a layer you are not looking at. Field incident: gh reported a rebase necessary; the
agent inspected locally, saw nothing, and **denied the rebase existed** — the stack's bottom
layer was ahead of the layers above it, and a conflict-free cascade rebase had to be run
manually.

Never deny a reported rebase. The check is:

```bash
git fetch
gh stack view --json     # which layers say "needsRebase": true?
```

If `view --json` says a layer needs a rebase, it does — proceed below. Only after fetch +
`view --json` shows `needsRebase: false` everywhere may you report "no rebase needed".

## Diagnose which case you are in

| Signal | Cause | Route |
|---|---|---|
| Trunk moved (new commits on `origin/<trunk>`) | normal drift / unrelated merges | `gh stack sync` — full loop incl. push (`playbook-sync.md`) |
| A **lower layer is ahead** of the layers above it (commits landed on the bottom/middle branch; upper layers don't contain its tip) | fix committed to a lower layer; or bottom advanced by a merge/ff | check out that layer, then `gh stack rebase --upstack` |
| A layer's PR merged | landed mid-stack | `gh stack sync` — merged PRs are replayed with `--onto` automatically, no spurious conflicts |
| Local and remote of one branch diverged | history rewritten somewhere | STOP — do not rebase over it; see `troubleshooting.md` |
| A branch ABOVE the stack's base (e.g. `main` above a `develop`-based stack) has commits the base lacks | release landed on the upper branch only | **not a rebase problem** — see "Merge-forward repositories" below |

## Merge-forward repositories

Before RUNNING or recommending any `gh stack rebase`/`sync` — diagnosis comes first,
never an exploratory sync "to see what happens" (it will conflict against foreign
history and, even though all branches restore, the attempt itself is the incident) —
check whether the drift is actually *above* the stack's base:

```bash
git fetch
git rev-list --count <base>..<upper>    # e.g. develop..main — nonzero means the upper
                                        # branch has commits the base lacks
```

In a merge-forward-only repository (upper branches merge down via PRs, never rebases),
that situation is fixed by **opening a merge-forward PR** (`<upper> -> <base>`) — never by
`gh stack rebase` or `gh stack sync`, which will conflict against history the base was
never meant to replay. Field incident: "the stack is out of date" was diagnosed as a
rebase, `gh stack rebase` conflicted, and the real cause (`main` carried a PR `develop`
lacked) was reachable with one `rev-list` before any rebase was suggested. Run the
`rev-list` check first; only when the drift is at or below the stack's own trunk is a
rebase the answer.

## The conflict-free case (most common)

"Rebase needed" usually does **not** mean conflicts. When a lower layer advanced, the layers
above just need a replay:

```bash
cd <stack-worktree>
gh stack checkout <layer-that-advanced>   # or: git switch <branch>
gh stack rebase --upstack                 # replays every layer above it
gh stack view --json                      # verify: all "needsRebase": false
```

Scope flags: `--upstack` = current branch → top (after editing a lower layer);
`--downstack` = trunk → current branch; `--no-trunk` = align stack branches with each other
only, no fetch/trunk rebase. Starting a rebase while one is in progress exits **7** — finish
or `--abort` the first one.

## If it conflicts

`--abort` restores **every** branch (never `git reset --hard`). Otherwise classify each
conflict with the SKILL.md rubric (trivial → resolve, `git add`,
`gh stack rebase --continue`; risky → leave the rebase paused in the worktree and surface
it). rerere replays previously recorded resolutions, so a re-run never re-asks.

## Verify the goal state

```bash
gh stack view --json   # every layer "needsRebase": false
```

Then push via `gh stack sync` or `gh stack submit --auto` — never `git push` directly.
