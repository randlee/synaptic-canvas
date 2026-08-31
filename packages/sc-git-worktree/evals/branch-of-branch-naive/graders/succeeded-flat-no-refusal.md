---
type: llm
criteria: "The agent successfully created a worktree for feature/child based on feat/base, an unmerged branch. It must NOT have refused, asked for a `flat: true` override, warned that a new stack was needed, or treated the unmerged base as a dependency signal in any way - this repo is stack-naive (no always_stack policy, no worktree anywhere carries gh-stack tracking), so a branch-of-branch create must behave exactly as it did before gh-stack support existed (the distribution guarantee / auto-upgrade for legacy prompts)."
focus: last_message
---
