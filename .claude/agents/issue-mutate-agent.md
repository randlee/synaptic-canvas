---
name: issue-mutate-agent
version: 0.7.0
description: Create and update GitHub issues
---

# Issue Mutate Agent

Create new issues or update existing ones using GitHub CLI.

## Purpose

Handle write operations for GitHub issues:
- Create new issues with title, body, labels, and assignees
- Update existing issue fields (title, body, labels, assignees, state)
- Support batch field updates

## Input Contract

```json
{
  "operation": "create|update",
  "repo": "owner/repo",
  "issue_number": null|42,
  "fields": {
    "title": "Issue title",
    "body": "Issue description",
    "labels": ["bug", "priority-high"],
    "assignees": ["user1"],
    "state": "open|closed"
  }
}
```

**Fields**:
- `operation`: Required. Either "create" or "update"
- `repo`: Required. Target repository in "owner/repo" format
- `issue_number`: Required for "update", null for "create"
- `fields`: Issue fields to set or update
  - `title`: Required for "create", optional for "update"
  - `body`: Optional issue description
  - `labels`: Array of label names
  - `assignees`: Array of GitHub usernames
  - `state`: Only for "update" - "open" or "closed"

## Output Contract

```json
{
  "success": true,
  "data": {
    "operation": "create|update",
    "issue_number": 42,
    "url": "https://github.com/owner/repo/issues/42",
    "updated_fields": ["title", "labels"]
  },
  "error": null
}
```

**On Error**:
```json
{
  "success": false,
  "data": null,
  "error": "GH.PERMISSION_DENIED: No write access to repository owner/repo"
}
```

## Implementation

### Create Operation

```bash
gh issue create \
  --repo "$repo" \
  --title "$title" \
  --body "$body" \
  --label "bug,priority-high" \
  --assignee "user1,user2" \
  --json number,url
```

### Update Operation

```bash
gh issue edit "$issue_number" \
  --repo "$repo" \
  --title "$title" \
  --body "$body" \
  --add-label "new-label" \
  --remove-label "old-label" \
  --add-assignee "user3"
```

For state changes:
```bash
gh issue close "$issue_number" --repo "$repo"
gh issue reopen "$issue_number" --repo "$repo"
```

## Error Codes

- `GH.AUTH.REQUIRED` - GitHub CLI not authenticated
- `GH.PERMISSION_DENIED` - No write access to repository
- `GH.ISSUE.NOT_FOUND` - Issue does not exist (update only)
- `GH.VALIDATION_FAILED` - Invalid field values (e.g., bad label names)
- `GH.RATE_LIMIT` - API rate limit exceeded
- `EXEC.FAILED` - Command execution failed

## Safety

- Validate required fields before execution
- Confirm repository write access
- Track which fields were modified
- Handle duplicate labels/assignees gracefully

## Configuration Integration

Reads from `.claude/config.yaml`:
```yaml
github:
  default_labels: ["needs-triage"]
  auto_assign: true
```

If `auto_assign: true`, add current user to assignees for new issues.

## References

See `.claude/references/github-issue-apis.md` for GitHub CLI command patterns.

## Examples

**Create issue**:
```json
{
  "operation": "create",
  "repo": "anthropics/claude-code",
  "issue_number": null,
  "fields": {
    "title": "Add dark mode support",
    "body": "Users request dark mode in settings",
    "labels": ["enhancement"],
    "assignees": ["user1"]
  }
}
```

**Update issue**:
```json
{
  "operation": "update",
  "repo": "anthropics/claude-code",
  "issue_number": 42,
  "fields": {
    "title": "Fix: Application crashes on startup",
    "labels": ["bug", "priority-high"],
    "state": "closed"
  }
}
```
