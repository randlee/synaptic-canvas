---
type: tool_used
tool: Bash
input_match: "worktree add[^\\n]*feature/z"
min: 0
max: 0
---

The agent must not fall back to creating a plain flat worktree anyway when
the mandatory stack prerequisites are missing - that would silently violate
the repo's declared always_stack policy. No `git worktree add ... feature/z`
may appear anywhere in the agent's own tool calls.
