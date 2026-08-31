---
type: tool_used
tool: Bash
input_match: "worktree remove[^\\n]*tracked-stack"
min: 0
max: 0
---

No `git worktree remove ... feature/tracked-stack` (or equivalent branch
deletion targeting it) may appear anywhere in the agent's own tool calls -
the gh-stack marker must stop the removal before it is attempted, not be
caught only in the report.
