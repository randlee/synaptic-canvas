---
name: sc-package-docs
version: 0.7.0
description: Locate and return package documentation (README.md) for a given Synaptic Canvas package.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 scripts/validate_sc_manage_hook.py"
---

# sc-package-docs

## Inputs
- `package`: required package name (e.g., sc-delay-tasks, sc-git-worktree)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `SC_REPO_PATH` or repo root.

## Execution
1. Run: `python3 scripts/sc_manage_docs.py` with JSON stdin.
2. The script validates package and returns README path + size.

## Output

````markdown
```json
{
  "success": true,
  "data": { "package": "sc-git-worktree", "readme_path": "/abs/path/packages/sc-git-worktree/README.md", "size_bytes": 2048 },
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
    "code": "README_NOT_FOUND",
    "message": "Package README.md not found",
    "recoverable": false,
    "suggested_action": "ensure README.md exists under the package root"
  }
}
```
````

## Constraints
- Do not inline large README content in the agent response; return only metadata. The skill is responsible for presentation/Q&A.
