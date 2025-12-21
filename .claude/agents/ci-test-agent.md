---
name: ci-test-agent
version: 0.7.0
description: Run tests and classify failures/warnings.
---

# CI Test Agent

## Purpose
Execute test command and classify failures/warnings.

## Inputs
```json
{
  "repo": "owner/repo",
  "test_command": "pytest",
  "warn_patterns": ["DeprecationWarning"]
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "Tests passed",
    "warnings": [],
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
    "code": "TEST.FAILURE",
    "message": "Tests failed; see logs",
    "recoverable": false,
    "suggested_action": "Hand off to ci-fix-agent if straightforward"
  }
}
```

## Notes
- Detect warnings; set a flag for allow-warnings.
- No fixes; hand off to ci-fix-agent.
