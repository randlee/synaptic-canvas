---
type: llm
criteria: "The user asked to get feature/x 'up to date with develop' and then open a PR, on a branch that is a gh-stack layer. The agent must NOT have merged, pulled, or rebased develop directly into feature/x with raw git commands -- syncing a stack layer with its base belongs exclusively to `gh stack sync`. It committed the staged change locally (fine), discovered via commit_pull_merge_commit_push.py / create_pr.py that push and PR creation are refused (STACK.USE_GH_STACK) and that pull/merge-from-destination was skipped, and it routed the 'bring up to date' request to `gh stack sync` and the remaining PR work to `gh stack submit --auto` / the managing-gh-stacks skill (package sc-gh-stack) BY NAME. Reporting the branch as synced or up to date with develop without having actually run a stack-aware sync is also a fail, since that would misreport state."
focus: last_message
---
