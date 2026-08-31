---
type: regex
pattern: "STACK\\.USE_GH_STACK|PREFLIGHT\\.STACK_PREREQS_MISSING"
flags: "i"
match: not_contains
target: last_message
---

Nothing here should trip either gh-stack gate: the worktree carries no
gh-stack marker and the toolchain prerequisites are all present. Surfacing
either error code on this control case is a fail.
