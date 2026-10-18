---
name: sc-packages-list
version: 0.14.2
description: Enumerate available Synaptic Canvas packages, detect install scope (no/local/global), and return a machine-readable table.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 scripts/validate_sc_manage_hook.py"
---

# sc-packages-list

## Purpose
List packages and their project/user-global install status for each selected target.

## Inputs (optional)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `SC_REPO_PATH` or repo root.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `~/.claude` (or `GLOBAL_CLAUDE_DIR`).
- `targets`: optional nonempty list of `claude`, `codex`, `cursor`, `hermes`;
  defaults to `["claude"]`.

## Execution
1. Run: `python3 scripts/sc_manage_list.py` with JSON stdin.
2. The script discovers packages by reading `<sc_repo_path>/packages/*/manifest.yaml`.
3. For each manifest, extract:
   - `name`
   - first line of `description`
   - `install.scope` if present: `local-only` | `global-only` | `both` (default `both`)
4. Detect installed state:
   - Local: `<repo_root>/.claude/` has any of the manifest's artifacts (commands/skills/agents/scripts)
   - Global: `<global_claude_dir>/` has any of the manifest's artifacts
5. Return a list ordered by package name with `installed` = `no` | `local` | `global` | `both`.

For non-Claude targets inspect `.<target>` and the selected profile root, using
skills/scripts/assets (Cursor sc-manage may also have `commands/sc-manage.md`).
Return `installed_by_target` for every selected target; `installed` is `mixed`
when their states differ. Do not infer Codex, Cursor or Hermes installation
from files under `.claude`.

## Output

````markdown
```json
{
  "success": true,
  "data": {
    "packages": [
      { "name": "sc-delay-tasks", "installed": "global", "description": "Schedule delayed one-shot or bounded polling actions" },
      { "name": "sc-git-worktree", "installed": "local", "description": "Manage git worktrees with optional tracking" }
    ]
  },
  "error": null
}
```
````

## Error Handling

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LIST_FAILED",
    "message": "Failed to enumerate packages or parse manifests",
    "recoverable": false,
    "suggested_action": "verify sc_repo_path and permissions"
  }
}
```
````

## Constraints
- Do not modify files; read-only operations only.
- Return ONLY fenced JSON.
