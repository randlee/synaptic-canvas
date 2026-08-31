---
type: regex
pattern: "worktrees/stack/"
match: not_contains
target: last_message
---

Product B uses the SAME path a flat worktree would use - no `stack/` prefix
anywhere. The reported path must be the normal `<base>/<branch>` sibling
path, not a special stack directory scheme.
