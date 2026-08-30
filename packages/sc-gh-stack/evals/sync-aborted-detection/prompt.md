---
name: "Detect exit-0 Sync aborted"
tags: ["sync", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a gh stack over `(main) <- feat/one <- feat/two`. Trunk
may have moved — please sync the stack so everything is rebased and pushed, and report
the final per-branch state.
