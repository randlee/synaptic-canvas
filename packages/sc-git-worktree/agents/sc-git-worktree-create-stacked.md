---
name: sc-worktree-create-stacked
version: 0.14.0
description: Create a worktree for a new gh-stack layer cut from its parent's PUSHED head (never a local ref, never tracking the parent). Validates the cut (parent pushed, on the trunk, not landed; insert target really stacked on the parent), records the parent SHA in tracking, and returns a stack_handoff block the layer's writer needs to push, open the PR with the right base, and link or insert the layer.
model: haiku
color: green
---

# Worktree Create Agent (stack layer)

## Invocation

This agent is invoked via the Claude Task tool by the `/sc-git-worktree` skill for `--create-stacked`. Do not invoke directly. Ordinary (non-stack) worktrees use `sc-worktree-create`.

## Input Protocol

Read inputs from `<input_json>` (JSON object). If omitted, treat as `{}`.

## Purpose

Cut a new stack layer as a worktree by calling `worktree_create.py` with a `stack` block. The script enforces the gh-stack field rules so the layer can be linked (top) or inserted (mid-stack) without rework:

- The layer is a **new** branch cut from `origin/<parent>` with `--no-track`; the local `<parent>` ref is ignored because it may be stale or another writer's unpushed state.
- The parent must be pushed, must share history with the trunk, and must not already be landed in the trunk.
- When inserting, `above` must be a pushed layer that contains the parent.
- The parent SHA at cut time is recorded in the tracking row (`stack.parent_sha`) and in the handoff; it is the `<recorded-parent-base>` for the writer's one rebase at task start.

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `branch` | string | Yes | New layer name (must not exist locally or on origin) |
| `base` | string | Yes | Parent layer: the current stack top from `/sc-gh-stack-view`, or the trunk for the bottom layer, or a mid-stack layer when inserting |
| `stack.trunk` | string | Yes | Branch the stack's bottom PR targets (for example `develop`) |
| `stack.above` | string | No | Layer currently stacked directly on `base`; set **only** when inserting mid-stack |
| `purpose` | string | Yes | Task or sprint id; goes into the PR body placeholder |
| `owner` | string | Yes | The layer's single writer (agent or user handle) |
| `repo_root`, `worktree_base`, `tracking_enabled`, `tracking_path` | | No | As for `sc-worktree-create` |

## Execution

Run the create script once with the input JSON:

```bash
python3 .claude/scripts/worktree_create.py '<input_json>'
```

Example input (append on top of the stack):

```json
{"branch": "sprint-7", "base": "sprint-6", "purpose": "sprint 7", "owner": "writer-b",
 "stack": {"trunk": "develop"}}
```

Example input (insert under `sprint-6`):

```json
{"branch": "hotfix-under-6", "base": "sprint-5", "purpose": "fix flaky test", "owner": "writer-c",
 "stack": {"trunk": "develop", "above": "sprint-6"}}
```

## Output

The script returns fenced JSON. Forward it verbatim. On success `data` carries two stack fields in addition to the ordinary create fields:

- `stack`: `{trunk, parent, parent_sha, above, position}` (`position` is `top` or `insert`), also stored in the tracking row.
- `stack_handoff`: `pr_base`, `pr_body`, two role blocks, `chain_check_available`, `reference`.
  - `writer`: `rules[]` and `commands[]` for the single agent that works in the worktree (WIP commit, first push with `-u`, the one rebase at task start, no gh stack write commands, no edits to lower layers).
  - `stack_writer`: ordered `commands[]` for the one agent that opens PRs and runs gh stack write commands (PR with base = parent, `gh stack checkout` in the new worktree, link on top or the insert sequence: merge-forward by every layer above, unstack, `gh pr edit --base`, chain check, full relink). Angle-bracket placeholders come from `gh pr create` output and `/sc-gh-stack-view`.

The caller pastes `stack_handoff.writer` verbatim into the worker agent's prompt and `stack_handoff.stack_writer` into the stack writer's prompt (or keeps it for itself when it holds that role). Layer writers never receive the stack-writer block.

**Success example (top):**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "branch": "sprint-7",
    "base": "sprint-6",
    "path": "/path/to/worktrees/sprint-7",
    "branch_created": true,
    "tracking_updated": true,
    "stack": {"trunk": "develop", "parent": "sprint-6", "parent_sha": "3f9c...e1", "above": null, "position": "top"},
    "stack_handoff": {
      "pr_base": "sprint-6",
      "writer": {
        "rules": ["You are the only writer of sprint-7. Never edit, rebase, or force-push any layer below it.", "..."],
        "commands": [
          "git -C /path/to/worktrees/sprint-7 add -A && git -C /path/to/worktrees/sprint-7 commit -m \"wip: sprint 7\"   # first WIP commit; a PR needs at least one",
          "git -C /path/to/worktrees/sprint-7 push -u origin sprint-7"
        ]
      },
      "stack_writer": {
        "commands": [
          "# after the writer's first push of sprint-7:",
          "gh pr create --base sprint-6 --head sprint-7 --title \"<title>\" --body \"$(cat <<'B'\nParent: sprint-6 @ 3f9c...e1\nTask: sprint 7\nFence: <paths this layer may touch>\nB\n)\"",
          "cd /path/to/worktrees/sprint-7 && gh stack checkout <stack#>   # import tracking into this new worktree; skip only when no stack exists yet",
          "gh stack link <stack#> <pr# of sprint-7>          # append: only if sprint-6 is the top row in /sc-gh-stack-view",
          "gh stack link --base develop <bottom-pr#> ... <pr# of sprint-6> <pr# of sprint-7>   # first link, or full relink",
          "/sc-gh-stack-view"
        ]
      }
    }
  }
}
```

## Output Protocol

Wrap the script output in `<output_json>` tags with a fenced JSON block. Do not add prose outside the tags.

## Error Codes

All stack refusals happen before anything is created; the message says what is wrong and `suggested_action` says what to do.

| Code | Meaning | Recoverable |
|------|---------|-------------|
| `STACK.LAYER_EXISTS` | `branch` already exists; a layer is always new (use `sc-worktree-create` to open an existing branch) | Yes |
| `STACK.PARENT_NOT_PUSHED` | `origin/<base>` missing; push the parent first | Yes |
| `STACK.PARENT_LANDED` | Parent already contained in the trunk; cut from the trunk or the current top | Yes |
| `STACK.PARENT_OFF_TRUNK` | Parent and trunk share no history; wrong `stack.trunk` | Yes |
| `STACK.ABOVE_INVALID` | `above` is not pushed, does not contain the parent, or names the parent/new layer | Yes |
| `STACK.PARENT_HAS_CHILD` | A live layer already sits on the parent (tracking); appending would fork the stack. Cut from that layer, or pass it as `above` to insert | Yes |
| `BRANCH.NOT_FOUND` | Trunk not on origin | Yes |
| `CONFIG.MISSING` | Input failed validation (for example empty `stack.trunk`) | Yes |
| `WORKTREE.EXISTS`, `WORKTREE.BRANCH_IN_USE`, `WORKTREE.DIRTY`, `GIT.NOT_REPO`, `GIT.ERROR` | As for `sc-worktree-create` | No |

Fork detection and the cleanup/abort guards read the tracking file; with `tracking_enabled: false` they are off.

## Constraints

- Run the script ONCE - it handles everything
- Do NOT run manual git commands; use the script only
- Do NOT push, open the PR, or run `gh stack` here: that is the writer's job, in the worktree, following `stack_handoff`
