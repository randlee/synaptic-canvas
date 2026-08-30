---
type: tool_used
tool: Bash
input_match: "merged-plain"
min: 1
---

`feature/merged-plain` carries no gh-stack tracking and is merged - it must
be handled by the normal auto-cleanup path (worktree removed, local branch
deleted, remote branch deleted since nothing is unpulled).
