---
name: "Release stack shape"
tags: ["plan", "field-incident"]
model: claude-haiku-4-5-20251001
runs: 2
max_turns: 10
timeout_seconds: 180
allowed_tools: [Skill, Read, Grep, Glob]
---

I'm cutting release 0.6.0. The flow is: the branch `release/0.6.0` (version bump +
changelog) must land in `develop`, and then `develop` must land in `main`. Both `develop`
and `main` are protected branches with required CI.

My plan: make a two-layer gh stack — bottom layer the `release/0.6.0 -> develop` PR, top
layer the `develop -> main` PR — and land the whole thing with one `gh stack merge --yes`.

Is that the right shape? If not, what should I do instead?
