# Field incidents behind the eval suite

Each incident below was hit by a real agent session using gh-stack (August 2026, repos
following a `main` / `develop` merge-forward release flow). For each: what happened, why,
how to recreate it, what the correct behavior is, and which eval case locks it in. This
file is background for eval authors and reviewers — nothing in the skill, agents, or
scripts references it.

---

## 1. Denied a rebase that gh had reported

**Eval:** `rebase-believe-the-report` · **Skill fix:** `references/playbook-rebase.md`
("Rule zero"), SKILL.md route-table row

**What happened.** gh reported the stack needed a rebase. The agent inspected the
branches locally, saw nothing wrong, and told the user no rebase was needed. The root of
the stack (the bottom branch) was ahead of the layers above it; a conflict-free cascade
rebase was required and the user had to run it manually.

**Why.** `needsRebase` is computed against remote/parent state. A local look at one
layer's diff cannot see that a *lower* layer advanced; stale remote-tracking refs make it
worse.

**Recreate.** Repo with `main <- feat/core <- feat/api`; after cutting `feat/api`,
commit again on `feat/core`. `gh stack view --json` reports `needsRebase: true` on
`feat/api` while `feat/api`'s own diff looks clean. Fix is
`gh stack checkout feat/core && gh stack rebase --upstack` (no conflicts).

**Correct behavior.** `git fetch` + `gh stack view --json`; believe the report; run the
cascade; only claim "no rebase needed" after `view --json` shows false everywhere.

---

## 2. Merged a subset of the intended stack (most costly)

**Evals:** `merge-membership-check`, `merge-verify-outcome` · **Skill fix:**
`references/playbook-merge.md` ("Rule zero", scope callout, post-merge verification),
SKILL.md pre-merge paragraph

**What happened.** `gh stack merge 149 --yes --merge` was run assuming the stack was
#148 → #149. The stack object actually contained only #149 — #148 (the version bump) was
never linked. The merge landed `develop -> main` without the bump, `main` stayed at
0.5.0, and a third PR (+ CI cycle + approval gate) was needed to repair. The agent
noticed #148 was still OPEN only after the fact.

**Why.** Two model errors: (a) `gh stack merge <pr>` was read as "merge these two PRs"
when the semantics are "merge the stack up to PR N" — scope is defined by the GitHub
stack object, not branch topology or PR bases; an unlinked PR is silently untouched.
(b) No `gh stack view --json` before merging, and no atomic post-merge verification.

**Recreate.** Two PRs where the upper one is tracked in a stack and the lower one is
not; run `gh stack merge <upper> --yes`. Observe: one PR merged, the other untouched, no
warning.

**Correct behavior.** `gh stack view --json` → assert expected PR **set and order** →
merge → in the same step assert every expected PR `MERGED` and the target branch carries
the change (e.g. the version file) → report. Ideal transcript ≈ 4 calls. If a PR is
missing from the stack: STOP and surface (link/restructure), never land the subset.

---

## 3. Planned a protected-branch head as a stack layer

**Eval:** `release-stack-shape` · **Skill fix:** SKILL.md hard rule 7,
`sc-stack-plan` rule 7, `references/playbook-merge.md` ("Release stacks")

**What happened.** A release flow was shaped as a 2-layer stack:
`release/0.6.0 -> develop` (bottom) and `develop -> main` (top).

**Why it's wrong.** The top layer's *head* is `develop`, a protected long-lived branch.
When the bottom layer merges, that head moves — invalidating the CI the gated merge
relied on — and stack tooling cannot rebase a protected head.

**Recreate.** Any repo with protected `develop`/`main`: stack the two PRs above,
merge the bottom, watch the top PR's head advance and its checks go stale.

**Correct behavior.** Stack lands INTO the protected branch (`release/x -> develop`);
the `develop -> main` PR is opened separately after it lands — or one
`release/x -> main` PR plus a merge-forward.

---

## 4. Fell back to `gh pr merge --admin` past a protection blocker

