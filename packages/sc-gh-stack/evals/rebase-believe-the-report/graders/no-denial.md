---
type: regex
pattern: "(no rebase (is )?(needed|necessary|required))|(does ?n[o']t (actually )?need (a |to )?rebase)|(github (is|was) wrong)"
flags: "i"
match: not_contains
target: last_message
---

The field incident: the agent denied a rebase that gh had reported. The final message
must never claim no rebase was needed or that GitHub was wrong.
