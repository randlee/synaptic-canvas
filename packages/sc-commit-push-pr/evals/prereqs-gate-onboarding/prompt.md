---
name: "Missing gh-stack toolchain blocks with install instructions"
tags: ["prereqs", "onboarding", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` is on branch `feature/x` with a staged change ready to go.
Please commit the staged change and open a PR to `develop`.
