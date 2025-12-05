# CI Automation Checklists

## Validation Gate
- [ ] Repo clean (unless allow_dirty)
- [ ] Config present (`.claude/ci-automation.yaml` or fallback)
- [ ] Auth available for PR (e.g., `GITHUB_TOKEN`)
- [ ] Dest/src resolved correctly

## Build Gate
- [ ] Run `build_command`
- [ ] Capture warnings (respect `allow_warnings`)
- [ ] If failure: classify straightforward vs. needs human input

## Test Gate
- [ ] Run `test_command`
- [ ] Capture warnings (respect `allow_warnings`)
- [ ] If failure: classify straightforward vs. needs human input

## Fix Heuristics (v0.1.0)
- Auto-fix low risk:
  - Missing imports/dependencies
  - Formatting/lint/obvious unused vars/type hints
  - Clear deprecation replacements
- Stop and escalate:
  - Logic/control-flow changes
  - API signature changes
  - Schema/migration changes
  - Security/auth/data persistence
  - >10 files touched or risk > low

## Root Cause Report Schema (example)
```json
{
  "success": true,
  "data": {
    "summary": "Build failed due to missing dependency and type mismatch",
    "root_causes": [
      {
        "category": "BUILD.DEPENDENCY_MISSING",
        "description": "Package foo not found",
        "affected_files": ["requirements.txt"],
        "confidence": "high"
      }
    ],
    "recommendations": [
      {
        "action": "Add foo>=2.0.0 to requirements.txt",
        "rationale": "Dependency missing",
        "estimated_effort": "5m",
        "risk": "low"
      }
    ],
    "blocking": true,
    "requires_human_input": true
  },
  "error": null
}
```

## PR Gate
- [ ] All gates passed
- [ ] Confirm PR target (main/master needs explicit confirmation unless `--dest main`)
- [ ] Build/test clean (or warnings allowed)
- [ ] Commit message and PR body populated
- [ ] Optional idempotency key for PR (future)
