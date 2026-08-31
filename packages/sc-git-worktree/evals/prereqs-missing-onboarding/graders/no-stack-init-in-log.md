---
type: regex
pattern: "stack init|stack add"
flags: "i"
match: not_contains
target: { source: file, path: "gh-calls.log" }
---

The mandatory prerequisite gate must refuse BEFORE any mutation - no
`gh stack init` or `gh stack add` may ever run when prerequisites are
missing.
