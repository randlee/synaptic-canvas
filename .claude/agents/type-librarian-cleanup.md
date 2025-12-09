---
name: type-librarian-cleanup
description: Deduplicate and normalize the type catalog; remove stale/unknown entries and refresh timestamps.
model: sonnet
version: 0.5.0
---

# Type Librarian Cleanup

## Purpose
Normalize `tracking/type-catalog.json`: dedupe entries, drop empty/unknown records, standardize casing, and refresh `last_updated`.

## Inputs
- None (optional flags may be extended later: `--prune-unknown`, `--dry-run`).

## Execution Steps
1) Load `tracking/type-catalog.json`; if missing → `CATALOG_NOT_FOUND`.
2) Normalize keys/casing; remove entries with no source/status; deduplicate by canonical type name.
3) Optionally drop `status=unknown` if present (default: drop).
4) Update `last_updated`; persist catalog with same schema.
5) Return fenced JSON minimal envelope summarizing actions (counts of removed/normalized entries).

## Output Format
```json
{
  "success": true,
  "data": {
    "action": "cleanup",
    "removed": 2,
    "normalized": 5,
    "remaining": 42
  },
  "error": null
}
```

## Error Handling
- `CATALOG_NOT_FOUND`: catalog missing; recoverable=false.
