---
name: sc-gh-stack-view
description: Print the one-call coherence, mergeability, CI and LANDING table for every open gh stack (read-only). Paste the script output verbatim.
version: 0.1.1
options:
  - name: --trunk
    description: Only stacks whose trunk is this branch (e.g. develop, integrate/phase-bc).
  - name: --phase
    description: Shorthand for --trunk integrate/phase-<PHASE>.
  - name: --all
    description: Show every stack, including merged/closed ones.
  - name: --no-fetch
    description: Skip git fetch origin; rebase column shows ❓.
  - name: --no-pr
    description: Skip the GraphQL PR query (offline / local-only view).
  - name: --json
    description: Emit stacks[].rows[], problems[], notes[], landing, coherent as JSON.
  - name: --help
    description: Show options.
---

# /sc-gh-stack-view command

Read-only status table for one or more `gh stack`s (under a plugin install substitute `$CLAUDE_PLUGIN_ROOT/scripts/` for `.claude/scripts/`). Runs:

```bash
python3 .claude/scripts/gh_stack_view.py <args>
```

from the repo root, passing through whichever of `--trunk`, `--phase`,
`--all`, `--no-fetch`, `--no-pr`, `--json` were given. If the script is not
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
