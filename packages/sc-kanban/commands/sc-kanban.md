---
name: sc-kanban
version: 0.9.0
description: Interact with the kanban state machine (backlog → board → done)
---

# /kanban

## Summary
Interact with the kanban state machine (backlog → board → done) using the shared board config (`.project/board.config.yaml`).

## Usage
- `/kanban query [--status planned|active|review|done] [--sprint <id>]`
- `/kanban transition --card <worktree|sprint_id> --status planned|active|review|done`

## Agents
- `kanban-query`
- `kanban-transition`

## Notes
- Requires valid board config (v0.7) and access to backlog.json/board.json/done.json in the repo.
- When `provider=checklist`, command should delegate to checklist agent instead of running gates.
