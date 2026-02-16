---
name: kanban-transition
version: 0.9.0
description: Move kanban cards across backlog/board/done with gates and scrubbing.
---

# kanban-transition Agent

## Role
- Apply transitions (planned→active→review→done) using shared board config.
- Enforce gates (pr_url, WIP now; PR/worktree/git via run_gates in v0.7.1).
- Scrub rich fields when moving to done.

## Inputs
- `card_selector`: worktree or sprint_id
- `target_status`: planned|active|review|done
- `config_path`: path to `.project/board.config.yaml`
- `base_dir`: directory holding backlog.json/board.json/done.json
- `gates` (optional): payload for run_gates (`worktrees`, `prs`)

## Behavior
1) Load board config (fail closed if invalid).  
2) If `provider=checklist`, return advisory error (`PROVIDER.CHECKLIST`).  
3) If `provider=kanban`:
   - WIP enforcement using config per-column limits.
   - Minimal gate: require `pr_url` before review/done.
   - Optional: if `gates` provided, invoke `scripts/run_gates.py`; on failure, return `GATE.FAILURES` with failed_gates metadata.  
   - Move card using `sc_kanban.board.transition_card` (includes scrubbing on done).  
4) Return fenced JSON envelope (v0.5) with updated card or gate failures.

## Output (success example)
```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "card": {
      "sprint_id": "1.1",
      "title": "Setup",
      "pr_url": "https://github.com/org/repo/pull/1",
      "completed_at": "2025-12-22T18:00:00Z",
      "actual_cycles": 2
    }
  },
  "error": null,
  "metadata": {
    "tool_calls": [],
    "duration_ms": 0
  }
}
```

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
    "suggested_action": "Invoke checklist-agent/query-update with same card selector"
  }
}
```
