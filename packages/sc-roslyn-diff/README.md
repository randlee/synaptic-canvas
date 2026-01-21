# sc-roslyn-diff

Semantic diffing for .NET source using roslyn-diff with JSON-first outputs, HTML reports, and git/PR-aware comparisons.

## What you get

- `/sc-diff` command for file or folder diffs
- JSON-first output for AI processing (always)
- Optional HTML reports per pair
- Git/PR diff agent for GitHub and Azure DevOps
- Smart batching for large diffs

## Install

```bash
aic plugin add sc-roslyn-diff
```

## Command

```bash
/sc-diff <description of files/folders to diff> [options]
```

Options:
- `--help` show usage
- `--files` comma-delimited list of two file paths
- `--folders` comma-delimited list of two folder paths
- `--html` generate HTML report and open it if differences are found
- `--mode` diff mode: `auto` (default), `roslyn`, `line`
- `--ignore-whitespace` ignore whitespace-only changes
- `--context` number of context lines for line diffs (default 3)
- `--text` write plain text diff to `.sc/roslyn-diff/temp/diff-#.txt` (or path if provided)
- `--git` write unified diff patch to `.sc/roslyn-diff/temp/diff-#.patch` (or path if provided)
- `--allow-large` allow large batches above the default cap
- `--files-per-agent` split batches across agents (default 10)

Notes:
- Exactly one of `--files` or `--folders` is required.
- Output is always JSON from roslyn-diff; text/git formats can be written to disk if needed.

## Skill

Use the `sc-diff` skill for orchestration. It delegates to:
- `sc-diff` agent: file/folder diffing with roslyn-diff
- `sc-git-diff` agent: git/PR-based diffs (GitHub + Azure DevOps)

## Caching

Repository-specific settings are stored in:

```
.sc/roslyn-diff/settings.json
```

This is used to cache resolved Azure DevOps org/project/repo details and defaults like `files_per_agent`.

HTML reports are written under:

```
.sc/roslyn-diff/output/
```

## Requirements

- `dotnet` 10+
- `roslyn-diff` 0.7.0 (`dotnet tool install -g roslyn-diff --version 0.7.0`)
- `git` 2.20+
- `python` 3.10+
- `az` CLI for Azure PR diffs (optional)

## Output contract

Agents always return fenced JSON using a discriminated union:

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
        "roslyn": {
          "$schema": "roslyn-diff-output-v2",
          "summary": { "totalChanges": 3 }
        },
        "output_paths": {
          "html": ["/abs/path/to/.sc/roslyn-diff/output/Old__New.html"],
          "text": [],
          "git": []
        },
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

## Security

- Default diff mode is `auto` (semantic for .cs/.vb, line diff otherwise).
- Large batches require `--allow-large` and will be split across agents.
- Read-only file operations; no modifications to source files.
- Local processing only; no external service calls for diff computation.
