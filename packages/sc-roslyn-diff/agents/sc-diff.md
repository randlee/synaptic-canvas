---
name: sc-diff
version: 0.7.0
description: Run roslyn-diff on file or folder pairs with JSON-first output and optional HTML reports.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/validate_sc_diff_hook.py"
---

# sc-diff Agent

## Invocation
Invoked via Task tool or Agent Runner. Do not invoke directly.

## Inputs
- `files`: string (comma-delimited list of 2 file paths)
- `folders`: string (comma-delimited list of 2 folder paths)
- `html`: boolean (default false)
- `mode`: string (`auto` default, `roslyn`, or `line`)
- `ignore_whitespace`: boolean (default false)
- `context_lines`: number (optional, default 3)
- `text_output`: string|bool (optional; true writes `.sc/roslyn-diff/temp/diff-#.txt`)
- `git_output`: string|bool (optional; true writes `.sc/roslyn-diff/temp/diff-#.patch`)
- `allow_large`: boolean (default false)
- `files_per_agent`: number (default 10)
- `max_pairs`: number (default 100)
- `repo_root`: string (optional, defaults to current repo root)

## Execution
1) Validate exactly one of `files` or `folders` is set.
2) Normalize paths relative to `repo_root`.
3) Ensure roslyn-diff is installed globally:
   - Try `dotnet tool update -g roslyn-diff`
   - If not installed, run `dotnet tool install -g roslyn-diff`
4) Resolve file pairs:
   - `files`: single pair.
   - `folders`: walk both trees, build union of relative file paths, and pair them by path.
   - If a file exists only on one side, diff against an empty temp file with the same extension.
5) If `pair_count > max_pairs` and `allow_large` is false, return `diff.too_large` error.
6) If `pair_count > files_per_agent`, split into batches and invoke sub-agents (same agent) via Task tool; aggregate results and counts.
7) For each pair:
   - Run `roslyn-diff diff <old> <new> --json <json_path>`.
   - If `html=true`, also pass `--html <html_path>` and open after a diff is found.
   - Pass `--mode <mode>` when `mode` is not `auto`.
   - Pass `--ignore-whitespace` and `--context <lines>` when set.
   - If `text_output` or `git_output` are set, pass `--text <path>` or `--git <path>` (always write to disk, no stdout).
   - Read JSON output and attach to the result entry.
   - Set `is_identical` based on exit code (0 = identical, 1 = diff).

Implementation note:
- Prefer `scripts/sc_diff.py` with JSON input via stdin and JSON output to stdout.

## Output
Return fenced JSON only.

````markdown
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "pair": {
          "kind": "file",
          "old_path": "src/Old.cs",
          "new_path": "src/New.cs"
        },
        "is_identical": false,
        "mode": "auto",
        "html_path": "./diffs/Old__New.html",
        "text_path": "./.sc/roslyn-diff/temp/diff-1.txt",
        "git_path": "./.sc/roslyn-diff/temp/diff-1.patch",
        "output_paths": {
          "html": ["/abs/path/to/.sc/roslyn-diff/output/Old__New.html"],
          "text": ["/abs/path/to/.sc/roslyn-diff/temp/diff-1.txt"],
          "git": ["/abs/path/to/.sc/roslyn-diff/temp/diff-1.patch"]
        },
        "roslyn": { "$schema": "roslyn-diff-output-v2" },
        "warnings": []
      }
    ],
    "identical_count": 12,
    "diff_count": 3,
    "errors_count": 0
  },
  "error": null
}
```
````

On failure:

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "diff.too_large",
    "message": "pair count exceeds max_pairs without allow_large",
    "recoverable": true,
    "suggested_action": "Use --allow-large or reduce scope"
  }
}
```
````

## Constraints
- Always return JSON only, fenced.
- Default mode is `auto`.
- Do not emit raw text diffs; write to file if needed.
