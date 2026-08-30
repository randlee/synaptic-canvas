---
type: llm
criteria: "The agent correctly determined feat/bottom is a dependent (unmerged) base that already has a tracked gh-stack worktree, and joined feature/next into that EXISTING worktree (./repo-worktrees/feat/bottom) as a new layer rather than creating a separate worktree for feature/next. The final message must name the existing stack worktree as where the work now lives (e.g. that feature/next is checked out inside repo-worktrees/feat/bottom). It must NOT claim a new worktree directory was created for feature/next, and must NOT refuse the request."
focus: last_message
---
