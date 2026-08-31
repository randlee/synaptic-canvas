---
type: llm
criteria: "The agent created a worktree for feature/y based on develop and communicated that it IS tracked as a gh-stack (mentions gh stack init, stack tracking, or being part of a stack), because .sc/shared-settings.yaml declares git.always_stack: true. It must NOT describe a plain/flat worktree with no stack involvement, and must NOT describe a refusal or missing-prerequisite error - all prerequisites are present in this fixture."
focus: last_message
---
