---
type: regex
pattern: "stack"
flags: "i"
match: not_contains
target: { source: file, path: "gh-calls.log" }
---

The stack-activity probe is the only settings read in a stack-naive repo;
dependency (is the base a layer of unmerged work?) is never evaluated, so
`gh` must never be invoked for anything stack-related.
