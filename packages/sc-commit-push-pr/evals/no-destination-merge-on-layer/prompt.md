---
name: "Never merge develop into a stack layer to 'sync' it"
tags: ["stack", "sync", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` is on branch `feature/x` with a staged change ready to go.
`develop` has moved on since I branched. Please commit and get my branch up to date
with `develop`, then open a PR.
