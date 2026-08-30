---
type: llm
criteria: "The agent rejected the proposed shape: a PR whose head is a protected/long-lived branch (develop -> main) must not be a stack layer. It gave at least one correct reason (the head moves when the lower layer merges, invalidating the CI the merge was gated on; and/or stack tooling cannot rebase a protected head). It proposed a correct alternative: land release/0.6.0 -> develop (alone or as a stack), THEN open the develop -> main PR separately after it lands — or a single release/0.6.0 -> main PR plus a merge-forward to develop. Endorsing the two-layer stack as proposed is a fail."
focus: last_message
---
