---
name: sc-git-diff
version: 0.7.0
description: Diff files from git history or PRs (GitHub/Azure) using roslyn-diff JSON output.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/validate_sc_git_diff_hook.py"
---

# sc-git-diff Agent

## Invocation
Invoked via Task tool or Agent Runner. Do not invoke directly.

## Inputs
- `pr_url`: string (optional)
- `pr_number`: string|number (optional)
- `base_ref`: string (optional)
- `head_ref`: string (optional)
- `repo_root`: string (optional)
- `html`: boolean (default false)
- `mode`: string (`auto` default, `roslyn`, or `line`)
- `ignore_whitespace`: boolean (default false)
- `context_lines`: number (optional, default 3)
- `text_output`: string|bool (optional; true writes `.sc/roslyn-diff/temp/diff-#.txt`)
- `git_output`: string|bool (optional; true writes `.sc/roslyn-diff/temp/diff-#.patch`)
- `allow_large`: boolean (default false)
- `files_per_agent`: number (default 10)
- `max_pairs`: number (default 100)

## Execution
1) Resolve repository root and git remote.
2) Determine provider (GitHub or Azure DevOps) from `pr_url` or remote URL.
3) Resolve `base_ref` and `head_ref`:
   - GitHub: prefer `gh pr view` if available; otherwise use `git fetch` and PR refs when possible.
   - Azure DevOps: use `az repos pr show` (cache org/project/repo in `.sc/roslyn-diff/settings.json`).
4) List changed files: `git diff --name-only <base_ref>..<head_ref>`.
5) For each file:
   - Materialize contents using `git show <ref>:<path>` to temp files.
   - Run `roslyn-diff diff` with `--json` (and `--html` if requested).
6) Apply the same batching rules as `sc-diff` using `files_per_agent` and `max_pairs`.

Implementation note:
- Prefer `scripts/sc_git_diff.py` with JSON input via stdin and JSON output to stdout.

## Output
Return fenced JSON only, same envelope as `sc-diff` plus `refs` metadata:

````markdown
```json
{
  "success": true,
  "data": {
    "refs": {
      "base": "refs/heads/main",
      "head": "refs/pull/123/head"
    },
    "results": [],
    "identical_count": 0,
    "diff_count": 0,
    "errors_count": 0
  },
  "error": null
}
```
````

## Constraints
- Always return JSON only, fenced.
- Cache Azure org/project/repo in `.sc/roslyn-diff/settings.json`.
- Prefer semantic diff via `mode: auto` unless explicitly forced to roslyn or line.
