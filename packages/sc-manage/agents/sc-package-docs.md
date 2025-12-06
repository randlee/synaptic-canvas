---
name: sc-package-docs
version: 0.5.0
description: Locate and return package documentation (README.md) for a given Synaptic Canvas package.
model: sonnet
color: blue
---

# sc-package-docs

## Inputs
- `package`: required package name (e.g., delay-tasks, sc-git-worktree)
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `/Users/randlee/Documents/github/synaptic-canvas`.

## Execution
1. Resolve package directory at `<sc_repo_path>/packages/<package>`.
2. Read `README.md` from the package directory, if present.
3. Return a summary JSON with the path and size in bytes. The skill will present the document and handle Q&A.

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
    "code": "DOC_NOT_FOUND",
    "message": "Package README.md not found",
    "recoverable": false,
    "suggested_action": "ensure README.md exists under the package root"
  }
}
```
````

## Constraints
- Do not inline large README content in the agent response; return only metadata. The skill is responsible for presentation/Q&A.
