---
name: sc-gh-stack-view
description: Print the one-call coherence, mergeability, CI and LANDING table for every open gh stack (read-only). Paste the script output verbatim.
version: 0.2.0
options:
  - name: --trunk
    description: Only stacks whose trunk is this branch (e.g. develop, integrate/phase-bc).
  - name: --phase
    description: Shorthand for --trunk integrate/phase-<PHASE>.
  - name: --all
    description: Show every stack, including merged/closed ones.
  - name: --no-fetch
    description: Forbid git fetch; qualify remote-tracking freshness.
  - name: --no-pr
    description: Forbid GitHub API calls, including numeric identifier resolution.
  - name: --remote
    description: Select the git remote (default origin).
  - name: --stack
    description: Select a stack before acquisition; explicit forms are number:N, branch:NAME or id:ID. Bare ASCII numbers mean stack numbers.
  - name: --full
    description: Print all layer rows without forcing refresh.
  - name: --refresh-git
    description: Refresh relevant git refs once; does not refresh hosted status.
  - name: --refresh-status
    description: Refresh required hosted observations for the selected scope.
  - name: --refresh
    description: Reconcile remote stack membership, git refs and hosted observations.
  - name: --json
    description: Emit complete stacks[].rows[] and branches[], problems[], notes[], landing, coherent and provenance as JSON.
  - name: --compact-json
    description: Bounded JSON presentation with explicit counts and truncation; not complete composition evidence.
  - name: --help
    description: Show options.
---

# /sc-gh-stack-view command

Read-only status table for one or more `gh stack`s (under a plugin install substitute `$CLAUDE_PLUGIN_ROOT/scripts/` for `.claude/scripts/`). Runs:

```bash
python3 .claude/scripts/gh_stack_view.py <args>
```

from the repo root, passing through the supplied scope, output and refresh
options. Default acquisition derives local state and reuses shared observations
before requesting missing hosted facts. Text summaries contain at most ten
layer rows; `--full` and `--json` retain all layers. If the script is not
found at that path, locate it with `find .claude ~/.claude -name gh_stack_view.py`
and use that path instead.

Paste stdout **verbatim and unfenced** (no ``` around it) so the markdown
table renders. Do not reformat, summarize, or replace it with per-branch
`gh pr view` calls.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | every shown stack coherent |
| 1 | problems listed under a VERDICT — report them, do not silently retry |
| 2 | nothing to show or the environment failed — show the single stderr line (`gh-stack-view: ...`) verbatim; it names the next action |

See the `sc-gh-stack-view` skill for the column legend and full output
walkthrough.
