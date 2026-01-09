# Checklist Agent Contract (fallback provider)

**Purpose:** Provide checklist-backed task tracking when `provider=checklist` is set in `.project/board.config.yaml`, using the same fenced JSON envelope but a simpler storage model (roadmap.md + ephemeral prompts) rather than backlog/board/done JSON files.

## Inputs
- `action`: `query` | `transition`
- `roadmap_path`: path to `roadmap.md`
- `prompts_dir`: path to `prompts/` directory for ephemeral per-sprint prompts
- `card`: object with lean fields (e.g., `worktree`, `sprint_id`, `title`, `assignee`, `pr_url`)
- `target_column` (for transitions): column id from `board.columns`

## Behavior
- `query`: return card list/status mapped from the checklist file; must include per-card fields and current column.
- `transition`: update card column and persist checklist representation; enforce nothing beyond basic existence checks (kanban gates not applied in this provider).
- Create/update ephemeral prompt files under `prompts/<sprint_id>.md` when entering active/review to hold temporary instructions for scrum-master; these are not stored in cards.
- If the checklist file or schema is invalid, return `success=false` with `error` populated and `suggested_action`.

## Output Envelope (v0.5 fenced JSON)
```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "cards": [
      {
        "id": "worktree:main/1-1-project-setup",
        "column": "active",
        "fields": {
          "worktree": "main/1-1-project-setup",
          "pr_url": null,
          "assignee": "dotnet-dev"
        }
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

## Error Shape
```json
{
  "success": false,
  "canceled": false,
  "aborted_by": null,
  "data": null,
  "error": {
    "code": "CHECKLIST.INVALID_SCHEMA",
    "message": "cards.fields ids must be unique",
    "recoverable": false,
    "suggested_action": "Fix .project/board.config.yaml and retry"
  }
}
```
