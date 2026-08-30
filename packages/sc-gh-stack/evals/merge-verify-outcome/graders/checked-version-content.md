---
type: tool_used
tool: Bash
input_match: "show (origin/)?main:VERSION"
min: 1
---

Post-merge verification must read the target branch's CONTENT (git show
origin/main:VERSION), not infer from commit history.