**Eval:** covered by graders in `merge-membership-check` / `merge-verify-outcome`
(`gh pr merge` and `gh api` are auto-fail) · **Skill fix:** SKILL.md hard rule 2,
`references/playbook-merge.md` ("Pre-merge protection check")

**What happened.** When the stack path failed, the agent tried `gh pr merge` (blocked —
wasted call), then `gh pr merge --admin` (bypassing protection). The actual blocker was
**stale required status contexts**: protection required `Clippy` / `Format check` while
CI had been renamed to `Just lint`, so the required contexts could never be satisfied.

**Recreate.** Branch protection requiring a status-check name no workflow produces;
all real CI green; attempt a merge.

**Correct behavior.** Before merging, compare
`gh api .../branches/<base>/protection --jq '.required_status_checks.contexts'` against
the head's check-run names. A required context absent from the head's runs blocks the
merge regardless of green CI — surface it (fixing protection is a human decision).
`--admin` is never an acceptable fallback.

---

## 5. Recommended a rebase when the drift was above the stack's base

**Eval:** `merge-forward-not-rebase` · **Skill fix:** SKILL.md hard rule 8,
`references/playbook-rebase.md` ("Merge-forward repositories")

**What happened.** The agent told the user the stack was out of date; the user ran
`gh stack rebase`, which conflicted. The real cause: `main` carried a PR (#116) that
`develop` (the stack's base) lacked — in a merge-forward-only repo. The one-command
diagnosis `git rev-list --count develop..main` was never run.

**Recreate.** Stack based on `develop`; commit a hotfix on `main` only; repo policy
merge-forward only. `rev-list --count develop..main` = 1; a rebase replays foreign
history and conflicts.

**Correct behavior.** Run the `rev-list` check before recommending any rebase/sync.
Drift *above* the base in a merge-forward repo → open a merge-forward PR
(`main -> develop`); never `gh stack rebase`/`sync`.

---

## 6. Rate-limited by ad-hoc CI polling

**Eval:** none yet (candidate: a mock-calls grader counting check-run queries) ·
**Skill fix:** `references/playbook-merge.md` ("Waiting on CI")

**What happened.** Repeated per-tick `gh api .../check-runs` loops (some from cron) hit
the 5,000/hr REST rate limit several times during one landing.

**Correct behavior.** One watcher per head (`gh pr checks <pr> --watch`, or a single
≥ 30s loop with a `--jq` filter to non-success runs); when rate-limited, stop polling
entirely until the window resets.

---

## 7. Refused merge answered with raw REST experiments

**Evals:** `api *` is a hard-fail path in every stub · **Skill fix:** SKILL.md
description + hard rules, `references/playbook-merge.md` ("Failure modes")

**What happened** (earlier incident, separate session). GitHub refused `gh pr merge` on
stacked PRs ("this pull request is part of a stack"); the agent offered a menu including
hand-rolled REST mutations against the stacks API.

**Correct behavior.** The refusal is routine, not an error: run `gh stack merge <pr#>
--yes` after the membership check. (GitHub's web UI stack merge is the same native flow
and is fine for humans.)

---

## 8. Silent sync abort reported as success

**Eval:** `sync-aborted-detection` · **Skill fix:** `gh_stack_sync.py`
(`SYNC.ABORTED`, exit 5), `sc-stack-sync` propagation rule,
`references/playbook-sync.md`

**What happened** (found in review, confirmed against upstream docs). Non-interactive
`gh stack sync` on a diverged local/remote stack prints both chains plus `Sync aborted`
and exits **0** without fetching, rebasing, or pushing anything. Exit-code-only checking
reports success while nothing happened.

**Recreate.** Track a stack locally, change its composition on the remote (e.g. link a
different PR), run `gh stack sync` non-interactively; observe exit 0 + `Sync aborted`.

**Correct behavior.** Treat `Sync aborted` as a failure distinct from success
(`SYNC.ABORTED`); present the keep-remote vs keep-local choice; never report synced.
