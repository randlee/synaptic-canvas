---
type: tool_used
tool: Bash
input_match: "checkout -b feature/next"
min: 1
---

The new branch must be created via `git checkout -b feature/next` run inside
the base's existing stack worktree (`./repo-worktrees/feat/bottom`), not via
a fresh `git worktree add`.
