---
type: regex
pattern: "on-base"
match: contains
target: { source: file, path: "repo-worktrees/feature/child/base.txt" }
---

The worktree must land at the standard sibling path
(`repo-worktrees/feature/child`) and actually be checked out from
`feat/base` - `base.txt` there must carry `feat/base`'s content. An unmerged
base must not block or redirect a stack-naive create.
