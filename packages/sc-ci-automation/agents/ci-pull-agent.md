---
name: ci-pull-agent
version: 0.1.0
description: Pull target branch and handle straightforward conflicts.
---

# CI Pull Agent

## Purpose
Pull from dest branch (inferred tracking or `--dest`) and handle simple merge conflicts.

## Inputs
```json
{
  "dest_branch": "develop",
  "src_branch": "feature-x",
  "repo": "owner/repo"
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "Pulled develop into feature-x",
    "actions": []
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
    "code": "GIT.MERGE_CONFLICT",
    "message": "Manual conflict resolution required",
    "recoverable": false,
    "suggested_action": "Resolve conflicts and rerun"
  }
}
```

## Notes
- Handle only straightforward conflicts (e.g., auto-merge trivial cases); otherwise stop.
- Never force-pull.
