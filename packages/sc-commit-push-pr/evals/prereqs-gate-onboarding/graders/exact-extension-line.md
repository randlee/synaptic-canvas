---
type: regex
pattern: "gh extension install github/gh-stack"
flags: ""
match: contains
target: last_message
---

The missing gh-stack extension must produce this exact install command, not a
paraphrase -- the user should be able to copy-paste it.
