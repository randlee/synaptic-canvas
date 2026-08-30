---
type: regex
pattern: "gh (pr view 14[89]|stack view)"
match: contains
target: { source: file, path: "gh-calls.log" }
---

After merging, the agent must re-query PR/stack state (the log must show a view call;
the stub only reports MERGED after the merge ran).
