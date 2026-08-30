---
name: create-pr
version: 0.12.0
description: Background agent for creating PRs from title/body.
hooks:
  SubAgentStart:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_pr_agent_start_hook.py"
---

# Create-PR Agent

Background agent that creates pull requests from provided title and body.

## Purpose

This agent creates a pull request using the appropriate provider (GitHub or Azure DevOps):
1. Accept PR title, body, source and destination branches
2. Detect provider from git remote
3. Create PR via provider API
4. Return PR info (id, url, branches)

## Input

The agent requires PR details via the prompt:

```json
{
  "title": "feat: Add new feature",
  "body": "## Summary\n\nThis PR adds...",
  "source": "feature-branch",
  "destination": "main"
}
```

## Output

Returns fenced JSON with standard envelope.

### Success

```json
{
  "success": true,
  "data": {
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

### Error

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PR.CREATE_FAILED",
    "message": "Failed to create PR: API returned 422",
    "recoverable": false,
    "suggested_action": "Check branch names and permissions, then retry."
  }
}
```

## Stacked Branches

This agent must never work around a `STACK.USE_GH_STACK` refusal with a
direct `gh pr create` -- surface it to the user and defer to the
**managing-gh-stacks skill (package `sc-gh-stack`)**. Two distinct gh-stack
gates apply:

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
   nothing changes. On a layer, PR creation is refused with
   `STACK.USE_GH_STACK` -- a layer's correct PR base (the layer below it,
   with stack object linkage) can only be set by `gh stack submit --auto`.

## Preflight Hook

The SubAgentStart hook validates:
- gh-stack toolchain prerequisites (gh CLI, gh-stack extension,
  managing-gh-stacks skill) are all present -- unconditional, every run
- Protected branches are configured in `.sc/shared-settings.yaml`
- Git authentication and PR creation permissions are valid
- Logs preflight status to `.claude/state/logs/sc-commit-push-pr/`

If preflight fails, the hook exits with code 2 to block execution.

## Error Codes

- `PR.CREATE_FAILED` - Provider API failed to create PR
- `PR.ALREADY_EXISTS` - PR already exists for this branch combination
- `PROVIDER.DETECT_FAILED` - Could not detect provider from git remote
- `PROVIDER.UNSUPPORTED` - Provider not supported
- `STACK.USE_GH_STACK` - Branch is a gh-stack layer; PR creation is owned by `gh stack submit --auto` (recoverable -- defer to managing-gh-stacks, never work around)
- `PREFLIGHT.STACK_PREREQS_MISSING` - gh-stack toolchain not installed (recoverable -- install what `suggested_action` lists)
