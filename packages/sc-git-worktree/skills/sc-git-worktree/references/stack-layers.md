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

`data.stack_handoff` is for the agent that will work in the worktree. Paste it
into that agent's prompt unchanged. Its `commands[]` are ordered; angle-bracket
placeholders are filled from `gh pr create` output and `/sc-gh-stack-view`.

## Writer contract (what the handoff says)

1. You are the only writer of the layer. Never edit, rebase or force-push any layer below it.
2. Push a WIP commit within minutes: `git push -u origin <layer>`. Then open the PR with `--base <parent>` (never the trunk unless the parent *is* the trunk). The PR body records `Parent: <parent> @ <parent_sha>`.
3. Stack on the first push, never "once it is green": `gh stack link <stack#> <pr#>` to append, or the full `gh stack link --base <trunk> <ordered pr#s>`. PR numbers, not branch names.
4. Rebase at most once per task, at the start, only while the layer has no children: `git rebase --onto origin/<parent> <parent_sha> <layer>` then `git push --force-with-lease`; record the new parent SHA.
5. The next layer is cut from `origin/<layer>` once it is pushed, never from a local ref.

## Insert mid-stack (`position: insert`)

`gh stack link` cannot insert. The handoff adds, in order:

1. Push and open the PR with base `<parent>` as above.
2. The writer of `<above>` carries the new layer forward with **one** merge commit (`git merge --no-ff origin/<layer>`), never a rebase; otherwise the stack is non-linear and cannot land.
3. `gh stack unstack <stack#>` (PRs and branches untouched; confirm with the user, it is outward-facing).
4. `gh pr edit <pr# of above> --base <layer>`.
5. Chain check (`gh_stack_chain_check.py`, present when `sc-gh-stack` is installed), then the full `gh stack link --base <trunk> ...` with the new layer in place.
6. Every other stack worktree: `gh stack unstack --local && gh stack checkout <new stack#>`; then `/sc-gh-stack-view`.

## What the other operations do with layers

- **Cleanup / abort**: a branch with live child layers in tracking (child has a worktree or a remote branch) is never deleted unless git shows the branch merged into the trunk. Error `STACK.HAS_CHILDREN` names the children; batch cleanup lists them under `stack_blocked`. A landed parent is safe to delete: GitHub retargets the children onto the trunk.
- **Scan**: layer rows carry `tracking_entry.stack` and may report `stack_parent_advanced: origin/<parent> <old> -> <new>` (the writer's one rebase applies) or `stack_parent_landed` (the PR should now target the trunk; confirm with `/sc-gh-stack-view`). The trunk moving under a bottom layer is not reported; it is expected.
- **Update**: unchanged; trunks are protected branches and are updated with `--update`.

## Not done here

Pushing, opening PRs, linking, unstacking and merging are the writer's and the
stack writer's jobs, in the worktree, with `sc-gh-stack`. This skill never runs
`gh`.
