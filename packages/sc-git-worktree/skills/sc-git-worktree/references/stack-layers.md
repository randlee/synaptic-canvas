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
  - Append on top: the current top from `/sc-gh-stack-view`.
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
filled from `gh pr create` output and `/sc-gh-stack-view`.

## Writer contract (`stack_handoff.writer`)

1. You are the only writer of the layer. Never edit, rebase or force-push any layer below it.
2. Make a WIP commit within minutes and push it: `git push -u origin <layer>`. A PR needs at least one commit. The stack writer opens the PR with `--base <parent>` (the trunk only when the parent *is* the trunk) and links it on that first push, never "once it is green".
3. Rebase at most once per task, at the start, only while the layer has no children: `git rebase --onto origin/<parent> <parent_sha> <layer>` then `git push --force-with-lease`. Between tasks the layer does not move.
4. Never run gh stack write commands (link, unstack, sync, rebase, merge) or open PRs from the worktree; report to the stack writer.
5. The next layer is cut from `origin/<layer>` once it is pushed, never from a local ref.

## Stack writer sequence (`stack_writer` block)

Append on top (`position: top`; the parent must be the top row of `/sc-gh-stack-view`, otherwise the create refuses with `STACK.PARENT_HAS_CHILD`):

1. After the writer's first push: `gh pr create --base <parent> --head <layer>` with the body `Parent: <parent> @ <parent_sha>` (quoted heredoc; the handoff renders it).
2. `cd <worktree> && gh stack checkout <stack#>` so the new worktree carries tracking before any write command; skip only when no stack exists yet.
3. Chain check when `sc-gh-stack` is installed, then `gh stack link <stack#> <pr#>` to append, or the full `gh stack link --base <trunk> <ordered pr#s>`. PR numbers, not branch names.
4. `/sc-gh-stack-view`.

Insert mid-stack (`position: insert`; `gh stack link` cannot insert):

1. PR with base `<parent>` and `gh stack checkout` as above.
2. **Every** layer above the insertion point, bottom to top, carries the layer below it forward with one merge commit each (`git merge --no-ff origin/<layer-below>` then push), starting with the writer of `<above>` merging the new layer. Never a rebase, never a force-push; otherwise some layer stops containing its parent and the stack cannot land.
3. `gh stack unstack <stack#>` (PRs and branches untouched; confirm with the user, it is outward-facing).
4. `gh pr edit <pr# of above> --base <layer>`.
5. Chain check, then the full `gh stack link --base <trunk> ...` with the new layer in place.
6. Every other stack worktree: `gh stack unstack --local && gh stack checkout <new stack#>`; then `/sc-gh-stack-view`.

## What the other operations do with layers

- **Cleanup**: a branch with live child layers (layers cut from it, or the layer it was inserted under; live = worktree directory or remote branch exists) is deleted only when git shows it landed with a merge commit into the children's trunk (`origin/<trunk>`). Error `STACK.HAS_CHILDREN` names the children; batch cleanup lists them under `stack_blocked`, together with fresh layers that have no commits yet (never swept). A landed parent is safe to delete: GitHub retargets the children onto the trunk. A fast-forward landing is indistinguishable from an empty branch and fails closed.
- **Abort**: with `allow_delete_branch`, a branch with live children is always refused (`STACK.HAS_CHILDREN`); a landed parent is cleaned with `--cleanup`, not aborted.
- Both guards read the tracking file: with `tracking_enabled: false` they are off. If a child is already gone but still listed, run `--list` to reconcile.
- **Scan**: layer rows carry `tracking_entry.stack` and may report `stack_parent_advanced` (the layer no longer contains the parent's pushed head; the writer's one rebase or a merge-forward clears it) or `stack_parent_landed` (the PR should now target the trunk; confirm with `/sc-gh-stack-view`, diff before any reset, never force-push over GitHub's retarget). The trunk moving under a bottom layer is not reported; it is expected.
- **Update**: unchanged; trunks are protected branches and are updated with `--update`.

## Not done here

Pushing, opening PRs, linking, unstacking and merging are the writer's and the
stack writer's jobs, in the worktree, with `sc-gh-stack`. This skill never runs
`gh`.
