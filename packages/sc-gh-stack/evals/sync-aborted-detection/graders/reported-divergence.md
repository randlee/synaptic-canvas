---
type: regex
pattern: "diverg|abort"
flags: "i"
match: contains
target: last_message
---

The final report must say the sync did not happen (diverged / aborted), not that the
stack is synced.
