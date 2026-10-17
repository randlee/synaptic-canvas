# Stack layers: what the worktree skill guarantees and what the writer must do

Read this when a worktree is a gh-stack layer. The stack model itself (append-only
linear stack, frozen layers, one writer per branch, one stack writer) is documented
in the `sc-gh-stack` package; this file covers only the worktree side.

## Why a layer needs its own create path

| Plain `--create <branch> <base>` | `--create-stacked <branch> <parent> <trunk>` |
|---|---|
| Branches from the **local** `<base>` ref when one exists | Always cuts from `origin/<parent>` after a fetch |
| Local ref may be stale or another writer's unpushed state | The pushed head is the only truth for a stack |
| No record of where the branch started | Records `parent_sha` in tracking and in the handoff |
| No check that `<base>` is a valid parent | Refuses: parent not pushed, parent already landed, parent off the trunk, bad insert target, branch already exists |
| Any remote-ref base is created with `--no-track` (fixed in 0.14.0) | Same; the layer never has the parent as upstream |

All refusals happen before any worktree or branch is created and return a
`suggested_action`.

## Inputs

- `branch`: new layer name. Must not exist locally or on origin.
- `parent` (`base` in JSON): the branch to cut from.
  - Append on top: the current pushed top from sufficient complete ordered composition, not the last displayed summary row. Reuse verified evidence; acquire a scoped `/sc-gh-stack-view --stack <known-stack#> --refresh` only when that remote composition is missing. A branch selector requires a known qualified local catalog containing the stack number; a newly linked worktree may have none.
  - Bottom of a new stack: the trunk itself.
  - Insert: the layer *below* the insertion point, plus `--above <layer>` naming the layer currently stacked on it.
- `trunk` (`stack.trunk`): the branch the stack's bottom PR targets.
- `purpose`, `owner`: the writer's task id and handle.

## Output the caller must forward

`data.stack` is stored in the tracking row:

```json
{"trunk": "develop", "parent": "sprint-6", "parent_sha": "<40-char sha>", "above": null, "position": "top"}
```

`data.stack_handoff` has two role blocks. Paste `writer` into the prompt of the
agent that will work in the worktree and `stack_writer` into the stack writer's
prompt (the one agent that opens PRs and runs gh stack write commands; layer
writers never do). `commands[]` are ordered; angle-bracket placeholders are
filled from `gh pr create` output and sufficient scoped composition evidence.

## Writer contract (`stack_handoff.writer`)

1. You are the only writer of the layer. Never edit, rebase or force-push any layer below it.
2. Make a WIP commit within minutes and push it: `git push -u origin <layer>`. A PR needs at least one commit. The stack writer opens the PR with `--base <parent>` (the trunk only when the parent *is* the trunk) and links it on that first push, never "once it is green".
3. Rebase at most once per task, at the start, only while the layer has no children: `git rebase --onto origin/<parent> <parent_sha> <layer>` then `git push --force-with-lease`. Between tasks the layer does not move.
4. Never run gh stack write commands (link, unstack, sync, rebase, merge) or open PRs from the worktree; report to the stack writer.
5. The next layer is cut from `origin/<layer>` once it is pushed, never from a local ref.

## Stack writer sequence (`stack_writer` block)

Append on top (`position: top`; complete ordered composition must establish the current pushed top, not summary row order; tracked live children cause `STACK.PARENT_HAS_CHILD`):

1. After the writer's first push: `gh pr create --base <parent> --head <layer>` with the body `Parent: <parent> @ <parent_sha>` (quoted heredoc; the handoff renders it).
2. Reuse sufficient exact-head and complete composition evidence. Explicit-number link/full link does not require importing tracking into each new worktree; import only when a later operation actually depends on that worktree's local tracking.
3. Chain check when `sc-gh-stack` is installed, then choose **one** form: `gh stack link <stack#> <pr#>` to append, or the full `gh stack link --base <trunk> <ordered pr#s>`. PR numbers, not branch names.
4. Record the returned numeric stack number from link (a relink mints a new number). Reconcile affected bases/heads from the mutation response. Only if complete composition/base evidence remains missing, use one scoped `/sc-gh-stack-view --stack <returned-stack#> --refresh`; no unconditional finish view. Do not substitute the new branch unless a qualified local catalog already records its stack number.

Insert mid-stack (`position: insert`; `gh stack link` cannot insert):

1. PR with base `<parent>` and sufficient scoped composition evidence as above.
2. **Every** layer above the insertion point, bottom to top, carries the layer below it forward with one merge commit each (`git merge --no-ff origin/<layer-below>` then push), starting with the writer of `<above>` merging the new layer. Never a rebase, never a force-push; otherwise some layer stops containing its parent and the stack cannot land.
3. `gh stack unstack <stack#>` (PRs and branches untouched; confirm with the user, it is outward-facing).
4. `gh pr edit <pr# of above> --base <layer>`.
5. Chain check, then the full `gh stack link --base <trunk> ...` with the new layer in place.
6. Record the new numeric stack number returned by link; reconcile affected facts from the unstack/link responses. Only if complete composition/base evidence remains missing, use `/sc-gh-stack-view --stack <returned-stack#> --refresh`. Inspect common/legacy catalogs locally, clear only proven-stale tracking, and import the new stack once in the worktree needing local tracking. Use `sc-gh-stack`'s `recipe-stale-tracking.md`; never fan out checkout/status across all worktrees.

## What the other operations do with layers

- **Cleanup**: a branch with live child layers (layers cut from it, or the layer it was inserted under; live = worktree directory or remote branch exists) is deleted only when git shows it landed with a merge commit into the children's trunk (`origin/<trunk>`). Error `STACK.HAS_CHILDREN` names the children; batch cleanup lists them under `stack_blocked`, together with fresh layers that have no commits yet (never swept). A landed parent is safe to delete: GitHub retargets the children onto the trunk. A fast-forward landing is indistinguishable from an empty branch and fails closed.
- **Abort**: with `allow_delete_branch`, a branch with live children is always refused (`STACK.HAS_CHILDREN`); a landed parent is cleaned with `--cleanup`, not aborted.
- Both guards read the tracking file: with `tracking_enabled: false` they are off. If a child is already gone but still listed, run `--list` to reconcile.
- **Scan**: layer rows carry `tracking_entry.stack` and may report `stack_parent_advanced` (the layer no longer contains the parent's pushed head; the writer's one rebase or a merge-forward clears it) or `stack_parent_landed` (the PR should now target the trunk; reuse sufficient lifecycle/base evidence or fill missing facts with `/sc-gh-stack-view --stack <layer>`, diff before any reset, never force-push over GitHub's retarget). The trunk moving under a bottom layer is not reported; it is expected.
- **Update**: unchanged; trunks are protected branches and are updated with `--update`.

## Not done here

Pushing, opening PRs, linking, unstacking and merging are the writer's and the
stack writer's jobs, in the worktree, with `sc-gh-stack`. This skill never runs
`gh`.
