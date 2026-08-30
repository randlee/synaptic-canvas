---
type: tool_used
tool: Bash
input_match: "worktree add[^\\n]*feature/next"
min: 0
max: 0
---

Product C never creates a new worktree directory for the layer - the new
branch is checked out INSIDE the base's existing stack worktree. No
`git worktree add ... feature/next` invocation may appear anywhere in the
agent's own tool calls.
