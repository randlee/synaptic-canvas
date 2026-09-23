---
name: sc-gh-stack
description: Run stacked PRs with gh-stack the way that lands (append-only layers, one stack writer, QA/CI on the top, one atomic merge). Routes to the sc-gh-stack skill and its recipes.
version: 0.1.1
options:
  - name: --status
    description: Run /sc-gh-stack-view and paste the coherence, mergeability, CI and LANDING table verbatim.
  - name: --check
    args:
      - name: trunk
        description: Branch the stack lands on (e.g. develop, integrate/phase-bc).
      - name: layers
        description: Proposed order bottom to top, branch names or PR numbers.
    description: Read-only pre-link chain check (gh_stack_chain_check.py); prints the exact link command to run next.
  - name: --cut
    args:
      - name: layer
        description: New branch name for the layer.
    description: Walk the cut-a-layer recipe (new worktree from the pushed top, PR on first push, link).
  - name: --link
    description: Walk the link recipe (append to the stack, or the full ordered link with --base).
  - name: --restack
    description: Walk the restack recipe (insert a layer, remove a red layer whose fix is above, collapse the bottom).
  - name: --land
    description: Walk the landing checklist and the atomic merge, with the merge-async and non-linear fallbacks.
  - name: --help
    description: Show options and the recipe index.
---

# /sc-gh-stack command

Delegates to the `sc-gh-stack` skill. For `--cut`, `--link`, `--restack` and
`--land`, start with the skill's Step 1 (CLI verification) and Step 2
(`/sc-gh-stack-view`), then open only the reference the option maps to.
`--status` and `--check` are themselves the status calls (Step 1 only);
`--help` runs nothing.

| Option | Reference in `skills/sc-gh-stack/references/` |
|--------|-----------------------------------------------|
| `--status` | run `python3 .claude/scripts/gh_stack_view.py [--trunk <t>]` (or `$CLAUDE_PLUGIN_ROOT/scripts/...` under a plugin install), paste stdout verbatim and unfenced |
| `--check <trunk> <layers...>` | run `python3 .claude/scripts/gh_stack_chain_check.py --trunk <trunk> <layers...>`, paste stdout verbatim |
| `--cut <layer>` | `recipe-cut-layer.md`, then `recipe-link.md` |
| `--link` | `recipe-link.md` |
| `--restack` | `recipe-restack.md`, then `recipe-stale-tracking.md` |
| `--land` | `recipe-land.md` |
| no option / `--help` | print this table and the one-paragraph model from `SKILL.md`; no repository chatter |

Rules the command enforces regardless of option:

- Every `gh stack` write command (`link`, `unstack`, `sync`, `rebase`,
  `merge`) is run only by the stack writer, only after `/sc-gh-stack-view`,
  and is followed by `/sc-gh-stack-view` again.
- Creating or re-creating a stack is one `gh stack link --base <trunk>` with
  the full ordered list; `gh stack link <stack#> <pr#>` only appends on top.
  Landing is `gh stack merge <stack#> --yes --merge`, never `--squash`.
- Landing, closing PRs and unstacking are confirmed with the user unless the
  user already directed that exact action.
- No tool traces in the reply: the pasted script output, the verdict, and
  the next command.
