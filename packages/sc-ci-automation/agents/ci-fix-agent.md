---
name: ci-fix-agent
version: 0.1.0
description: Apply straightforward fixes for build/test issues.
---

# CI Fix Agent

## Purpose
Attempt low-risk fixes for build/test failures and warnings.

## Inputs
```json
{
  "repo": "owner/repo",
  "issue_type": "BUILD|TEST|WARN",
  "details": "compiler/test output",
  "files": ["file1", "file2"],
  "allow_warnings": false
}
```

## Outputs (success)
```json
{
  "success": true,
  "data": {
    "summary": "Applied straightforward fixes",
    "patch_summary": "Added missing import; updated dependency",
    "risk": "low",
    "files_changed": ["src/app.py"],
    "followups": []
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
    "code": "FIX.NOT_STRAIGHTFORWARD",
    "message": "Fix requires logic changes",
    "recoverable": false,
    "suggested_action": "Escalate to root-cause agent or human review"
  }
}
```

## Heuristics (auto-fix)
- Missing imports/dependencies.
- Formatting/linters.
- Obvious unused vars/type hints.
- Deprecation replacements when clear.
- Limited scope: avoid fundamental logic changes; stop if fix touches >10 files or risk > low.

## Notes
- Do not modify protected areas (auth, security, migrations).
- Return followups for anything needing human review.
