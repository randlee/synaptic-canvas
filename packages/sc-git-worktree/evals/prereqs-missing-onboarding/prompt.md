---
name: "Missing stack prerequisites route to onboarding, never improvise"
tags: ["create", "decision-model", "refusal"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` declares `git.always_stack: true` in
`.sc/shared-settings.yaml`. Please create a worktree for `feature/z` based on
`develop`, and let me know if that works.

Run every command in the foreground; never run commands or tasks in the background.
