---
name: "Dependent base joins the existing stack as a layer"
tags: ["create", "decision-model"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` already has `feat/bottom` checked out in its own
worktree (`./repo-worktrees/feat/bottom`), tracked as a gh-stack. Please
create a worktree for `feature/next` based on `feat/bottom`, and tell me
where the work ended up.
