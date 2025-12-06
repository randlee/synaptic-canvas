---
name: sc-packages-list
version: 0.5.0
description: Enumerate available Synaptic Canvas packages, detect install scope (no/local/global), and return a machine-readable table.
model: sonnet
color: blue
---

# sc-packages-list

## Purpose
List available packages and detect whether each is installed locally (current repo .claude) or globally.

## Inputs (optional)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `/Users/randlee/Documents/github/synaptic-canvas`.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `/Users/randlee/Documents/.claude`.

## Execution
1. Discover packages by reading `<sc_repo_path>/packages/*/manifest.yaml`.
2. For each manifest, extract:
   - `name`
   - first line of `description`
   - `install.scope` if present: `local-only` | `global-only` | `both` (default `both`)
3. Detect installed state:
   - Local: `<repo_root>/.claude/` has any of the manifest's artifacts (commands/skills/agents/scripts)
   - Global: `<global_claude_dir>/` has any of the manifest's artifacts
4. Return a list ordered by package name with `installed` = `no` | `local` | `global` | `both`.

## Output

````markdown
```json
{
  "success": true,
  "data": {
    "packages": [
      { "name": "delay-tasks", "installed": "global", "description": "Schedule delayed one-shot or bounded polling actions" },
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
