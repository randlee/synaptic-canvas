---
name: kanban-card
version: 0.8.0
description: Create or update kanban cards (backlog → board) using shared board config.
---

# kanban-card

## Role
- Create lean backlog entries or rich board entries.
- Update existing cards with planning/execution metadata (pr_url, status_report, actual_cycles).

## Inputs
- `action`: `create` | `update` (default: create)
- `card`: object with fields (worktree or sprint_id required; other fields as needed)
- `target_status`: backlog|planned|active|review (default: backlog)
- `config_path`: path to `.project/board.config.yaml`
- `base_dir`: workspace root (default ".")

## Behavior
- Load board config (fail closed).
- If provider=checklist, return advisory (`PROVIDER.CHECKLIST`).
- `create`:
  - target_status=backlog → add to backlog.json (lean)
  - target_status in planned/active/review → add to board.json (rich), remove duplicates from backlog/board
- `update`: merge fields into existing card in backlog or board; error if not found.
- Persist backlog.json / board.json; return updated card.

## Output (v0.5 envelope)
```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": { "card": { "worktree": "main/1-1", "status": "planned" } },
  "error": null,
  "metadata": { "tool_calls": [], "duration_ms": 0 }
}
```

## Errors
- `CONFIG.INVALID`, `PROVIDER.CHECKLIST`, `CARD.NOT_FOUND`, `INPUT.UNSUPPORTED_ACTION`, `INPUT.MISSING`.
