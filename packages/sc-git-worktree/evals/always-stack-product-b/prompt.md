---
name: "always_stack policy produces a new stack"
tags: ["create", "decision-model"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` uses gh-stack for everything (see
`.sc/shared-settings.yaml`). Please create a worktree for `feature/y` based on
`develop`, and tell me what happened, including whether it's tracked as a
stack.
