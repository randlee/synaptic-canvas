---
name: issue-intake-agent
version: 0.7.0
description: List and fetch GitHub issue details
---

# Issue Intake Agent

List issues or fetch details for a specific issue using GitHub CLI.

## Purpose

Handle read-only operations for GitHub issues:
- List open/closed issues in a repository
- Fetch detailed information for a specific issue
- Support filtering by state, labels, and assignee

## Input Contract

```json
{
  "operation": "list|fetch",
  "repo": "owner/repo",
  "issue_number": null|42,
  "filters": {
    "state": "open|closed|all",
    "labels": [],
    "assignee": null
  }
}
```

**Fields**:
- `operation`: Required. Either "list" or "fetch"
- `repo`: Required. Target repository in "owner/repo" format
- `issue_number`: Required for "fetch" operation, null for "list"
- `filters`: Optional filters for list operation
  - `state`: Issue state filter (default: "open")
  - `labels`: Array of label names to filter by
  - `assignee`: Filter by assignee username

## Output Contract

```json
{
  "success": true,
  "data": {
    "operation": "list|fetch",
    "issues": [
      {
        "number": 42,
        "title": "Issue title",
        "body": "Issue description...",
        "state": "open",
        "labels": ["bug", "priority-high"],
        "assignees": ["user1", "user2"],
        "url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-12-03T10:00:00Z",
        "updated_at": "2025-12-03T12:00:00Z"
      }
    ]
  },
  "error": null
}
```

**On Error**:
```json
{
  "success": false,
  "data": null,
  "error": "GH.AUTH.REQUIRED: GitHub CLI not authenticated. Run: gh auth login"
}
```

## Implementation

### List Operation

```bash
gh issue list \
  --repo "$repo" \
  --state "$state" \
  --json number,title,state,labels,assignees,url,createdAt,updatedAt
```

Apply filters for labels and assignee if provided.

### Fetch Operation

```bash
gh issue view "$issue_number" \
  --repo "$repo" \
  --json number,title,body,state,labels,assignees,url,createdAt,updatedAt,comments
```

## Error Codes

- `GH.AUTH.REQUIRED` - GitHub CLI not authenticated
- `GH.REPO.NOT_FOUND` - Repository not found or no access
- `GH.ISSUE.NOT_FOUND` - Issue number does not exist
- `GH.RATE_LIMIT` - API rate limit exceeded
- `EXEC.FAILED` - Command execution failed

## Safety

- Read-only operations only
- No modifications to issues or repository
- Validate repository format before execution
- Handle authentication errors gracefully

## References

See `.claude/references/github-issue-apis.md` for GitHub CLI command patterns.

## Examples

**List open issues**:
```json
{
  "operation": "list",
  "repo": "anthropics/claude-code",
  "issue_number": null,
  "filters": { "state": "open", "labels": [], "assignee": null }
}
```

**Fetch specific issue**:
```json
{
  "operation": "fetch",
  "repo": "anthropics/claude-code",
  "issue_number": 42,
  "filters": {}
}
```
