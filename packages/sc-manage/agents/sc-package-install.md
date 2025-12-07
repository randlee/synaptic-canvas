---
name: sc-package-install
version: 0.5.1
description: Install a Synaptic Canvas package locally (repo .claude) or globally according to package policy.
model: sonnet
color: blue
---

# sc-package-install

## Inputs
- `package`: required package name (e.g., sc-delay-tasks, sc-git-worktree)
- `scope`: required `local` | `global` (ask if missing)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `/Users/randlee/Documents/github/synaptic-canvas`.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `/Users/randlee/Documents/.claude`.

## Execution
1. Validate `package` exists under `<sc_repo_path>/packages/`.
2. Read its manifest.yaml. If `install.scope: local-only` and `scope=global`, return error.
3. Resolve destination:
   - Local: `<repo_root>/.claude` (detect via `git rev-parse --show-toplevel`)
   - Global: `<global_claude_dir>`
4. Run installer:
   ```
   python3 <sc_repo_path>/tools/sc-install.py install <package> --dest <dest>
   ```
5. Return JSON summary.

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
