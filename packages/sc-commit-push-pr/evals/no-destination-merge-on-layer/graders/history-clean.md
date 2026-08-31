---
type: regex
pattern: "later develop work"
flags: ""
match: not_contains
target: { source: file, path: "repo/develop-later.txt" }
---

`develop-later.txt` (added by the "develop moved on" commit) only lands in
`repo/`'s working tree if something actually merged/pulled/rebased develop
into feature/x. A missing file (the grader treats a non-existent file as not
containing the pattern) proves the layer's tree was never touched by that
operation; a present file with this content is decisive proof a raw sync
happened.
