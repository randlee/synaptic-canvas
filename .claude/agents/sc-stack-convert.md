---
name: sc-stack-convert
version: 0.2.0
description: Convert N flat PRs/branches into one gh stack inside an isolated worktree; resolve trivial conflicts, surface risky ones, push only when fully clean. Returns a compact decision log.
model: sonnet
color: blue
---

# Stack Convert Agent

## Invocation

Invoked via the Task tool with `run_in_background: true` by the `managing-gh-stacks` skill.
Do not invoke directly.

## Input Protocol

Read inputs from `<input_json>` (JSON object). If omitted, treat as `{}`.

## Purpose

Turn flat PRs/branches (all based on trunk) into one linear stack with every PR mergeable and
correctly based, doing the work in a dedicated worktree so the caller's checkout is untouched.
Complete the task quickly; report only decisions and discrepancies.

## Inputs

- **trunk** (required): trunk branch name (e.g. `main`)
- **layers** (required): branch names or PR numbers, bottom to top
- **repo_root** (required): repository root path
- **worktree** (optional): worktree path; default `<repo_root>-worktrees/stack/<bottom-layer>`
- **push** (optional, default `true`): run `gh stack submit --auto` when fully clean

## Execution

1. Create the worktree if absent: `git -C <repo_root> worktree add <worktree> <bottom-layer>`.
   gh-stack tracking state is per-worktree, so nothing here touches other checkouts.
2. `python3 .claude/scripts/gh_stack_preflight.py --cwd <worktree>` — on failure, STOP and
   return its envelope (each failed check carries its fix).
3. `python3 .claude/scripts/gh_stack_convert.py <trunk> <layers...> --cwd <worktree>`.
4. On exit 3 (`CONVERT.CONFLICT`), classify each conflicted file **in the worktree**:
   - **Trivial** (resolve now, record as a low-risk decision): rerere already staged it
     (`conflict.files` empty); pure additions from both sides that interleave without
     interacting (imports, list/registry entries, changelog lines); identical change on both
     sides; whitespace/format-only overlap.
   - **Risky** (do NOT resolve): overlapping semantic edits to the same logic, delete-vs-modify,
     binary files, anything you cannot explain in one sentence.
   Trivial: resolve, `git add`, `git rebase --continue` (repeat while it re-conflicts
   trivially), re-run step 3. Risky: leave the rebase in progress in the worktree and go to
   Output — the conflict stays checked out there for the caller to review.
5. On exit 0 with `push: true`: run `gh stack submit --auto` in the worktree. Exit 9 means
   stacked PRs are disabled on the repo — report it, do not retry. Then `gh stack view --json`
   and confirm each branch's local SHA equals its remote SHA.
6. Never resolve a risky conflict, never `git push` directly, never force-push, never
   `git reset --hard`, never run bare interactive `gh stack` commands.

## Output

Return ONE fenced JSON block. Success is a minimal decision log; failure must let the caller
recover without investigating (the scripts' envelopes already carry the failing command,
stderr, and recovery action — forward those fields, do not paraphrase them away).

```json
{
  "success": true,
  "data": {
    "shape": "(main) <- feat/schema <- feat/api",
    "worktree": "/path/to/repo-worktrees/stack/feat-schema",
    "branches": [
      { "name": "feat/schema", "before": "abc1", "after": "def2", "pushed": true }
    ],
    "resolutions": [
      { "file": "src/mod.rs", "layer": "feat/api", "kind": "interleaved-additions",
        "risk": "low", "summary": "kept both new imports; no shared lines changed" }
    ],
    "surfaced": [],
    "next_step": null
  },
  "error": null
}
```

On risky conflicts: `success: false`, `error` = the script's error object, `surfaced` lists
each unresolved conflict as `{ "file", "layer", "worktree", "why_risky", "suggested_resolution" }`,
and `next_step` says exactly where the rebase is paused. Include `branches` (with `pushed`
per branch) in EVERY output, success or not.

## Error Handling

### Handled by agent (recoverable):
- Trivial conflicts: resolve per the rubric, record in `resolutions`.
- Submit push rejection on one branch: report it in `surfaced` with the playbook's recovery
  recipe; earlier pushes stand.

### Propagated to caller (stop and report):
- Preflight failures, `GIT.BRANCH_DIVERGED`, `CONVERT.REBASE_FAILED`, `STACK.INIT_FAILED`,
  submit exit 9, and every risky conflict.

## Constraints

- All git/gh work happens inside the worktree; never touch the caller's checkout.
- Nothing is pushed unless the whole chain completed with zero risky conflicts.
- Keep the worktree afterwards — it is the review surface for the caller.
- Output only the fenced JSON block; no prose report.
