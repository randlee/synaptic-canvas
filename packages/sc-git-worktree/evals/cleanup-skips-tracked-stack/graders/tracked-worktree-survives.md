---
type: regex
pattern: "init"
match: contains
target: { source: file, path: "repo-worktrees/feature/tracked-stack/README.md" }
---

`feature/tracked-stack` carries gh-stack tracking and is merged - batch
cleanup must skip it entirely (per-worktree stack state; only a single-branch
cleanup with explicit approval may remove it). The worktree and its files
must still exist afterward.
