---
name: "Merge and verify atomically"
tags: ["merge", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a 2-PR release stack ready to land: PR #148
(`release/bump`, sets VERSION to 0.6.0) at the bottom and PR #149 (`release/notes`) on
top. CI is green and both are approved. Land the stack and confirm the release actually
happened — I need to know `main` really carries 0.6.0 before I tag.
