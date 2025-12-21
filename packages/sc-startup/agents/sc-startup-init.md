---
name: sc-startup-init
version: 0.6.0
description: Detect existing sc-startup config, suggest defaults, and report installed packages; returns fenced JSON with YAML payload for the skill to drive Q&A.
---

# sc-startup-init

## Purpose
Collect startup configuration signals (existing config, candidate prompt/checklist paths, installed packages) without mutating anything. Return a structured summary so the calling skill can guide the user via AskQuestion.

## Inputs
- `repo_root` (string, required): Absolute path to repo root (path safety anchor).
- `config_path` (string, optional): Repo-root-relative path to config. Default: `.claude/sc-startup.yaml`.
- `readonly` (bool, optional): When true, skip any mutation (this agent never writes anyway; included for clarity).
- `detect_plugins` (bool, optional, default true): Detect installed packages/plugins.

## Execution Steps
1) Validate `repo_root` exists; fail with `VALIDATION.INVALID_REPO` if not. Resolve `config_path` against `repo_root`; reject escapes with `VALIDATION.INVALID_PATH`.
2) If config exists: load YAML, parse keys. On parse failure: `FORMAT.INVALID_YAML`.
3) Detect packages (if `detect_plugins`):
   - Check `.claude-plugin/marketplace.json` for plugins `sc-ci-automation`, `sc-git-worktree`, `sc-startup`.
   - For each, record `installed` (bool) and `version` if present. Optionally confirm `packages/<name>` exists.
4) Suggest candidates (scan `pm/`, `project(s)/`, and repo root; return multiple if found):
   - `startup_prompt_candidates`: glob for `pm/**/*prompt*.md`, `pm/**/*startup*.md`, `pm/**/ARCH-*.md`, `project*/**/*prompt*.md`, `project*/**/*startup*.md`, `README*.md` (bounded max 10).
   - `checklist_candidates`: glob for `pm/**/*checklist*.md`, `project*/**/*checklist*.md`, `**/*checklist*.md` (bounded max 10).
   - Sort candidates by modification time (most recent first) to prioritize active documents.
5) Compute `missing_keys` based on required fields (`startup-prompt`, `check-list`) plus optional flags (`worktree-scan`, `pr-enabled`, `worktree-enabled`).
6) Return fenced JSON with a YAML payload summarizing findings.

## Output Format
Fenced JSON (minimal envelope). `data` contains a YAML string under `yaml` plus structured fields:
```json
{
  "success": true,
  "data": {
    "config_found": true,
    "config_path": ".claude/sc-startup.yaml",
    "config": { "startup-prompt": "pm/ARCH-SC.md", "check-list": "pm/checklist.md" },
    "missing_keys": ["worktree-scan"],
    "plugins": {
      "sc-ci-automation": { "installed": true, "version": "0.6.0" },
      "sc-git-worktree": { "installed": true, "version": "0.6.0" },
      "sc-startup": { "installed": true, "version": "0.6.0" }
    },
    "candidates": {
      "startup_prompt": ["pm/ARCH-SC.md", "pm/startup-prompt.md", "README.md"],
      "checklist": ["pm/checklist.md", "pm/master-checklist.md"]
    },
    "yaml": "startup-prompt: pm/ARCH-SC.md\ncheck-list: pm/checklist.md\nworktree-scan: scan\npr-enabled: true\nworktree-enabled: true\n"
  },
  "error": null
}
```

## Error Handling
- `VALIDATION.INVALID_REPO`: repo_root missing.
- `VALIDATION.INVALID_PATH`: config path escapes repo.
- `VALIDATION.MISSING_CONFIG`: config not found (still success=false; caller can prompt to create).
- `FORMAT.INVALID_YAML`: config parse error.
- `SCAN.IO`: file read failure.
- `DEPENDENCY.MISSING`: only if plugin detection fails due to missing marketplace file.

## Constraints
- No mutations. Detection-only.
- Fenced JSON only; do not call AskQuestion or other user-facing tools.
- Keep globs bounded (e.g., max 10 candidates per category).
