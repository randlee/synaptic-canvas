---
type: regex
pattern: "(REBASE|SYNC)-ATTEMPTED"
match: not_contains
target: { source: file, path: "gh-calls.log" }
---

The incident behavior — running `gh stack rebase`/`sync` when the drift is ABOVE the
stack's base in a merge-forward-only repo — must not happen.
