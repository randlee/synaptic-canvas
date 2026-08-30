---
type: llm
criteria: "The agent (1) confirmed stack membership (#148 and #149 both tracked, in order) via gh stack view --json BEFORE merging, (2) merged via gh stack merge (never gh pr merge or REST), (3) after merging, verified BOTH PRs report MERGED and that main actually carries VERSION 0.6.0 (e.g. git show origin/main:VERSION or fetching and reading the file), and (4) only then reported success, stating 0.6.0 is on main. Reporting success without the post-merge verification, or without checking VERSION on main, is a fail. Efficiency counts: the core flow should be roughly view -> merge -> verify, not long exploratory polling."
focus: last_message
---
