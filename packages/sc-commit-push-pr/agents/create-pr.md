---
name: create-pr
version: 0.1.0
description: Background agent for creating PRs from title/body.
hooks:
  SubAgentStart:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 .claude/scripts/create_pr_agent_start_hook.py"
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

## Preflight Hook

The SubAgentStart hook validates:
- Protected branches are configured in `.sc/shared-settings.yaml`
- Git authentication and PR creation permissions are valid
- Logs preflight status to `.claude/state/logs/sc-commit-push-pr/`

If preflight fails, the hook exits with code 2 to block execution.

## Error Codes

- `PR.CREATE_FAILED` - Provider API failed to create PR
- `PR.ALREADY_EXISTS` - PR already exists for this branch combination
- `PROVIDER.DETECT_FAILED` - Could not detect provider from git remote
- `PROVIDER.UNSUPPORTED` - Provider not supported
