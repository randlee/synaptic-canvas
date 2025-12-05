# CI Automation Data Contracts

## Minimal Envelope (all agents)
```json
{
  "success": true,
  "data": {
    "summary": "Operation completed successfully",
    "actions": ["action1", "action2"]
  },
  "error": null
}
```

## Error Schema
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NAMESPACE.CODE",
    "message": "Human-readable detail",
    "recoverable": false,
    "suggested_action": "Next step"
  }
}
```

Namespaces: `VALIDATION.*`, `GIT.*`, `BUILD.*`, `TEST.*`, `PR.*`, `EXECUTION.*`.

## Agent-Specific Notes
- Fix agent: include `patch_summary`, `risk`, `files_changed`, `followups`.
- Root-cause agent: include `root_causes[]`, `recommendations[]`, `blocking`, `requires_human_input`.
