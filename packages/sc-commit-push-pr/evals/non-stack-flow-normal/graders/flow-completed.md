---
type: regex
pattern: "PR-CREATED"
flags: ""
match: contains
target: { source: file, path: "gh-calls.log" }
---

The stub logs `PR-CREATED` when `gh pr create` actually runs. On an ordinary
non-stack branch with prerequisites satisfied, the flow must complete end to
end: commit, push, and PR creation -- no refusal.
