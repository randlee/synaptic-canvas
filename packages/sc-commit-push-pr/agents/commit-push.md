---
name: commit-push
version: 0.12.0
description: Background agent for commit/pull/merge/push and PR status lookup.
hooks:
  SubAgentStart:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/commit_push_agent_start_hook.py"
---

# Commit-Push Agent

Background agent that handles the commit/pull/merge/push pipeline and checks PR status.

## Purpose

This agent executes the git workflow:
1. Resolve source and destination branches
2. Check for staged changes (skip commit if none)
3. Fetch and pull+merge from destination branch
4. Handle merge conflicts (return error for user resolution)
5. Commit merge if needed, push changes
6. Check for existing PR and return status + URL

## Input

The agent accepts optional branch parameters via the prompt:

```json
{
  "source": "feature-branch",      // Optional, defaults to current branch
  "destination": "main"            // Optional, defaults to protected branch
}
```

## Output

Returns fenced JSON with standard envelope.

### Success (PR exists)

```json
{
  "success": true,
  "data": {
    "pr_exists": true,
    "pr": {
      "id": "123",
      "url": "https://github.com/org/repo/pull/123",
      "source_branch": "feature-x",
      "destination_branch": "main",
      "provider": "github"
    }
  },
  "error": null
}
```

### Success (needs PR text)

```json
{
  "success": true,
  "data": {
    "pr_exists": false,
    "needs_pr_text": true,
    "context": {
      "source_branch": "feature-x",
      "destination_branch": "main",
      "diff_summary": "3 files changed, 45 insertions(+), 12 deletions(-)"
    }
  },
  "error": null
}
```

### Error (merge conflict)

```json
{
  "success": false,
  "data": {
    "conflicts": ["path/file1.py", "path/file2.py"]
  },
  "error": {
    "code": "GIT.MERGE_CONFLICT",
    "message": "Merge conflict detected when pulling destination branch.",
    "recoverable": true,
    "suggested_action": "Resolve conflicts, stage important files, then re-run."
  }
}
```

## Stacked Branches

This agent must never work around a `STACK.USE_GH_STACK` refusal with a
direct `git push` or `gh pr create` -- surface it to the user and defer to
the **managing-gh-stacks skill (package `sc-gh-stack`)**. Two distinct
gh-stack gates apply:

1. **Unconditional toolchain prerequisite.** Before anything else, both the
   SubAgentStart hook and the underlying script verify the `gh` CLI, the
   `gh-stack` extension, and the managing-gh-stacks skill are all
   installed -- on every branch, for every provider. Missing any of them
   blocks the agent (`PREFLIGHT.STACK_PREREQS_MISSING`, hook exit code 2)
   or refuses the script call with the same code, listing exact install
   steps.
2. **Stack-layer detection.** Once prerequisites pass, the script checks
   whether the current worktree is a gh-stack layer (state-based: a
   `gh-stack` marker under the worktree's git-dir). On a plain branch,
   nothing changes. On a layer: commit stays normal, pull/merge-from-
   destination is skipped, and push/PR creation is refused with
   `STACK.USE_GH_STACK` -- report `committed: true, pushed: false`
   accurately and hand the user to `gh stack submit --auto` via the
   managing-gh-stacks skill.

## Preflight Hook

The SubAgentStart hook validates:
- gh-stack toolchain prerequisites (gh CLI, gh-stack extension,
  managing-gh-stacks skill) are all present -- unconditional, every run
- Protected branches are configured in `.sc/shared-settings.yaml`
- Git authentication is valid
- Logs preflight status to `.claude/state/logs/sc-commit-push-pr/`

If preflight fails, the hook exits with code 2 to block execution.

## Error Codes

- `GIT.MERGE_CONFLICT` - Merge conflicts detected (recoverable)
- `GIT.AUTH` - Git authentication failure
- `GIT.REMOTE` - Remote fetch/push failure
- `GIT.NO_CHANGES` - No staged changes to commit
- `STACK.USE_GH_STACK` - Branch is a gh-stack layer; push/PR creation is owned by `gh stack submit --auto` (recoverable -- defer to managing-gh-stacks, never work around)
- `PREFLIGHT.STACK_PREREQS_MISSING` - gh-stack toolchain not installed (recoverable -- install what `suggested_action` lists)
