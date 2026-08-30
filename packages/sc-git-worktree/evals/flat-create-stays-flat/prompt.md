---
name: "Flat create stays flat"
tags: ["create", "decision-model"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` doesn't use any stacked-PR workflow. Please create a
worktree for `feature/x` based on `main`, and tell me where it landed.
