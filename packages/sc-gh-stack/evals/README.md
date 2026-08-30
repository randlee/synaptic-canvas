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

## Two tiers: nudged vs discovery-canary

Behavioral cases name the skill explicitly in the prompt ("Use the managing-gh-stacks
skill…") — mirroring production, where orchestration prompts name skills rather than
relying on trigger matching. Two cases (`release-stack-shape`, `sync-aborted-detection`)
deliberately carry NO nudge: they double as discovery canaries — when small models start
consulting the skill unprompted, they'll show it. Every case allows the `Skill` tool
(omitting it was a real harness bug: models could see skills but not load them).

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

### Primary: test-packages harness

The repo's test harness (`test-packages/`, see its README) executes these cases with
full isolation (HOME override), hook traces, artifact preservation, and its HTML
report format. `scripts/generate-eval-fixtures.py` converts every case here into
`test-packages/fixtures/sc-gh-stack-evals/` (files are marked GENERATED — edit the
case, re-run the generator):

```bash
python3 scripts/generate-eval-fixtures.py --package sc-gh-stack
pytest test-packages/fixtures/sc-gh-stack-evals/ -v --open-report --run-evals
python3 scripts/collect-eval-reports.py     # rebuilds the site/reports/evals pages
```

`--run-evals` is required: eval fixtures execute live Claude agent sessions, so the
harness skips them by default — a broad `pytest test-packages/fixtures/` sweep, CI, or
an accidental run can never start one.

Eval-fixture reports publish **directly** to
`site/reports/evals/<pkg>/<YYYYMMDD-HHMMSS>-<pkg>-evals.html` (plus the JSON sidecar and
artifacts folder) — the long-term, GitHub-Pages-viewable record with full history. An
explicit `--report-dir` overrides. The collector run afterwards refreshes the Pages
index.

Grader types map onto harness expectations (tool_used → tool_call/tool_not_called,
regex → output_contains/output_not_contains/file_contains/file_not_contains, plus
tool_order and llm_judge added to the harness for these evals). A case's `env:` block
is applied via the generated project `.claude/settings.json` (the harness runs Claude
with `--setting-sources project`).

### Fallback: standalone local runner (until `claude plugin eval` is unlocked)

`claude plugin eval` is early access (org enablement pending). Until then,
`scripts/run-evals-local.py` executes the same case files unchanged — scaffold, prompt
frontmatter (model/max_turns/env/allowed_tools), and all grader types (regex, tool_used,
tool_order, file_exists, llm-judged) — via headless `claude -p`, installs the package
into the throwaway workspace's `.claude/` so the skill is live, and writes
`aggregate-result.json` + `report.html` into `evals/results/<timestamp>/` in the same
layout the official harness uses:

```bash
python3 scripts/run-evals-local.py --package sc-gh-stack            # all cases
python3 scripts/run-evals-local.py --package sc-gh-stack --case merge-verify-outcome
```

The publish step below is identical for both harnesses; retire the local runner once
the official one is enabled.

### Official harness

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
