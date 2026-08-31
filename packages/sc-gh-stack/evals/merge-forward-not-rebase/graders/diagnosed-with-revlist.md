---
type: tool_used
tool: Bash
input_match: "rev-list|merge-base|log .*develop.*main|log .*main.*develop"
min: 1
---

Must actually diagnose where the drift is (e.g. `git rev-list --count develop..main`)
before recommending anything.
