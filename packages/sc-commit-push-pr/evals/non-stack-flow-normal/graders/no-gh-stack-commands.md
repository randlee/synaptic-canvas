---
type: tool_used
tool: Bash
input_match: "gh stack"
min: 0
max: 0
---

A plain, non-stack branch has no reason to invoke any `gh stack` subcommand.
Reaching for stack tooling here would itself be a (harmless but wrong)
misdiagnosis of the repository state.
