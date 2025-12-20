---
name: ci-validate-agent
version: 0.1.0
description: Pre-flight checks for CI automation (clean repo, config, auth).
---

# CI Validate Agent

## Purpose
Stop early if prerequisites aren’t met.

## Inputs
```json
{
  "repo": "owner/repo",
  "allow_dirty": false,
  "config_path": ".claude/ci-automation.yaml",
  "auth_required": true
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "Validation passed",
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
    "code": "VALIDATION.DIRTY_REPO",
    "message": "Working tree not clean",
    "recoverable": false,
    "suggested_action": "Commit/stash changes or rerun with allow_dirty"
  }
}
```

## Checks
- Git clean (unless overridden).
- Config present (preferred `.claude/ci-automation.yaml`, fallback `.claude/config.yaml`).
- Auth available for PR operations (e.g., `GITHUB_TOKEN`).

## Notes
- No fixes; report and exit.
