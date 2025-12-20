---
name: type-librarian-refresh
description: Refresh the annotations/testing cache by running the extract script; report updated packages.
model: sonnet
version: 0.5.0
---

# Type Librarian Refresh

## Purpose
Update `.claude-cache/claude-docs/` from embedded NuGet package docs.

## Inputs
- None.

## Execution Steps
1) Run `scripts/extract-claude-docs.ps1`.
2) On non-zero exit, return `success=false` with `error.code="SCRIPT_FAILED"`, include exit code/message, `recoverable=false`.
3) On success, note which packages were refreshed when available.
4) Return fenced JSON minimal envelope.

## Output Format
```json
{
  "success": true,
  "data": {
    "action": "refresh-cache",
    "script": "scripts/extract-claude-docs.ps1",
    "packages_updated": ["Radiant.Annotations", "Radiant.Testing.XUnit"]
  },
  "error": null
}
```

## Error Handling
- `SCRIPT_FAILED`: PowerShell script failed; recoverable=false; include exit code/message.
