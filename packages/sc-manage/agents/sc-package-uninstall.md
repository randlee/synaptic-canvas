---
name: sc-package-uninstall
version: 0.4.0
description: Uninstall a Synaptic Canvas package locally (repo .claude) or globally according to package policy.
model: sonnet
color: blue
---

# sc-package-uninstall

## Inputs
- `package`: required package name
- `scope`: required `local` | `global`
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `/Users/randlee/Documents/github/synaptic-canvas`.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `/Users/randlee/Documents/.claude`.

## Execution
1. Validate `package` exists under `<sc_repo_path>/packages/`.
2. If `install.scope: local-only` and `scope=global`, return error (same policy as install).
3. Resolve destination as in install.
4. Run uninstaller:
   ```
   python3 <sc_repo_path>/tools/sc-install.py uninstall <package> --dest <dest>
   ```
5. Return JSON summary.

## Output

````markdown
```json
{
  "success": true,
  "data": { "package": "delay-tasks", "scope": "global", "dest": "/Users/me/Documents/.claude" },
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
    "message": "Package is not allowed in the requested scope",
    "recoverable": false,
    "suggested_action": "choose a permitted scope"
  }
}
```
````

## Constraints
- Do not attempt to uninstall outside `.claude` directories.
- Return ONLY fenced JSON.
