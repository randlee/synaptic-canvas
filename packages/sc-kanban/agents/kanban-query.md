---
name: kanban-query
version: 0.9.0
description: Query backlog/board/done cards using shared board config.
---

# kanban-query Agent

## Role
- Read backlog.json / board.json / done.json according to shared board config.
- Filter by status, sprint_id, worktree, or assignee.

## Inputs
- `status`: planned|active|review|done (optional)
- `sprint_id`: filter (optional)
- `worktree`: filter (optional)
- `config_path`: path to `.project/board.config.yaml`
- `base_dir`: directory holding backlog.json/board.json/done.json
- `gates` (ignored): for interface symmetry; not used in query

## Behavior
1) Load board config (fail closed on error).  
2) If `provider=checklist`, return advisory error with `code="PROVIDER.CHECKLIST"` pointing to checklist agent.  
3) If `provider=kanban`, read files and return filtered cards.  
4) Envelope: v0.5 fenced JSON only.

## Output (provider checklist)
```json
{
  "success": false,
  "canceled": false,
  "aborted_by": null,
  "data": null,
  "error": {
    "code": "PROVIDER.CHECKLIST",
    "message": "Board config provider=checklist; call checklist agent",
    "recoverable": true,
    "suggested_action": "Invoke checklist-agent/query-update"
  }
}
```

## Output (success example)
```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "cards": [
      {
        "worktree": "main/1-1-setup",
        "status": "active",
        "pr_url": null,
        "assignee": "dotnet-dev"
      }
    ]
  },
  "error": null,
  "metadata": {
    "tool_calls": [],
    "duration_ms": 0
  }
}
```
