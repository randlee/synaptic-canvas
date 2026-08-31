---
type: regex
pattern: "stack init --base develop"
match: contains
target: { source: file, path: "gh-calls.log" }
---

Product B must adopt the new branch into gh-stack with
`gh stack init --base develop feature/y` inside the new worktree, after the
prerequisite gate (gh CLI, extension, managing-gh-stacks skill) already
passed.
