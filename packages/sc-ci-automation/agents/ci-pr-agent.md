---
name: ci-pr-agent
version: 0.1.0
description: Commit, push, and create PR after quality gates pass.
---

# CI PR Agent

## Purpose
Perform final commit/push/PR when gates are clean and user allows (or `--yolo`).

## Inputs
```json
{
  "repo": "owner/repo",
  "src_branch": "feature-x",
  "dest_branch": "develop",
  "pr_title": "CI automation fixes",
  "pr_body": "Summary of changes",
  "pr_template_path": ".github/PULL_REQUEST_TEMPLATE.md",
  "allow_warnings": false
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "PR created",
    "pr_url": "https://github.com/owner/repo/pull/123",
    "branch": "feature-x"
  },
  "error": null
}
```

## Outputs (error)
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PR.NO_CHANGES",
    "message": "No changes to commit",
    "recoverable": false,
    "suggested_action": "Skip PR or rerun after changes"
  }
}
```

## Notes
- Respect protected branches; confirm PR to main/master unless `--dest main` specified.
- Avoid duplicate PRs; consider idempotency keys in future versions.
