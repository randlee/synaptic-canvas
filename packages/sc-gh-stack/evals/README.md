# sc-gh-stack evals

Behavioral evals for the `managing-gh-stacks` skill, run with the (early-access)
`claude plugin eval` harness against a small model. Each case reproduces a real field
incident in a **local fixture repo with a scripted `gh` stub** — no GitHub repo, no
network, fully deterministic. What is being graded is the *agent's decisions* (does it
believe `needsRebase`, check stack membership before merging, detect a silent sync
abort), not the gh-stack extension itself.

## Cases

| Case | Field incident it locks in |
|---|---|
| `rebase-believe-the-report` | gh reported a rebase necessary; the agent inspected locally, saw nothing, and denied the rebase existed (stack root was ahead; a conflict-free `rebase --upstack` fixed it) |
| `merge-membership-check` | `gh stack merge <top>` on a "2-PR stack" merged only the top PR because the other was never linked into the stack — cost an extra PR + CI + approval cycle |
| `sync-aborted-detection` | non-interactive `gh stack sync` on a diverged stack prints "Sync aborted" but exits 0; success must not be reported |

## Running

Requires `claude plugin eval` early access (enabled per organization).

```bash
cd packages/sc-gh-stack
claude plugin eval . --model claude-haiku-4-5-20251001 --allow-tools Bash Read Grep Glob
```

One case:

```bash
claude plugin eval . --case rebase-believe-the-report --model claude-haiku-4-5-20251001 --allow-tools Bash Read Grep Glob
```

Results land in `evals/results/<timestamp>/aggregate-result.json` (+ `report.html`).
Each case pins `model:` to haiku in its frontmatter as well, so a bare invocation grades
the small-model behavior the skill must survive.

## Fixtures

Each case's `scaffold.sh` builds a throwaway git repo (with a local bare `origin`, so
`git fetch` is real) and prepends a stub `gh` to PATH that replays the recorded upstream
behavior for that scenario (`stack view --json` payloads, the exit-0 `Sync aborted`
output, PR lookups). The stub records every invocation to `gh-calls.log` in the
workspace. `sync-aborted-detection` also copies the package scripts into
`.claude/scripts/` so the skill's script route is available.

## Future lane (optional)

A live end-to-end lane against a throwaway GitHub repository with the real gh-stack
extension would additionally cover upstream behavior drift. Not included: it needs a
dedicated repo, auth, and cleanup, and upstream behavior is already pinned by the
verbatim references. Revisit if upstream releases change semantics.
