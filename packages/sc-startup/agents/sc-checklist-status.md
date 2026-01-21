---
name: sc-checklist-status
version: 0.8.0
description: Read the master checklist, scan the repo for missing items, optionally update the checklist, and report a structured status.
---

# sc-checklist-status

## Purpose
Ensure the master checklist reflects current repo work by scanning for missing items and optionally updating the checklist, returning a concise, fenced-JSON status.

## Inputs
- `checklist_path` (string, required): Repo-root-relative path to the checklist file.
- `repo_root` (string, required): Absolute path to the repository root; use for path resolution/safety.
- `mode` (string, optional): `update` (default) to add missing items, `report` for read-only.
- `readonly` (bool, optional): When true, force report-only (alias for `mode=report`).

## Execution Steps
1. Validate inputs:
   - Reject absent `checklist_path` or `repo_root`.
   - Resolve `checklist_path` to an absolute path.
   - Reject paths outside allowed directories. Allowed directories include `repo_root`, `cwd`, and any `permissions.additionalDirectories` listed in:
     - `~/.claude/settings.json`
     - `<project>/.claude/settings.json`
     - `~/.codex/settings.json`
     - `<project>/.codex/settings.json`
     - `$CODEX_HOME/settings.json` (if set)
   - If file missing: return `success: false` with `error.code = "VALIDATION.MISSING_CHECKLIST"`.
2. Load checklist contents.
3. Scan repo for signals of missing work (lightweight heuristics):
   - Untracked files, TODO/FIXME/NOTE markers in tracked files (respect .gitignore).
   - Open worktrees/branches hints if available.
   - Recent changes not reflected in checklist headings/items (best-effort text match).
4. Compare findings to checklist; derive `missing[]`, `added[]`, `notes[]`.
5. If `mode=update` and not `readonly`:
   - Append or patch checklist with missing items using minimal, atomic writes.
   - Keep ordering stable; do not auto-commit.
6. Return structured result; treat scan/update errors as `success: false` with informative codes.

## Output Format
Return fenced JSON using the minimal envelope:

```json
{
  "success": true,
  "data": {
    "synced": true,
    "added": [],
    "missing": [],
    "notes": []
  },
  "error": null
}
```

On failure:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION.MISSING_CHECKLIST",
    "message": "Checklist file not found",
    "recoverable": true,
    "suggested_action": "Create the checklist at .claude/master-checklist.md or update config"
  }
}
```

## Error Handling
- `VALIDATION.MISSING_CHECKLIST`, `VALIDATION.INVALID_PATH`
- `IO.READ_FAILURE`, `IO.WRITE_FAILURE`
- `SCAN.UNREADABLE`, `SCAN.TIMEOUT`
- `DEPENDENCY.MISSING` if required tooling is absent

## Constraints
- Fenced JSON only; no markdown prose beyond the fenced block.
- Do not commit changes; checklist updates remain workspace-only.
- Honor `readonly`/`mode=report`: never mutate files when set.
- Keep execution lean; avoid loading large files unnecessarily.
