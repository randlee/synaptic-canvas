---
type: tool_used
tool: Bash
input_match: "merge (origin/)?develop|pull( +--[a-z-]+)* +origin +develop|rebase (origin/)?develop"
min: 0
max: 0
---

Getting a stack layer "up to date with develop" must never be a raw
`git merge`/`git pull`/`git rebase` of develop into the layer -- that is
`gh stack sync`'s job and a plain merge here would corrupt the stack. This
must never appear as a Bash command the agent runs directly.
