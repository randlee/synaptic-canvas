# The append-only stack model

Read this once, before the first `gh stack` command in a repository. It defines
the vocabulary every recipe uses and the four rules everything else follows
from. The rules were derived over five production phases (2026-09-05 to
2026-09-23) of running 2 to 21 stacked PRs per stack; every "why" is an
incident, not a preference.

## Vocabulary

| Term | Meaning |
|------|---------|
| **trunk** | The branch the stack lands on. `develop`, an integration branch such as `integrate/phase-N`, or a release branch. Always named explicitly; never the repository default branch by assumption. |
| **layer** | One branch with one PR whose base is the layer below (the bottom layer's base is the trunk). |
| **bottom / top** | Bottom is closest to the trunk and merges first. Top is the landing head. `gh stack up` moves away from trunk, `down` toward it. |
| **writer** | The single agent allowed to push a layer. |
| **stack writer** | The single agent (lead, orchestrator) allowed to run any `gh stack` write command: `link`, `unstack`, `sync`, `rebase`, `merge`. |
| **frozen** | A layer whose task has closed. Nobody touches it again, ever. |
| **landing head** | The pushed head of the top layer; the only tree that reaches the trunk. |
| **stack number** | GitHub's identifier for the stack. `gh stack link` prints it and the PR page shows it in the stack panel; `gh stack view --json` does not. Record it after every link. If it was lost, `gh stack checkout <pr#>` from a worktree without stale tracking resolves the stack by PR number and imports it. Every unstack + re-link mints a new one. |

## Rule 1 — The stack is append-only and linear

Every unit of work (sprint, fix round, cleanup, docs, evidence) is a **new
worktree cut from the current pushed top**. Its PR opens on the first push with
base = the layer below and is linked into the stack at once. A layer is frozen
the moment its task closes; anything found on it later is fixed on a new layer
above the top.

Consequences, all of them deliberate:

- Every layer is immutable once it exists, so reviews and QA verdicts on it
  stay true.
- The top contains everything by construction, so there is never a
  merge-forward.
- Fixes are new layers that close findings in lower layers.
- Only the top runs the gating CI, and the stack merges once from the top.
- Who owns what is derivable from git instead of relayed by message.
- Nobody waits for a lower layer's QA or CI. A dev's next sprint starts on a
  layer cut from their just-pushed head.

*Why:* a phase that reintroduced serial waits (a sprint queued behind a fix
round, fix rounds on frozen layers, a layer cut from a stale head) lost an hour
per instance. One agent working this way moves through every sprint of a phase
back-to-back without stopping.

**Strictly linear.** One parent, at most one child. Two layers cut from the
same head are a fork: `gh stack merge` refuses forks, and the sibling that is
not merged forward loses files upstack, shows red CI on stale merge refs, and
produces false conflict reports. Order siblings by dependency and chain them,
or run the independent one as its own stack on the trunk.

## Rule 2 — One writer per branch, one stack writer

The stack writer opens PRs, links, syncs, restacks and lands. A layer's writer
pushes commits to that layer and nothing else: never to another layer, never to
the trunk. Devs never run `gh stack` write commands.

*Why:* devs running `gh stack` writes, cloned variable files, and a dev holding a
push "until the parent SHA is known" each cost hours in one phase.

## Rule 3 — QA and CI gate the top only

The landing head is the only tree that reaches the trunk, so its CI and its QA
verdict are the only gates. Red CI on a frozen layer is not fixed there.

- QA is dispatched once, on the top, when the top is pushed. A QA already
  running on a mid layer of a large stack may finish and its verdict carries
  forward; nothing new is dispatched below the top.
- QA diffs the layer against the commit it was cut from (pinned SHA), not
  against the moving GitHub base. The verdict is posted on the PR.
- A red check on a lower layer can be a base-branch defect fixed minutes later:
  PR CI builds `head + base as it stood when the run started`. Read the job
  log's "Merge <head> into <base>" line before dispatching anyone.
- Per-layer QA on a small stack only doubles the "qualitative best-practices"
  findings.

## Rule 4 — CI runs once, the merge happens once

Every push to a PR head cancels and restarts its CI (30 to 60 minutes on a
large repository). The whole layering discipline exists to make CI run once per
landing, not once per tweak.

- No cosmetic or metadata commit to a PR that is green or mid-run; put it in
  the layer that lands next.
- Batch follow-ups into one validated push, not a drip.
- Never rebase or sync a branch whose CI is running unless it is the landing
  layer and the sync is required to land.
- Never push to the trunk while a stack sync or merge is in flight; that
  restarts CI on every layer (see `preconditions.md`, trunk freeze).
- Prefer local gates (format, lint, tests) over CI polling; at most one CI
  watcher at a time, polling no faster than every 60 seconds. GitHub's
  secondary rate limit is per user across every agent and trips on bursts.

## The small-fix rule

A change with one owner and bounded scope, well under a few hundred lines with
fix and tests together, is **one PR off the trunk with no stack**: local lint
and tests, one acceptance check, CI green, merge. No stack, no QA task, no
triage record.

*Why:* a thirty-line fix became two layers, two QA rounds (the second produced
only a pre-existing "best-practices" finding), and a bottom-alone merge that
turned the trunk red.

## Two shapes that work

| Shape | Trunk | Use |
|-------|-------|-----|
| Phase stack | `integrate/phase-N` (or any integration branch) | Several sprints and fix rounds from several devs that must land as one unit. The phase closes with one PR trunk → `develop`. Worked example: `phase-model-example.md`. |
| Develop stack | `develop` | Several open fix or feature PRs already targeting `develop` that must land together: chain them (one merge-forward commit per upper layer), link with `--base develop`, freeze everything below the top, QA and CI on the top, merge once. Evidence-only PRs may merge alone. `recipe-link.md` section B. |

*Why (develop stack):* "do not wait 5 hours for CI to re-run after every PR";
three independent PRs onto an integration branch cost three CI cycles and two
re-runs. One linear stack means the top's CI validates everything.

## Related

- `workflow.md` — the lifecycle of one layer, step by step.
- `preconditions.md` — the checks that stop each known failure.
- `stack-design.md` — how to cut layers so they stay independent.
