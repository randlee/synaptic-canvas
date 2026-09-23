# Recipe: cut a new layer from the top of the stack

Use for every unit of work on a stack: a sprint, a fix round, a cleanup, a
docs or evidence layer. The layer is a new worktree cut from the current
**pushed** top. Nothing below the top is edited again.

## Inputs

- `<trunk>`: the stack's trunk (for example `develop`, `integrate/phase-bc`).
- `<top>`: the current top branch, from `/sc-gh-stack-view` (the last open
  row). For the first layer of a new stack, `<top>` is the trunk.
- `<layer>`: the new branch name. Follow the repository's naming policy;
  names are used verbatim by gh-stack.

## Steps

1. Status: `/sc-gh-stack-view`. Note the top branch and its origin SHA.

2. Verify the top is pushed and contains every lower layer:

   ```bash
   git fetch origin
   git rev-parse --verify origin/<top>
   for lower in <every open layer below top>; do
     git merge-base --is-ancestor origin/$lower origin/<top> && echo "ok $lower" || echo "MISSING $lower"
   done
   ```

   A `MISSING` line means the top is not the top; stop and fix the chain
   first (`recipe-restack.md`). A fork is never cut from a head that does not
   contain everything below it.

3. Create the worktree from the pushed head, never from a local ref:

   ```bash
   git worktree add --no-track ../<repo>-worktrees/<layer> -b <layer> origin/<top>
   ```

   `--no-track` matters: without it the new branch's upstream is
   `origin/<top>`, and the first `git push` or a later
   `push --force-with-lease` targets the parent branch. The first push is
   `git push -u origin <layer>`.

   With `sc-git-worktree` installed: `/sc-git-worktree --create <layer> <top>`
   after refreshing the local `<top>` ref
   (`git fetch origin <top> && git update-ref refs/heads/<top> origin/<top>`),
   because that skill branches from the local ref.

4. Record the parent SHA the layer was cut from
   (`git rev-parse origin/<top>`). It goes in the PR body and any ledger; QA
   diffs against it, and the rebase-at-task-start uses it as
   `<recorded-parent-base>`.

5. Hand the worktree to its single writer. The writer pushes a WIP commit
   within minutes; there is no reason to wait.

6. On that first push: `recipe-link.md` (PR with base = `<top>`, then link).

## Two layers from the same head

Sometimes two units of work are ready at once (a fix round and the next
sprint). Declare at cut time which one merges the other forward, and cut the
second only from the first's pushed head as soon as it exists. If both must
start now from the same head, the declared follower does one plain merge
commit (never a rebase, never a force-push) of the leader before linking, so
the chain is linear. Push the WIP first; the merge-forward is a later
appended commit.

## Finish

`/sc-gh-stack-view` after the link. Record the stack number if the link
printed a new one.
