# GitHub Issue APIs Reference

Quick reference for GitHub CLI commands and API endpoints used by the github-issue skill.

## GitHub CLI Commands

### Authentication

```bash
# Check authentication status
gh auth status

# Login to GitHub
gh auth login

# Refresh authentication
gh auth refresh
```

### Issue Operations

```bash
# List issues
gh issue list \
  --repo owner/repo \
  --state open|closed|all \
  --label bug,enhancement \
  --assignee username \
  --limit 30 \
  --json number,title,state,labels,assignees,url,createdAt,updatedAt

# View single issue
gh issue view <number> \
  --repo owner/repo \
  --json number,title,body,state,labels,assignees,milestone,url,createdAt,updatedAt,comments

# Create issue
gh issue create \
  --repo owner/repo \
  --title "Issue title" \
  --body "Issue description" \
  --label bug,enhancement \
  --assignee user1,user2 \
  --milestone "v1.0"

# Update issue
gh issue edit <number> \
  --repo owner/repo \
  --title "New title" \
  --body "New description" \
  --add-label label1,label2 \
  --remove-label label3 \
  --add-assignee user1 \
  --remove-assignee user2

# Close issue
gh issue close <number> --repo owner/repo

# Reopen issue
gh issue reopen <number> --repo owner/repo
```

### Pull Request Operations

```bash
# Create PR
gh pr create \
  --repo owner/repo \
  --base main \
  --head feature-branch \
  --title "PR title" \
  --body "PR description" \
  --draft

# View PR
gh pr view <number> --repo owner/repo

# Enable auto-merge
gh pr merge <number> --auto --squash --repo owner/repo
```

### Repository Operations

```bash
# View repository info
gh repo view --json nameWithOwner,owner,name

# Get current repository
gh repo view --json nameWithOwner -q .nameWithOwner
```

## JSON Output Fields

### Issue Fields

```json
{
  "number": 42,
  "title": "Issue title",
  "body": "Issue description",
  "state": "open|closed",
  "labels": [
    {
      "name": "bug",
      "color": "d73a4a"
    }
  ],
  "assignees": [
    {
      "login": "username"
    }
  ],
  "milestone": {
    "title": "v1.0",
    "number": 1
  },
  "url": "https://github.com/owner/repo/issues/42",
  "createdAt": "2025-12-01T10:00:00Z",
  "updatedAt": "2025-12-02T15:30:00Z",
  "comments": {
    "totalCount": 3
  }
}
```

### Pull Request Fields

```json
{
  "number": 123,
  "title": "PR title",
  "body": "PR description",
  "state": "open|closed|merged",
  "baseRefName": "main",
  "headRefName": "feature-branch",
  "url": "https://github.com/owner/repo/pull/123",
  "isDraft": false,
  "mergeable": "MERGEABLE|CONFLICTING|UNKNOWN"
}
```

## GitHub REST API

Alternative to `gh` CLI for advanced use cases.

### Authentication

```bash
# Using personal access token
curl -H "Authorization: token ghp_xxxx" \
  https://api.github.com/user
```

### Issue Endpoints

```bash
# List issues
GET /repos/{owner}/{repo}/issues

# Get single issue
GET /repos/{owner}/{repo}/issues/{issue_number}

# Create issue
POST /repos/{owner}/{repo}/issues
{
  "title": "Issue title",
  "body": "Issue description",
  "labels": ["bug"],
  "assignees": ["user1"]
}

# Update issue
PATCH /repos/{owner}/{repo}/issues/{issue_number}
{
  "title": "New title",
  "state": "closed"
}
```

## Rate Limits

GitHub API rate limits:
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour

Check rate limit:
```bash
gh api rate_limit
```

## Error Codes

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `204`: No Content (success with no response body)
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden (rate limit or permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (validation failed)

## URL Formats

Issue URLs:
- Standard: `https://github.com/owner/repo/issues/42`
- With comment: `https://github.com/owner/repo/issues/42#issuecomment-123`
- Short form: `owner/repo#42`

## Best Practices

1. **Always use `--json` flag**: Easier to parse than human-readable output
2. **Check authentication first**: Fail fast if not authenticated
3. **Handle rate limits**: Implement retry with exponential backoff
4. **Validate repository access**: Check permissions before mutations
5. **Use issue references**: `Fixes #42`, `Closes #42`, `Resolves #42` in PRs
