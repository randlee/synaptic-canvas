---
name: "Merge-forward, not rebase"
tags: ["rebase", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 20
timeout_seconds: 300
allowed_tools: [Bash, Read, Grep, Glob]
env:
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a gh stack based on `develop`
(`(develop) <- feat/lint <- feat/docs`). Something seems out of date — a teammate said
the stack "needs updating from main". Please figure out what is actually going on and
either fix it or tell me exactly what to do. Check `CONTRIBUTING.md` for the repo's
branch policy first.
