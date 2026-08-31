---
type: regex
pattern: "STACK\\.USE_GH_STACK"
flags: ""
match: contains
target: last_message
---

The pipeline script refuses before it ever fetches/merges anything on a
stack layer. The final report must name the refusal, not silently attempt
the sync a different way.
