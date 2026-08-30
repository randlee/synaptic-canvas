# Playbook: cleanly rebase a stack after trunk moves or a mid-stack fix

**Situation.** A stack `(main) <- L1 <- L2 <- L3 <- L4` needs rebasing because trunk advanced,
a layer was squash-merged, or a fix just landed in a middle layer (review changes committed on
L2). The goal state: every layer linear on the one below, every branch pushed, every PR
mergeable, no conflict resolved twice.

**Mid-stack fix rule first** (hard rule 4): the fix is committed on the layer that owns the
concern — check out L2 in the stack's worktree, commit there, never on L4. Then sync.

## Route A — delegate to `sc-stack-sync` (default)

```json
{ "worktree": "/path/repo-worktrees/stack/L1", "fix_branch": "L2" }
```

(The worktree path uses the SKILL.md slug rule — `/` becomes `-`, no case folding.)

The agent runs `gh_stack_sync.py` (which wraps `gh stack sync`: fetch → reconcile with GitHub
→ fast-forward trunk → cascade rebase → atomic push). Merged and squash-merged layers are
detected automatically, so a merged L1 does not produce spurious conflicts. With
`fix_branch`, the agent verifies every layer above L2 now contains L2's tip.

Expected report on success — a minimal decision log:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "branches": [
      { "name": "L2", "before": "abc1", "after": "def2", "pushed": true },
      { "name": "L3", "before": "1122", "after": "3344", "pushed": true },
      { "name": "L4", "before": "5566", "after": "7788", "pushed": true }
    ],
    "resolutions": [],
    "surfaced": [],
    "next_step": null
  },
  "error": null,
  "metadata": { "duration_ms": 32000, "tool_calls": 9, "retry_count": 0 }
}
```

A risky-conflict stop comes back as `canceled: true, aborted_by: "policy"` with error code
`SYNC.CONFLICT_RISKY` — a deliberate hold for review, not a failed sync.

On conflict, `gh stack sync` restores **every branch** to its pre-sync state (all-or-nothing;
exit 3), so a failed sync never leaves the stack half-rebased. The agent then drives
`gh stack rebase` and applies the conflict rubric from SKILL.md: trivial conflicts are
resolved and reported in `resolutions` (file, layer, kind, one-sentence summary); a risky
conflict stops the agent, leaving the rebase paused in the worktree — `surfaced` names the
file, layer, worktree path, why it is risky, and a suggested resolution. Resolve it there,
`git add`, `gh stack rebase --continue`, then re-invoke the agent (or re-run the script) to
finish and push.

## Route B — manual (fallback; also what the agent does under the hood)

```bash
python3 .claude/scripts/gh_stack_sync.py --cwd <worktree>    # exit 0 = synced and pushed
```

- Exit 3, `SYNC.CONFLICT`: all branches restored. `gh stack rebase` in the worktree, resolve +
  `git add` + `gh stack rebase --continue` until it finishes (rerere replays every previously
  recorded resolution — the same conflict is never resolved twice), re-run the script.
- Exit 5, `SYNC.ABORTED`: local and remote stacks diverged, so `gh stack sync` deliberately
  did nothing (upstream prints "Sync aborted" but exits 0 — the script converts that to a
  real failure so exit 0 always means synced). Nothing was fetched, rebased, or pushed. The
  caller chooses keep-remote (`gh stack unstack --local`, then `gh stack checkout <n>`) or
  keep-local — see `references/troubleshooting.md`, "Local and remote stacks have diverged".
- Exit 5, `SYNC.NO_STACK`: gh-stack tracking is per-worktree. For a stack that exists on
  GitHub, create a worktree on the bottom branch and run `gh stack checkout <bottom>` there —
  it pulls the stack down and sets up local tracking. For a local-only stack (never
  submitted), tracking lives in the checkout that created it: run there, or re-adopt with
  `gh stack init --base <trunk> <layers...>` in the new worktree.
- Any other failure: the envelope carries the failing command, stderr, per-branch state, and
  the recovery action — act on `error.suggested_action`, then re-run.

Verify the goal state: `gh stack view --json` shows every branch `needsRebase: false`, and the
report shows `pushed: true` for every branch.
