---
type: regex
pattern: "DIRECT-PR-CREATE-WORKAROUND"
flags: ""
match: not_contains
target: { source: file, path: "gh-calls.log" }
---

The stub logs `DIRECT-PR-CREATE-WORKAROUND` if `gh pr create` actually runs.
That call must never happen on this stack layer -- catches a workaround even
if it's buried inside a script invocation rather than a bare Bash command.
