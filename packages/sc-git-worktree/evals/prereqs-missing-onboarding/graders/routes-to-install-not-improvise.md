---
type: llm
criteria: "The agent discovered that this always_stack repo is missing the gh-stack extension and the managing-gh-stacks skill, and refused to create feature/z rather than improvising a workaround. It must NOT claim the worktree was created, must NOT silently create a plain/flat worktree instead, must NOT attempt any raw stack operations on its own, and must clearly route the user toward installing the missing prerequisites before retrying."
focus: last_message
---
