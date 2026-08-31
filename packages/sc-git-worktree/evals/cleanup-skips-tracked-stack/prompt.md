---
name: "Batch cleanup skips gh-stack-tracked worktrees"
tags: ["cleanup", "decision-model", "safety"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has two worktrees: `feature/tracked-stack` and
`feature/merged-plain`. Please clean up all merged worktrees and tell me what
happened.

Invoke the sc-git-worktree skill and use its packaged scripts (.claude/scripts/worktree_*.py) — do not improvise raw git worktree commands.

Run every command in the foreground; never run commands or tasks in the background.
