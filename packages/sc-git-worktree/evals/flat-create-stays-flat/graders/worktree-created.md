---
type: regex
pattern: "init"
match: contains
target: { source: file, path: "repo-worktrees/feature/x/README.md" }
---

The worktree must actually land at the standard sibling path
(`<repo>-worktrees/feature/x`, no `stack/` prefix, no separate directory
scheme) - `README.md` there must carry `main`'s content, proving the worktree
was really created and checked out.
