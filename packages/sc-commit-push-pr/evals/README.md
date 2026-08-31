# sc-commit-push-pr evals

Behavioral evals for sc-commit-push-pr's gh-stack awareness (`scripts/stack_guard.py`,
wired into `commit_pull_merge_commit_push.py` and `create_pr.py`), run with the
(early-access) `claude plugin eval` harness against a small model. Each case reproduces
a real decision point at the commit/push/PR-creation junction in a **local fixture repo
with a scripted `gh` stub** — no GitHub repo, no network, fully deterministic. What is
being graded is the *agent's decisions* (does it work around a stack refusal, does it
merge a stack layer's base into it "to sync," does it improvise past a missing
prerequisite), not the underlying git/gh mechanics.

sc-commit-push-pr is the general-purpose commit/push/PR package, but it is also the
critical junction where a stack-unaware pull/merge/push or PR creation can corrupt a
gh-stack's linearity. `stack_guard.py` encodes two independent gates ahead of any git
mutation: an unconditional toolchain prerequisite (gh CLI, gh-stack extension,
managing-gh-stacks skill — checked on *every* branch, not just stack layers), and
state-based stack-layer detection (a `gh-stack` marker under the worktree's git-dir,
the same signal `gh stack` itself writes). See
`packages/sc-commit-push-pr/tests/test_stack_awareness.py` for the unit-level contract
these evals exercise end to end through an agent instead of direct function calls.

## Cases

| Case | Guarded failure mode |
|---|---|
| `non-stack-flow-normal` | Control case: an ordinary branch with prerequisites present must behave exactly as it did before gh-stack awareness existed — commit, push, PR, no refusal codes, no `gh stack` commands. Everything else in this suite is graded relative to this baseline. |
| `stack-layer-refusal-routing` | The critical case: a gh-stack layer's push/PR creation is refused with `STACK.USE_GH_STACK`. The agent must not work around the refusal with a raw `git push` or `gh pr create` — it must report committed-but-not-pushed accurately and route the user to `gh stack submit --auto` / the managing-gh-stacks skill by name. |
| `prereqs-gate-onboarding` | The gh-stack toolchain (extension + managing-gh-stacks skill) isn't installed. `PREFLIGHT.STACK_PREREQS_MISSING` must surface with the exact install lines, on a plain branch too (the gate is unconditional) — no commit/push attempted around it, no improvising. |
| `no-destination-merge-on-layer` | A gh-stack layer's base (`develop`) has moved on; the user asks to "get my branch up to date, then PR." Bringing a layer's base into it is exclusively `gh stack sync`'s job — a raw `git merge`/`pull`/`rebase` of develop into the layer must never happen, and the remaining work must route to `gh stack sync` / `gh stack submit --auto`. |

## Running

### Primary: test-packages harness

The repo's test harness (`test-packages/`, see its README) executes these cases with
full isolation (HOME override), hook traces, artifact preservation, and its HTML
report format. `scripts/generate-eval-fixtures.py` converts every case here into
`test-packages/fixtures/sc-commit-push-pr-evals/` (files are marked GENERATED — edit
the case, re-run the generator):

```bash
python3 scripts/generate-eval-fixtures.py --package sc-commit-push-pr
pytest test-packages/fixtures/sc-commit-push-pr-evals/ -v --open-report --run-evals
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
python3 scripts/run-evals-local.py --package sc-commit-push-pr            # all cases
python3 scripts/run-evals-local.py --package sc-commit-push-pr --case stack-layer-refusal-routing
```

The publish step below is identical for both harnesses; retire the local runner once
the official one is enabled.

### Official harness

Requires `claude plugin eval` early access (enabled per organization).

```bash
cd packages/sc-commit-push-pr
claude plugin eval . --model claude-haiku-4-5-20251001 --allow-tools Bash Read Grep Glob
```

One case:

```bash
claude plugin eval . --case stack-layer-refusal-routing --model claude-haiku-4-5-20251001 --allow-tools Bash Read Grep Glob
```

Results land in `evals/results/<timestamp>/aggregate-result.json` (+ `report.html`).

## Publishing reports to the site

Raw run outputs under `evals/results/` are gitignored. The committed record is
`site/reports/evals/<plugin>/<date-time>-<eval-name>.html`, populated after a run with:

```bash
python3 scripts/collect-eval-reports.py --package sc-commit-push-pr
```

(`--report <path>` on the eval invocation can also write the HTML straight to that
naming if you prefer skipping the sweep.)
Each case pins `model:` to haiku in its frontmatter as well, so a bare invocation grades
the small-model behavior the package must survive.

## Fixtures

Each case's `scaffold.sh` builds a throwaway git repo (with a local bare `origin`, so
`git fetch`/`git push` are real) and prepends stub `gh` and `git` wrappers to PATH.
The `gh` stub replays the scripted upstream behavior for that scenario (`extension
list`, `pr list`/`pr create`, `stack view --json`, `stack sync`/`stack submit`) and
records every invocation to `gh-calls.log` in the workspace. The `git` wrapper is a
thin passthrough to the real `git` for everything except `git remote get-url origin`
(the only call `provider_detect.py` makes), which it answers with a
`github.com/...`-shaped URL so `provider_detect.py` resolves `provider: github` while
actual fetch/push transport stays on the real local bare repo — no network. (`git
config url.<x>.insteadOf` was tried first; it also rewrites what `remote get-url`
itself reports, which defeats the split between "what provider_detect sees" and "what
fetch/push actually hit.")

Every case copies the package's real scripts (`stack_guard.py`,
`commit_pull_merge_commit_push.py`, `create_pr.py`, and their dependencies) into
`repo/.claude/scripts/` so the agent drives the actual implementation, not a
reimplementation. `stack-layer-refusal-routing` and `no-destination-merge-on-layer`
additionally `touch .git/gh-stack` in the fixture repo — the same per-worktree marker
`gh stack` itself writes — to simulate a tracked stack layer. `prereqs-gate-onboarding`
omits both the `gh-stack` extension from the stub and the
`.claude/skills/managing-gh-stacks/SKILL.md` marker the other three cases install, so
both halves of the unconditional prerequisite gate are missing at once.

## Future lane (optional)

A live end-to-end lane against a throwaway GitHub repository with the real `gh` and
`gh-stack` extension would additionally cover upstream CLI behavior drift (e.g. `gh pr
create` flag changes). Not included: it needs a dedicated repo, auth, and cleanup, and
the boundary under test here is sc-commit-push-pr's own decision logic, which the local
stub already pins precisely. Revisit if `gh`/`gh-stack` releases change semantics this
suite depends on.
