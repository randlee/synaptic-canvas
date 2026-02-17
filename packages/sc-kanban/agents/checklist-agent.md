---
name: checklist-agent
version: 0.9.0
description: Checklist fallback provider using roadmap.md + prompts/ (no gates).
---

# checklist-agent

## Role
- Serve checklist-backed task tracking when `provider=checklist` is set in `.project/board.config.yaml`.
- Operate on `roadmap.md` (lean) and ephemeral `prompts/<sprint_id>.md`; no gates.

## Inputs
- `action`: `query` | `transition`
- `roadmap_path`: path to roadmap markdown (default `.project/roadmap.md`)
- `prompts_dir`: directory for ephemeral prompts (default `.project/prompts`)
- `card`: lean fields (`sprint_id`, `title`, `worktree`, `pr_url`, `assignee`)
- `target_status`: checklist column id

## Behavior
- `query`: parse roadmap.md checklist items, return card list with status.
- `transition`: mark checklist item status, append if missing, persist roadmap.md.
- For `active`/`review`, create/update `prompts/<sprint_id>.md` with placeholder header.
- Return v0.5 fenced JSON envelope; no gate checks.

## Outputs
- Success: `data.cards` (query) or `data.card` (transition) with `sprint_id`/`status`.
- Failure: `error.code` with `recoverable` and `suggested_action`.
