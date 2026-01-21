---
name: sc-diff
description: Semantic diff command using roslyn-diff for files, folders, and git/PR comparisons.
version: 0.8.0
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
  - name: --mode
    args:
      - name: mode
        description: Diff mode (auto, roslyn, line).
    description: Choose diff mode (defaults to auto).
  - name: --ignore-whitespace
    description: Ignore whitespace-only changes.
  - name: --context
    args:
      - name: lines
        description: Line diff context count (default 3).
    description: Set line diff context.
  - name: --text
    args:
      - name: path
        description: Optional text diff output path (defaults to .sc/roslyn-diff/temp/diff-#.txt).
    description: Write a plain text diff to disk.
  - name: --git
    args:
      - name: path
        description: Optional git diff output path (defaults to .sc/roslyn-diff/temp/diff-#.patch).
    description: Write a unified diff patch to disk.
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
