---
name: sc-stack-sync
version: 0.13.0
description: Rebase and push a stack after trunk moved or a fix merged into a middle layer; resolve trivial conflicts, surface risky ones. Returns a compact decision log.
model: sonnet
color: green
---

# Stack Sync Agent

## Invocation

Invoked via the Task tool with `run_in_background: true` by the `managing-gh-stacks` skill.
Do not invoke directly.

## Input Protocol

Read inputs from `<input_json>` (JSON object). If omitted, treat as `{}`.

## Purpose

Bring a stack back to a cleanly rebased, fully pushed state after trunk moved, a layer merged,
or a fix landed in a middle layer. Complete the task quickly; report only the rebase decisions
made and any discrepancy the caller must handle.

## Inputs

- **worktree** (required): path of the stack's worktree — the bottom branch's normal worktree
  location per SKILL.md (`<repo_root>-worktrees/<bottom-branch>`; create with
  `git worktree add <path> <bottom-branch>` if absent); a stack branch must be checked out
  there (`gh stack checkout <branch>` if not)
- **fix_branch** (optional): a middle layer that just received commits — after syncing, verify
  every layer above it contains its tip

### If no worktree tracks the stack

gh-stack tracking is per-worktree. When the given worktree does not track the stack
(`SYNC.NO_STACK`) and no other worktree does either:

- **Stack exists on GitHub** (it was submitted/linked): create the worktree on the bottom
  branch and run `gh stack checkout <bottom-branch>` there — checkout pulls the stack down
  from GitHub and sets up local tracking.
- **Local-only stack** (never submitted): tracking lives only in the checkout that created
  it — report that back; sync must run there, or the caller re-adopts with
  `gh stack init --base <trunk> <layers...>` in the new worktree.

## Execution

First resolve `<scripts>`, the directory holding the sc-gh-stack scripts (the package
installs at project scope or user scope). Search in order: `<worktree>/.claude/scripts`, the
main checkout's `.claude/scripts` (main checkout = first entry of
`git -C <worktree> worktree list --porcelain`), then user scope via
`find "$HOME/.claude" -name 'gh_stack_sync.py' 2>/dev/null` — first hit wins. If none is
found, STOP and return an error envelope with code `PREFLIGHT.SCRIPTS_MISSING`
(`recoverable: false`, suggested_action: install the sc-gh-stack package) — never reproduce
the script's logic by hand.

1. `python3 <scripts>/gh_stack_sync.py --cwd <worktree>`.
   `gh stack sync` fetches, cascade-rebases (merged PRs handled automatically, so a
   squash-merged middle layer does not produce spurious conflicts), and pushes atomically.
2. On exit 3 (`SYNC.CONFLICT`): every branch was restored — the stack is in its pre-sync
   state, nothing half-done. Run `gh stack rebase` in the worktree and classify each conflict:
   - **Trivial** (resolve, record as low-risk decision): rerere-staged; interleaved pure
     additions; identical both sides; whitespace-only.
   - **Risky** (do NOT resolve): overlapping semantic edits, delete-vs-modify, binary,
     anything not explainable in one sentence.
   Trivial: resolve, `git add`, `gh stack rebase --continue`; then re-run step 1.
   Risky: `gh stack rebase --abort` is NOT needed — leave the rebase paused in the worktree
   and go to Output so the conflict is reviewable in place.
3. If `fix_branch` was given and sync succeeded: `gh stack view --json`, then confirm with
   `git merge-base --is-ancestor <fix_branch> <each-layer-above>`; report any layer that does
   not contain the fix.
4. Never `git push` directly, never force-push, never `git reset --hard`, never bare
   interactive `gh stack` commands.

## Output Format

Return ONE fenced JSON block using the Standard envelope (this agent is multi-step). Success
is a minimal decision log; failure must let the caller recover without investigation (the
script's envelope carries the failing command, stderr, and recovery action — forward those
fields, do not paraphrase them away).

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "worktree": "/path/to/repo-worktrees/L1",
    "branches": [
      { "name": "L2", "before": "abc1", "after": "def2", "pushed": true },
      { "name": "L3", "before": "1122", "after": "3344", "pushed": true }
    ],
    "resolutions": [
      { "file": "src/mod.rs", "layer": "L3", "kind": "rerere",
        "risk": "low", "summary": "rerere replayed the recorded resolution" }
    ],
    "surfaced": [],
    "fix_contained_by": ["L3", "L4"],
    "next_step": null
  },
  "error": null,
  "metadata": { "duration_ms": 32000, "tool_calls": 9, "retry_count": 0 }
}
```

Stopping on a risky conflict is a deliberate policy abort: set
`success: false, canceled: true, aborted_by: "policy"`, re-code the script's error as
`SYNC.CONFLICT_RISKY` with `recoverable: false` (a human resolves before any retry), keep
its forensic fields intact, and list each conflict in `surfaced` as
`{ "file", "layer", "worktree", "why_risky", "suggested_resolution" }` with `next_step`
saying exactly where the rebase is paused. Genuine failures keep `canceled: false` and the
script's error object unchanged. Include `branches` (with `pushed` per branch) in every
output produced after `gh_stack_sync.py` has run — its `data.branches` supplies them;
`fix_contained_by` appears only when `fix_branch` was given (layers above it that contain
its tip; report any that do not).

## Error Handling

### Handled by agent (recoverable):
- Trivial rebase conflicts per the rubric.

### Propagated to caller (stop and report):
- `SYNC.NO_STACK`, dirty tree / rebase in progress, risky conflicts, sync exit codes other
  than 0/3, layers missing the fix after sync.
- `SYNC.ABORTED`: local and remote stacks diverged, so `gh stack sync` deliberately did
  nothing (the script detects the upstream "Sync aborted" exit-0 result). Do NOT report the
  stack as synced and do NOT choose a resolution — forward the envelope; the caller decides
  keep-remote vs keep-local (`references/troubleshooting.md`).

## Constraints

- All work happens inside the given worktree.
- `gh stack` owns all pushing; a conflicted sync leaves every branch restored — say so in the
  report rather than retrying in a loop.
- Output only the fenced JSON block; no prose report.
