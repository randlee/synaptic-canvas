---
name: sc-diff
description: Semantic diff command using roslyn-diff for files, folders, and git/PR comparisons.
version: 0.7.0
options:
  - name: --help
    description: Show usage and options.
  - name: --files
    args:
      - name: paths
        description: Comma-delimited list of two file paths.
    description: Compare two files.
  - name: --folders
    args:
      - name: paths
        description: Comma-delimited list of two folder paths.
    description: Compare two folders.
  - name: --html
    description: Generate and open HTML report if differences are found.
  - name: --roslyn
    description: Prefer semantic diff (default; auto fallback for non-.NET).
  - name: --line
    description: Force line-by-line diff.
  - name: --allow-large
    description: Allow batches above the default cap.
  - name: --files-per-agent
    args:
      - name: count
        description: Max pairs per agent (default 10).
    description: Split large batches across agents.
---

# /sc-diff

Use the `sc-diff` skill to orchestrate roslyn-diff comparisons.

Examples:
- `/sc-diff compare old/new --files ./old.cs,./new.cs`
- `/sc-diff compare folders --folders ./before,./after --html`
