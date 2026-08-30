---
type: regex
pattern: "stack add feature/next"
match: contains
target: { source: file, path: "gh-calls.log" }
---

The new layer must be adopted into the existing stack with
`gh stack add feature/next`, run inside the base's stack worktree.
