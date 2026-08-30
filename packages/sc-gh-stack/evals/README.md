# sc-gh-stack evals

Behavioral evals for the `managing-gh-stacks` skill, run with the (early-access)
`claude plugin eval` harness against a small model. Each case reproduces a real field
incident in a **local fixture repo with a scripted `gh` stub** — no GitHub repo, no
network, fully deterministic. What is being graded is the *agent's decisions* (does it
believe `needsRebase`, check stack membership before merging, detect a silent sync
abort), not the gh-stack extension itself.

`INCIDENTS.md` documents each underlying field incident with enough detail to recreate
it — background for authoring or reviewing cases. Nothing outside `evals/` references
this folder: the skill installs and runs fully without it (`sc-install` skips `evals/`
unless `--include-evals` is passed).

## Cases

| Case | Field incident it locks in |
|---|---|
| `rebase-believe-the-report` | gh reported a rebase necessary; the agent inspected locally, saw nothing, and denied the rebase existed (stack root was ahead; a conflict-free `rebase --upstack` fixed it) |
| `merge-membership-check` | `gh stack merge <top>` on a "2-PR stack" merged only the top PR because the other was never linked into the stack — cost an extra PR + CI + approval cycle |
| `sync-aborted-detection` | non-interactive `gh stack sync` on a diverged stack prints "Sync aborted" but exits 0; success must not be reported |
| `merge-forward-not-rebase` | "stack out of date" was mis-diagnosed as a rebase; `gh stack rebase` conflicted — the real drift was `main` ahead of `develop` (merge-forward-only repo), reachable with one `git rev-list --count develop..main` |
| `release-stack-shape` | a `develop -> main` PR was planned as a stack layer; a protected-branch head is a bad layer (head moves on lower-layer merge, invalidating gated CI; tooling can't rebase it) |
| `merge-verify-outcome` | post-merge state was checked only after the fact (#148 still OPEN); verification of MERGED state + target content belongs in the merge step — ideal transcript is ~4 calls |

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

## Publishing reports to the site

Raw run outputs under `evals/results/` are gitignored. The committed record is
`site/reports/evals/<plugin>/<date-time>-<eval-name>.html`, populated after a run with:

```bash
python3 scripts/collect-eval-reports.py --package sc-gh-stack
```

(`--report <path>` on the eval invocation can also write the HTML straight to that
naming if you prefer skipping the sweep.)
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
