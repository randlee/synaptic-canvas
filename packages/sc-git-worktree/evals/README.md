# sc-git-worktree evals

Behavioral evals for the `sc-managing-worktrees` skill's **worktree factory decision
model** (see `../DESIGN.md`, "Worktree factory decision model"), run with the
(early-access) `claude plugin eval` harness against a small model. Each case reproduces
a scenario in a **local fixture repo with a real git repo + bare origin, and a scripted
`gh` stub** — no GitHub repo, no network, fully deterministic. `git` itself is never
stubbed: every worktree/branch/merge check in these fixtures is a real `git` operation.
What is being graded is the *agent's decisions* — which of the three factory products
(A/B/C) a request resolves to, and whether the mandatory refusals fire — not the
gh-stack extension itself.

## Cases and the decision-table rows they lock in

| Case | DESIGN.md row it locks in |
|---|---|
| `flat-create-stays-flat` | Stage 2, stack-activity probe: repo has no `always_stack` and no worktree anywhere carries gh-stack tracking → **not stack-active → product A immediately**, no settings read beyond the one `always_stack` lookup, no `gh` invocation at all |
| `branch-of-branch-naive` | Same stage-2 row, exercised against an **unmerged** base branch — the "positive-signal rule" / "auto-upgrade for legacy prompts": dependency is never evaluated in a stack-naive repo, so a branch-of-branch create stays flat exactly as it did before gh-stack support existed |
| `always-stack-product-b` | Stage 5, Policy: stack-active via `git.always_stack: true`, prerequisites present, base (`develop`) is independent (it IS `stack_root`) → **product B** — same path as a flat worktree, `git config rerere.enabled true`, `gh stack init --base develop <branch>` |
| `dependent-base-joins-stack` | Stage 4, Dependency: stack-active via tracking-marker-only (no `always_stack` needed — any tracked worktree anywhere makes the repo stack-active), base is unmerged and its own worktree carries gh-stack tracking → **product C** — no new worktree, `git checkout -b` + `gh stack add` inside the base's existing stack worktree |
| `prereqs-missing-onboarding` | Stage 3, mandatory prerequisite gate: stack-active via `always_stack`, but the gh-stack extension and the managing-gh-stacks skill are both missing → **refuse `CREATE.STACK_PREREQS_MISSING`** naming the exact installs, before any mutation (including `git fetch`) — never fall back to a flat worktree or improvise stack operations |
| `cleanup-skips-tracked-stack` | Interop rule #2 (`gh-stack-support.md`): gh-stack tracking is **per-worktree** state; batch cleanup must skip any worktree carrying it regardless of merge state, while cleaning up merged, untracked worktrees normally |

## Running

### Primary: test-packages harness

The repo's test harness (`test-packages/`, see its README) executes these cases with
full isolation (HOME override), hook traces, artifact preservation, and its HTML
report format. `scripts/generate-eval-fixtures.py` converts every case here into
`test-packages/fixtures/sc-git-worktree-evals/` (files are marked GENERATED — edit the
case, re-run the generator):

```bash
python3 scripts/generate-eval-fixtures.py --package sc-git-worktree
pytest test-packages/fixtures/sc-git-worktree-evals/ -v --open-report --run-evals
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
python3 scripts/run-evals-local.py --package sc-git-worktree            # all cases
python3 scripts/run-evals-local.py --package sc-git-worktree --case dependent-base-joins-stack
```

The publish step below is identical for both harnesses; retire the local runner once
the official one is enabled.

### Official harness

Requires `claude plugin eval` early access (enabled per organization).

```bash
cd packages/sc-git-worktree
claude plugin eval . --model claude-haiku-4-5-20251001 --allow-tools Skill Bash Read Grep Glob
```

One case:

```bash
claude plugin eval . --case always-stack-product-b --model claude-haiku-4-5-20251001 --allow-tools Skill Bash Read Grep Glob
```

Results land in `evals/results/<timestamp>/aggregate-result.json` (+ `report.html`).

Every case's `allowed_tools` list `Skill` first: the harness previously omitted it,
which let a small model *see* the installed `sc-managing-worktrees` skill (and its
DESIGN.md-documented decision model) but never actually invoke it, so it fell back to
guessing from priors and failed. `Skill` must stay first in every case's frontmatter.

## Publishing reports to the site

Raw run outputs under `evals/results/` are gitignored. The committed record is
`site/reports/evals/<plugin>/<date-time>-<eval-name>.html`, populated after a run with:

```bash
python3 scripts/collect-eval-reports.py --package sc-git-worktree
```

(`--report <path>` on the eval invocation can also write the HTML straight to that
naming if you prefer skipping the sweep.)
Each case pins `model:` to haiku in its frontmatter as well, so a bare invocation grades
the small-model behavior the decision model must survive.

## Fixtures

Each case's `scaffold.sh` builds a real git repo at `./repo` (with a local bare
`origin`, so `git fetch`/`push` are real) and prepends a stub `gh` to PATH that replays
the recorded `gh`/`gh-stack` surface for that scenario (`extension list`,
`stack init`/`stack add` exit codes). The stub records every invocation to
`gh-calls.log` in the workspace. **`git` itself is never stubbed** — every merge/branch/
worktree check the decision model relies on runs against a real repository, matching
`tests/test_factory_decision.py`. Every scaffold also copies the package's own
`scripts/*.py` into `repo/.claude/scripts/` so the agent can drive the real
`worktree_create.py` / `worktree_cleanup.py` decision logic directly, the same way
`sc-gh-stack`'s `sync-aborted-detection` scaffold copies its scripts.

Cases that require the mandatory prerequisite gate to already be satisfied
(`always-stack-product-b`, `dependent-base-joins-stack`) also drop a
`.claude/skills/managing-gh-stacks/SKILL.md` marker file into the repo, matching
`check_sc_gh_stack_skill`'s direct-candidate path. `prereqs-missing-onboarding`
deliberately omits it.

## Future lane (optional)

A live end-to-end lane against a throwaway GitHub repository with the real gh-stack
extension would additionally cover upstream behavior drift. Not included: it needs a
dedicated repo, auth, and cleanup, and the decision model itself is pure local
git/filesystem logic with no upstream dependency. Revisit only if `gh stack` semantics
that the prerequisite/tracking checks rely on change upstream.
