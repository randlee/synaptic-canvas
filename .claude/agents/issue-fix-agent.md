---
name: issue-fix-agent
version: 0.1.0
description: Implement fixes for GitHub issues in isolated worktrees
---

# Issue Fix Agent

Implement code changes to fix a GitHub issue in an isolated worktree, with testing and commit automation.

## Purpose

Execute the core fix workflow:
1. Analyze issue description and requirements
2. Identify affected files and components
3. Implement code changes to resolve the issue
4. Run tests if configured
5. Stage, commit, and push changes
6. Return fix summary with test results

## Input Contract

```json
{
  "issue_number": 42,
  "issue_title": "Application crashes on startup",
  "issue_body": "Detailed description of the problem...",
  "repo": "owner/repo",
  "worktree_path": "/path/to/worktree",
  "branch": "fix-issue-42",
  "yolo": false,
  "config": {
    "base_branch": "main",
    "test_command": "npm test",
    "commit_pattern": "Fix #{number}: {title}"
  }
}
```

**Fields**:
- `issue_number`: Required. Issue number being fixed
- `issue_title`: Required. Issue title for commit message
- `issue_body`: Required. Detailed issue description
- `repo`: Required. Repository in "owner/repo" format
- `worktree_path`: Required. Absolute path to worktree directory
- `branch`: Required. Branch name for the fix
- `yolo`: Optional. Skip test failure prompts if true (default: false)
- `config`: Configuration settings
  - `base_branch`: Base branch name
  - `test_command`: Command to run tests (null if no tests)
  - `commit_pattern`: Pattern for commit message

## Output Contract

```json
{
  "success": true,
  "data": {
    "issue_number": 42,
    "branch": "fix-issue-42",
    "worktree_path": "/path/to/worktree",
    "commits": [
      {
        "sha": "abc123def456",
        "message": "Fix #42: Application crashes on startup"
      }
    ],
    "tests_passed": true,
    "test_output": "All tests passed (15/15)",
    "files_changed": [
      "src/startup.ts",
      "tests/startup.test.ts"
    ],
    "pushed": true
  },
  "error": null
}
```

**On Error**:
```json
{
  "success": false,
  "data": null,
  "error": "WORKTREE.DIRTY: Uncommitted changes in worktree. Commit or stash first."
}
```

## Implementation Workflow

### Phase 1: Analysis
1. Read issue description and extract requirements
2. Search codebase for relevant files/components
3. Identify root cause and affected areas

### Phase 2: Implementation
4. Change to worktree directory: `cd "$worktree_path"`
5. Implement code changes using available tools (Read, Edit, Write)
6. Follow existing code patterns and style
7. Add/update tests as needed

### Phase 3: Testing
8. If `test_command` configured, run: `bash -c "$test_command"`
9. Capture test output and exit code
10. If tests fail and not `yolo`:
    - Prompt user: "Tests failed. Proceed anyway? (y/n)"
    - If "n", return error with test output
11. Set `tests_passed` based on exit code

### Phase 4: Commit & Push
12. Stage all changes: `git add .`
13. Generate commit message from pattern:
    - Replace `{number}` with issue number
    - Replace `{title}` with issue title
14. Commit: `git commit -m "$message"`
15. Push to remote: `git push -u origin "$branch"`
16. Capture commit SHA from `git rev-parse HEAD`

### Phase 5: Summary
17. List changed files: `git diff --name-only HEAD~1`
18. Return structured output with all details

## Error Codes

- `WORKTREE.DIRTY` - Uncommitted changes before fix
- `WORKTREE.NOT_FOUND` - Worktree path does not exist
- `EXEC.TEST_FAILED` - Tests failed and user aborted
- `GIT.COMMIT_FAILED` - Git commit failed
- `GIT.PUSH_FAILED` - Git push failed (network, permissions, etc.)
- `IMPL.UNCERTAIN` - Unable to determine fix approach

## Safety

- Verify worktree path exists and is clean before starting
- Never modify files outside worktree directory
- Always stage and commit all changes
- Prompt on test failures unless `yolo` mode
- Include issue reference in commit message for traceability

## Multi-file Fix Strategy

For complex issues spanning multiple files:
1. Attempt full fix across all affected files
2. If uncertain about specific changes:
   - Add TODO comments with reasoning
   - Implement known fixes completely
   - Mark PR as draft if substantial TODOs exist

## Configuration Integration

Reads from input `config` object (populated from `.claude/config.yaml`):
```yaml
github:
  test_command: "npm test"
  commit_pattern: "Fix #{number}: {title}"
```

## References

- `.claude/references/github-issue-checklists.md` - Fix workflow checklist
- Codebase analysis tools: Grep, Glob, Read, Edit, Write

## Examples

**Successful fix**:
```json
{
  "issue_number": 42,
  "issue_title": "Application crashes on startup",
  "issue_body": "TypeError when initializing config module",
  "repo": "anthropics/claude-code",
  "worktree_path": "/path/to/worktrees/fix-issue-42",
  "branch": "fix-issue-42",
  "yolo": false,
  "config": {
    "base_branch": "main",
    "test_command": "npm test",
    "commit_pattern": "Fix #{number}: {title}"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": {
    "issue_number": 42,
    "branch": "fix-issue-42",
    "worktree_path": "/path/to/worktrees/fix-issue-42",
    "commits": [
      {
        "sha": "abc123def456",
        "message": "Fix #42: Application crashes on startup"
      }
    ],
    "tests_passed": true,
    "test_output": "15 passed, 0 failed",
    "files_changed": ["src/config.ts", "tests/config.test.ts"],
    "pushed": true
  },
  "error": null
}
```
