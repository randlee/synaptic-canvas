---
name: issue-pr-agent
version: 0.1.0
description: Create pull requests for issue fixes
---

# Issue PR Agent

Create a pull request from a fix branch with proper issue references and templated body.

## Purpose

Final step of the fix workflow:
1. Generate PR title and body from issue and template
2. Create PR using GitHub CLI
3. Link PR to issue with "Fixes #N" syntax
4. Return PR details for user display

## Input Contract

```json
{
  "issue_number": 42,
  "issue_title": "Application crashes on startup",
  "repo": "owner/repo",
  "branch": "fix-issue-42",
  "base_branch": "main",
  "commits": [
    {
      "sha": "abc123",
      "message": "Fix #42: Application crashes on startup"
    }
  ],
  "pr_template": null,
  "draft": false
}
```

**Fields**:
- `issue_number`: Required. Issue number being fixed
- `issue_title`: Required. Issue title for PR title
- `repo`: Required. Repository in "owner/repo" format
- `branch`: Required. Fix branch name (head)
- `base_branch`: Required. Target branch (base)
- `commits`: Required. Array of commits in the fix
- `pr_template`: Optional. Template string for PR body
- `draft`: Optional. Create as draft PR (default: false)

## Output Contract

```json
{
  "success": true,
  "data": {
    "pr_number": 123,
    "url": "https://github.com/owner/repo/pull/123",
    "title": "Fix #42: Application crashes on startup",
    "state": "open",
    "draft": false,
    "head": "fix-issue-42",
    "base": "main"
  },
  "error": null
}
```

**On Error**:
```json
{
  "success": false,
  "data": null,
  "error": "GH.BRANCH.NOT_PUSHED: Branch fix-issue-42 not found on remote"
}
```

## Implementation

### PR Title Generation
Default pattern: `Fix #<issue_number>: <issue_title>`

Example: `Fix #42: Application crashes on startup`

### PR Body Generation

If `pr_template` provided, perform substitutions:
- `{issue_number}` → issue number
- `{issue_title}` → issue title
- `{commits}` → formatted commit list

Default template if none provided:
```markdown
## Summary
Fixes #<issue_number>

## Changes
<List of commits with SHA and message>

## Testing
<Test results from fix agent>
```

### Create PR

```bash
gh pr create \
  --repo "$repo" \
  --base "$base_branch" \
  --head "$branch" \
  --title "$pr_title" \
  --body "$pr_body" \
  --json number,url,title,state,isDraft \
  ${draft:+--draft}
```

### Link to Issue

Ensure PR body contains `Fixes #<issue_number>` so GitHub auto-links and auto-closes on merge.

## Error Codes

- `GH.AUTH.REQUIRED` - GitHub CLI not authenticated
- `GH.PERMISSION_DENIED` - No write access to repository
- `GH.BRANCH.NOT_PUSHED` - Fix branch not found on remote
- `GH.PR.ALREADY_EXISTS` - PR already exists for this branch
- `GH.VALIDATION_FAILED` - Invalid PR parameters
- `GH.RATE_LIMIT` - API rate limit exceeded
- `EXEC.FAILED` - Command execution failed

## Safety

- Verify branch exists on remote before creating PR
- Confirm base branch exists
- Always include issue reference for auto-linking
- Handle PR-already-exists gracefully (return existing PR)

## Configuration Integration

Reads `pr_template` from input (populated from `.claude/config.yaml`):
```yaml
github:
  pr_template: |
    ## Summary
    Fixes #{issue_number}

    ## Description
    {issue_title}

    ## Changes
    {commits}
```

Template substitutions:
- `{issue_number}` → issue number
- `{issue_title}` → issue title
- `{commits}` → formatted list of commits

## Draft PR Strategy

Create as draft if:
1. `draft: true` in input, OR
2. Fix agent included TODO comments (detected from commit diffs)

User can convert draft to ready in GitHub UI after review.

## References

See `.claude/references/github-issue-apis.md` for GitHub CLI command patterns.

## Examples

**Create PR**:
```json
{
  "issue_number": 42,
  "issue_title": "Application crashes on startup",
  "repo": "anthropics/claude-code",
  "branch": "fix-issue-42",
  "base_branch": "main",
  "commits": [
    {
      "sha": "abc123def456",
      "message": "Fix #42: Application crashes on startup"
    }
  ],
  "pr_template": "## Summary\nFixes #{issue_number}\n\n## Changes\n{commits}",
  "draft": false
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "pr_number": 123,
    "url": "https://github.com/anthropics/claude-code/pull/123",
    "title": "Fix #42: Application crashes on startup",
    "state": "open",
    "draft": false,
    "head": "fix-issue-42",
    "base": "main"
  },
  "error": null
}
```

**Error - branch not pushed**:
```json
{
  "success": false,
  "data": null,
  "error": "GH.BRANCH.NOT_PUSHED: Branch fix-issue-42 not found on remote. Ensure commits were pushed."
}
```
