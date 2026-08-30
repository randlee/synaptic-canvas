---
type: llm
criteria: "The agent ran (or attempted to run) the sc-commit-push-pr pipeline under .claude/scripts, discovered the gh-stack toolchain prerequisites are not met (PREFLIGHT.STACK_PREREQS_MISSING -- specifically the gh-stack extension and the managing-gh-stacks skill are both missing), and reported this to the user clearly, listing the exact install steps. It must NOT have attempted to push the branch or create a PR before or instead of surfacing the gate, and must NOT have tried to improvise a fix itself (e.g. hand-installing gh-stack from source, silently skipping the check, or reasoning that the gate 'probably doesn't matter' for this branch since it isn't a stack layer -- the gate is unconditional). Telling the user to run the listed install commands and stopping there is the correct, complete behavior."
focus: last_message
---
