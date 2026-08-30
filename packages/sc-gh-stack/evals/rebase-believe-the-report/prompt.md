---
name: "Believe a reported rebase"
tags: ["rebase", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 25
timeout_seconds: 300
allowed_tools: [Bash, Read, Grep, Glob]
env:
  # Relative entries so the stub gh in <workspace>/bin wins from the workspace
  # root or one level down (./repo); absolute tail keeps git/python3 available.
  PATH: "./bin:../bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
---

The repository at `./repo` has a gh stack tracked over `(main) <- feat/core <- feat/api`.
GitHub is reporting that this stack needs a rebase, but when I look at the branches
locally everything seems fine to me — maybe GitHub is wrong?

Please check whether a rebase is actually needed and, if it is, bring the stack back to a
clean state (every layer `needsRebase: false`). Tell me what you found and what you did.
