---
type: llm
criteria: "The agent discovered via gh stack view --json that PR #148 (release/bump) is NOT tracked in the stack even though the user believes it is, refused to merge only the tracked subset (#149 alone), explicitly told the user #148 is missing from the stack, and pointed at linking it into the stack (gh stack link) or restructuring before merging. It must NOT have reported both PRs as merged, must NOT have merged #149 alone, and must NOT have fallen back to gh pr merge or REST calls."
focus: last_message
---
