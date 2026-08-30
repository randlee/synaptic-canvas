---
type: regex
pattern: "stack"
flags: "i"
match: not_contains
target: { source: file, path: "gh-calls.log" }
---

Product A never invokes `gh` for stacking at all (the stack-activity probe is
the only settings read; a stack-naive repo never reaches the prerequisite
gate or dependency/policy stages). `gh-calls.log` must not contain any
`stack` invocation.
