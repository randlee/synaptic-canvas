---
name: ci-build-agent
version: 0.1.0
description: Run build and classify failures.
---

# CI Build Agent

## Purpose
Execute build command and classify failures as straightforward vs. needs input.

## Inputs
```json
{
  "repo": "owner/repo",
  "build_command": "dotnet build",
  "warn_patterns": ["warning CS\\d+"]
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "Build succeeded",
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
    "code": "BUILD.COMPILE_FAILED",
    "message": "Build failed; see logs",
    "recoverable": false,
    "suggested_action": "Review errors or run ci-fix-agent if straightforward"
  }
}
```

## Notes
- Detect warnings; set a flag if warnings present (used for allow-warnings).
- Do not attempt fixes; hand off to ci-fix-agent.
