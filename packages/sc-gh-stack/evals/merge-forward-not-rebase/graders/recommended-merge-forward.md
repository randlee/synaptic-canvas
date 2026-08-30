---
type: llm
criteria: "The agent (1) read the merge-forward-only policy, (2) determined that main has a commit develop lacks (drift ABOVE the stack's base) rather than the stack being stale against develop, (3) did NOT run or recommend gh stack rebase/sync for it, and (4) recommended or opened a merge-forward PR (main -> develop) as the fix. Recommending a rebase of any branch onto main, or telling the user the stack itself needs rebasing, is a fail."
focus: last_message
---
