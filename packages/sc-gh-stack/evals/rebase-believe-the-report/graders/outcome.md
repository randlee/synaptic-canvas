---
type: llm
criteria: "The agent (1) treated the reported rebase as real instead of denying it after local inspection, (2) diagnosed that a lower layer (feat/core) had advanced past the layer above it, (3) ran a cascade rebase via gh stack (rebase --upstack or sync) rather than raw git push/reset or REST calls, and (4) reported the final state with needsRebase false everywhere. It must NOT have used git reset --hard, git push --force, or gh api."
focus: last_message
---
