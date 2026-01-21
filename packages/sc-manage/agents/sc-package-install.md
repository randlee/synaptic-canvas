---
name: sc-package-install
version: 0.8.0
description: Install a Synaptic Canvas package locally (repo .claude) or globally according to package policy.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 scripts/validate_sc_manage_hook.py"
---

# sc-package-install

## Inputs
- `package`: required package name (e.g., sc-delay-tasks, sc-git-worktree)
- `scope`: required `local` | `project` | `global` | `user` (ask if missing)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `SC_REPO_PATH` or repo root.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `~/.claude` (or `GLOBAL_CLAUDE_DIR`).
- `user_claude_dir`: absolute path to the user `.claude`. Default: `~/.claude` (or `USER_CLAUDE_DIR`).

## Execution
1. Run: `python3 scripts/sc_manage_install.py` with JSON stdin.
2. The script validates package, scope, and install policy.
3. The script resolves destination and runs `tools/sc-install.py`.
4. Return JSON summary.

## Output

````markdown
```json
{
  "success": true,
  "data": { "package": "sc-git-worktree", "scope": "local", "dest": "/path/to/repo/.claude" },
  "error": null
}
```
````

## Errors

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SCOPE_NOT_ALLOWED",
    "message": "Package 'sc-git-worktree' may only be installed locally",
    "recoverable": false,
    "suggested_action": "use --local scope"
  }
}
```
````

## Constraints
- Do not attempt to install outside `.claude` directories.
- Do not echo secrets; return JSON only.
