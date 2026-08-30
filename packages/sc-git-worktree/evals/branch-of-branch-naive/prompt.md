---
name: "Branch-of-branch stays flat in a stack-naive repo"
tags: ["create", "decision-model"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a branch `feat/base` that is not yet merged
into `main`. Please create a worktree for `feature/child` based on
`feat/base`, and tell me where it landed.
