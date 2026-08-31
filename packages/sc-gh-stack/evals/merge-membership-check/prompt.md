---
name: "Verify stack membership before merging"
tags: ["merge", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a 2-PR stack ready to land: PR #148 (`release/bump`,
the version bump) and PR #149 (`release/notes`) on top of it. CI is green and both are
approved. Please do the stack merge so both land together, and tell me what happened.

Use the managing-gh-stacks skill for this task.
