---
type: llm
criteria: "The agent's final report distinguishes the two worktrees: feature/merged-plain was cleaned up normally (worktree and branches removed), while feature/tracked-stack was explicitly skipped/preserved because it carries gh-stack tracking (per-worktree stack state that batch cleanup must not silently remove). It must NOT claim both were cleaned up, and must NOT claim feature/tracked-stack was removed."
focus: last_message
---
