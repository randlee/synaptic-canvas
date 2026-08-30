---
type: regex
pattern: "/plugin install sc-gh-stack"
flags: ""
match: contains
target: last_message
---

The missing managing-gh-stacks skill must surface this exact plugin-install
command (from `stack_guard.missing_prereq_actions()`), not a vague "install
the stack skill somehow."
