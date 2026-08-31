---
type: llm
criteria: "The agent discovered (via commit_pull_merge_commit_push.py and/or create_pr.py under .claude/scripts, run against the real repo) that feature/x is a gh-stack layer and that push/PR creation is refused with STACK.USE_GH_STACK. It committed the staged change locally (that part is fine and expected -- commit stays normal on a stack layer) but did NOT push feature/x directly and did NOT create a PR directly. It accurately reported the state as committed-but-not-pushed (not as failed, not as fully done). It routed the remaining work to `gh stack submit --auto` and/or the managing-gh-stacks skill (package sc-gh-stack) BY NAME -- it must not just say 'use a different tool' vaguely, it must name gh stack / managing-gh-stacks specifically. It must NOT have worked around the refusal with a raw `git push` or `gh pr create`, and must NOT have reported the PR as opened when it was not."
focus: last_message
---
