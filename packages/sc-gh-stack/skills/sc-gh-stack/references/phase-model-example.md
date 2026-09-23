# Worked example: a phase as one append-only stack

Read this to see every rule applied end to end. The example is the model the
rules were learned in: a multi-sprint phase of a Rust workspace, one lead
agent as stack writer, several dev agents, a QA agent, an integration branch
as trunk. Names and numbers are real (phase-bc, 2026-09-20 to 2026-09-23).
Repository-specific tooling is named where it appears so you can substitute
your own.

## Setup

- Trunk: `integrate/phase-bc`, cut from `develop`. Sprint work never targets
  `develop` or `main` directly; the phase closes with one PR
  `integrate/phase-bc → develop`.
- Roles: the lead owns every `gh stack` write and every PR open. Each sprint
  has one dev with one worktree and one branch. A QA agent reviews the top
  only.
- Local gates run before every accepted push (format, clippy with warnings as
  errors, workspace tests, line-count and boundary lints). They are the CI,
  locally; CI itself is a merge gate, never a dispatch gate.
- Merge commits only (repository rule).

## The plan is cut by layer

Sprints were cut on crate boundaries: `bc.1` storage, `bc.2` typed
observability (runtime), `bc.3` CLI, `bc.4` release tooling, `bc.6` docs.
Each sprint's file list was disjoint from every other's. The earlier phase
that used vertical slices (every crate in every sprint) was cancelled after
five hours with ten layers and three fix rounds per sprint.

## Cutting and linking

1. `bc.1` worktree cut from `origin/integrate/phase-bc`. First push within
   minutes; the lead opened PR #1547 (base `integrate/phase-bc`, body with the
   parent SHA and the fence). A stack needs two PRs, so the first
   `gh stack link --base integrate/phase-bc 1547 <second-pr>` ran the moment
   the second layer's PR opened.
2. As soon as `bc.1`'s types and core paths were pushed ("could `bc.2`
   compile against this head?"), the `bc.2` worktree was cut from
   `origin/feature/bc1-...` and its dev deployed. `bc.1` continued its QA and
   fix rounds on layers above.
3. Every QA finding became a fix layer at the top (`fix/bc2-review-N`), PR on
   first push, appended with `gh stack link <stack#> <pr#>`. The stack reached
   20 PRs: 1547 → … → 1565 (sprints plus 13 review-fix layers), then
   1566 → 1567 → 1568 (`bc.4`).
4. The lead ran `/sc-gh-stack-view --trunk integrate/phase-bc` after every link
   and before every dispatch; devs never ran a stack write.

## Rebase at task start

When a dev started a fix task on their sprint layer (a live layer with no
children, never a frozen one), the first step was:

```bash
git fetch origin
git rebase --onto origin/<parent> <recorded-parent-base> <layer>
git push --force-with-lease
```

The lead recorded the new parent SHA in the ledger. No other rebases happened
between tasks. Frozen intermediate layers were not rebased at all.

## QA on the top, pinned

The phase-end review was dispatched once, on PR #1568 at `5c53dff79` with all
checks green, with the pinned head and the base ref
(`git merge-base integrate/phase-bc 5c53dff79`) in the task variables. The
reviewer read every file with `git show 5c53dff79:<path>`. Seventeen
per-layer background QA rounds run earlier were history, not the gate.

The verdict was FAIL with seven blocking findings. Each was verified before
dispatch (one was pre-existing on `develop`, one was false), then fixed on new
layers above #1568: a docs layer by one dev, artifact layers by another.
Nothing below the top was touched.

## Removing red layers whose fix lived above

Four layers (#1555, #1556, #1566, #1567) were red for defects fixed on the
layers above them. Instead of waiting for the stack merge to serialise behind
them:

```bash
gh stack unstack 1564
gh stack link --base integrate/phase-bc <every green PR, bottom to top>   # 17 PRs
gh pr close 1555 --comment "Carried by #1557; branch kept."               # and 1556, 1566, 1567
```

Result: stack #1564 became #1570, 17 layers, #1557 rebased by GitHub onto
`feature/bc2-typed-observability`, #1568 onto `fix/bc2-review-7`, all green in
one CI pass. Base changes did not restart CI on unchanged heads. Then the
stale-tracking cleanup in every other worktree, then the view tool.

## Merge-forward as a head-of-queue task

Where a sibling had to merge another forward, the instruction was sent as a
task with a stable id, re-assigned with the updated head as siblings landed
(`atm task assign <dev> --task-id MERGE-<layer> --head` in that repository's
team tooling): it cannot be missed or crossed, it is ordered in the task list,
and `--head` does not pre-empt the active task, so it runs right after the
layer task closes.

## Landing

Checklist from `recipe-land.md`: every lower layer frozen with its SHA in the
ledger; top gates green and QA PASS on the PR; FREEZE sent to the two trunk
writers (the lead and the QA agent, both of which push triage records to the
trunk) and acked; then `gh stack merge 1570 --yes --merge`. After landing:
view tool, check that no in-flight PR was closed, "landed" sent, freeze
lifted, phase PR `integrate/phase-bc → develop` opened. Integration tests that
need the landed tree run on `develop`, not on the stack.

## What it cost when a rule was skipped (same repository, earlier phases)

| Skipped | Cost |
|---------|------|
| One event-log push to the trunk one minute after the final sync | Async-merge fallback, CI restarted on every layer, 40 to 60 minutes |
| Two layers cut from the same top with no declared order | Missing files upstack, false conflicts, an afternoon |
| A lower layer rewritten after children branched | `gh stack merge` refused; landed via fallback B |
| Bottom layer merged alone with its red fixed above | `develop` red; an unrelated PR held its push |
| Scoped merge without reading `branches[]` | An upper draft merged and its branch deleted |
| `gh stack link` without `--base` | Bottom PR retargeted to `main` and locked |
| Per-branch fix rounds and waiting on lower-layer QA | Two to three hours per sprint |
| Sprints as vertical slices | Phase cancelled at 10 layers |
