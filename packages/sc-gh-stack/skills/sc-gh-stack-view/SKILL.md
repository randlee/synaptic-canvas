---
name: sc-gh-stack-view
version: 0.2.2
description: Report local stack coherence and content conflicts, hosted merge eligibility and CI. Use for stacked-PR status questions or /sc-gh-stack-view; reuse sufficient observations rather than checking layers individually.
entry_point: /sc-gh-stack-view
---

# sc-gh-stack-view

Read-only stack status. One command replaces the "one `gh pr view` per branch"
habit, which never shows the two things that actually break stacks:

1. **Base coherence** - is each layer's base SHA the head SHA of the layer
   below (and the bottom layer's base the trunk head)? Local catalogs and
   git refs provide recorded bases and actual heads without extension views.
2. **Rebase / mergeability** - local content-conflict checks for every
   intended base/head pair and top/trunk, separately from GitHub's
   `mergeable` and `mergeStateStatus` (`CONFLICTING`, `BEHIND`, `DIRTY`,
   `BLOCKED`, `CLEAN`). Clean git merges do not establish hosted policy
   eligibility. Missing evidence is unknown; never text-parse `gh pr checks`.

The script also compares every local head against `origin/<branch>` and the
PR's `headRefOid`, so stale local tracking (someone else rebased the stack) is
caught before anyone runs `gh stack sync` on top of it.

## Step 1 — Verify gh, gh-stack extension, git, python3

Check tool availability once at setup or after a version change/failure.
Local reports need git and Python; gh/auth is needed only for hosted reads,
and the extension only for extension operations:

```bash
which gh && gh --version            # >= 2.0
gh extension list | grep -i stack && gh stack --version   # github/gh-stack v0.1.0
which git && git --version          # >= 2.38
python3 --version                   # >= 3.9
```

If any is missing, probe the usual off-PATH locations first (Claude Code's
bash may not share PATH with the interactive shell):

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && echo "$cli found at: $d/$cli" && break
  done
done
```

Found off-PATH: `export PATH="<dir>:$PATH"` for this session. Still missing,
below the floors (git < 2.38, gh < 2.0, python3 < 3.9), or no gh-stack
extension for an extension operation: read
`references/installation-and-troubleshooting.md` and stop dependent work.
API-free reporting can still expose useful local evidence and unknowns.

## Usage

```
/sc-gh-stack-view [--trunk <branch> | --phase aw] [--stack <number-or-branch>] [--remote origin] [--all] [--full | --json | --compact-json] [--refresh-git] [--refresh-status] [--refresh] [--no-fetch] [--no-pr]
```

Run from anywhere in the repo, normally the main checkout on `develop` or
`main`. The script reads common and legacy worktree catalogs locally, validates
their composition, and derives git state before selecting missing hosted facts.
It never invokes `gh stack view` per worktree. The default view shows every stack that still
has an open layer, on any trunk. `--trunk`/`--phase` narrows to one trunk
(`--phase` is shorthand for `--trunk integrate/phase-<x>`); `--all` also shows
merged/closed stacks. Hidden stacks are counted on a `hidden:` line.
Bare positive ASCII stack numbers take precedence over branch names. Explicit
forms are `--stack number:42`, `--stack branch:42`, and `--stack id:<catalog-id>`.
Use the branch form for numeric or non-ASCII-digit branch names; invalid numeric
selectors fail before hosted acquisition.

Default reports reuse sufficient shared observations and acquire only required
missing or stale remote facts in bounded batches. `--refresh-git` coordinates
one fetch for the selected remote (default `origin`); `--refresh-status` renews
hosted observations; `--refresh` does both. A fetch does not refresh CI or
reviews. `--no-fetch` forbids fetching; `--no-pr` forbids GitHub API calls,
including numeric-identifier resolution. Failed fetches, missing objects or
history, stale hosted facts and unavailable API budget remain explicit unknowns.
Do not repeat reports when existing evidence answers the next operation.

Ordinary membership is locally observed, not certified remotely complete.
For missing structural evidence before a cut or scoped merge, scoped
`--refresh --stack <number-or-branch>` reconciles remote membership (a known
numeric stack number is required). Require `structure_observation.complete == true`
and `freshness == "fresh"`; `--refresh-status` refreshes PR fields only.
Use the compact projection in `../sc-gh-stack/references/recipe-evidence.md`.
An unscoped structural refresh refuses missing numeric identities before any
structural request. Scope it to a known number, or request git/status refresh
without claiming complete remote membership.

Text summaries show at most ten layer rows and count all blockers/unknowns.
`--full` shows all rows without forcing refresh; `--json` is always complete and
includes provenance, observation age, exact SHAs and unknown reasons.
`--compact-json` bounds routine agent output to ten rows per stack, ten stacks and bounded
diagnostics, with total/shown/truncated counts and full-scope verdicts. It does
not change acquisition or certify complete composition; never use its truncated
rows for selecting a top, cut, restack or merge range. Use sufficient
complete evidence or the full-JSON projection above for those operations.
Shared observations live under the common repository's
`.sc/sc-gh-stack/output/`; nonsecret cooldowns under `~/.sc/sc-gh-stack/`.
No tokens are stored. Respect reported cooldowns; do not retry via another protocol.

```bash
python3 .claude/scripts/gh_stack_view.py --trunk develop
```

Resolve `../../scripts/gh_stack_view.py` relative to this skill's directory and
use its absolute path in the example above. This works for Claude, Codex, Cursor,
and Hermes installs, including custom profile roots, and in source checkouts.
Do not choose an unrelated host's stale helper. Claude plugin installs may also
use `$CLAUDE_PLUGIN_ROOT/scripts/gh_stack_view.py`.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | every shown chain coherent and local conflict checks complete/clean; not hosted merge authorization |
| 1 | problems or unknown required local/chain observations |
| 2 | environment/discovery failure, incomplete explicit membership refresh, or snapshot changed; see Errors |

## Errors

Environment/discovery failures produce one `gh-stack-view: ...` stderr line,
never a traceback; `--json` also emits a structured error. Hosted PR-field failures
retain useful local output with qualified observations. An incomplete explicit
membership refresh or changed snapshot refuses the report instead of certifying
old composition.

Both JSON modes report invalid command-line arguments as structured
`INPUT.INVALID_ARGUMENT` errors (exit 2).

- `git` not on PATH or not inside a git repository. `gh` is needed only for requested hosted acquisition; the extension is not needed for reporting.
- Hosted acquisition failure: inspect the reported auth/cooldown reason; `--no-pr` gives an API-free view meanwhile.
- GraphQL errors, null data or non-JSON output: same, with the PR numbers named.
- Malformed or conflicting local catalogs: reconcile tracking using the stale-tracking recipe.
- No open stack found: the line reports how many merged/closed/other-trunk stacks were hidden; use `--trunk`, `--phase` or `--all`.

Non-fatal: a failed requested fetch is qualified explicitly rather than
claiming fresh remote heads. Missing refs/history and hosted failures retain
useful local evidence with unknown reasons.

## Output

The script renders everything. **Paste its output verbatim and unfenced**
(no ``` around it) so the markdown table renders in the terminal. The agent
makes no rendering decisions: no reformatting, no re-summarising, no
substituting its own per-branch lookups. Example (as it should appear):

stack: fix/aw-pool-read-migration -> integrate/phase-aw @ 0e640b20a

| L | PR | rebase | local conflict | GitHub | CI |
|---|---|---|---|---|---|
| 1/2 | #1242 | ✅ | clean | 🚧 | 🌀 |
| 2/2 | #1244 | ✅ | clean | 🚧 | 🌀 |

VERDICT: ✅ COHERENT - observed local/fetched chain; hosted eligibility is separate

| Column | Source | Icons |
|--------|--------|-------|
| L | layer / stack depth, bottom first | |
| rebase | local catalog bases, git heads and remote-tracking refs; hosted `headRefOid` when available | ✅ coherent · ⚠️ drift · 🔄 stale tracking · ❓ unknown · 🏁 merged |
| local conflict | every intended parent/head and combined top/trunk git merge probe | clean · CONFLICT · unknown; not hosted eligibility |
| GitHub | cached/batched `mergeable`, `mergeStateStatus`, draft/lifecycle facts | ✅ observed mergeable, not authorization · 🚧 blocked · ❓ stale/unknown · 🏁 merged |
| CI | hosted `statusCheckRollup.state` with provenance and age | ✅ green · 🌀 running · ⛔ failed, do not enter · ❓ unknown · — none |

`VERDICT` names the branch and the owner action for every problem (SHAs
appear there, not in the table). The lowest OPEN layer (layer 1, or the first
layer above already-merged ones) merely behind trunk is a note, not a problem:
do not rebase a layer whose CI could go green just to catch up with trunk. The legend is printed once at the end. `--json` emits
`stacks[].rows[]`, `problems[]`, `notes[]`, `coherent` plus complete
`stacks[].branches[]` (`name`, actual `head`, `recorded_head`, `base`,
`isMerged`, `isQueued`, `needsRebase`, `pr`) for agents that need to branch on
the result. Inspect exact SHAs and unknown reasons before acting.

`LANDING` is only the top/trunk content-merge prediction plus lower-head
containment. A green `LANDING` is not a whole-stack clean result: require
`local_mergeability.clean == true` for all intended layer pairs and top/trunk,
with no unknown/conflicted pair. Hosted CI/QA still gate the exact top head
only; local cleanliness never substitutes for GitHub's policy enforcement.
Green LANDING also requires fresh positive pushed refs for trunk and every
active layer, never local-head fallback. A fresh negative remote advertisement
(`exists == false`, `absence_fresh == true`) identifies an unpushed layer;
it expires after 60 seconds and never makes an old tracking SHA current.

If you see stale local tracking (🔄, or a false `NOT COHERENT` with `-` rows
right after an `unstack`), that is fixed by the recipe in
`../sc-gh-stack/references/recipe-stale-tracking.md`, not by re-running this
script harder.

## Rules the skill enforces by convention

- This is **the** status call for stacks. Do not fan out `gh pr view` per
  branch; that costs N calls and still misses base coherence and needsRebase.
- The script is read-only. `gh stack sync` and `gh stack rebase` rewrite and
  force-push every layer; only the stack writer runs them, and only with
  sufficient exact-head evidence for every layer (otherwise sync re-rebases stale local
  heads over someone else's push and turns PRs CONFLICTING).
- After a mutation, reconcile affected facts before dependent work. Reuse
  sufficient mutation responses; refresh only missing or invalidated evidence.
- Use one acquisition coordinator and the shared client. Its cooldown cannot
  throttle unrelated direct `gh` processes; no parallel per-worktree status or
  checkout loops and no alternate-protocol retries around a cooldown.
- Draft PRs block `gh stack merge`; the table flags them.

## Related

The `sc-gh-stack` skill (`../sc-gh-stack/SKILL.md`) owns the stacked-PR model,
preconditions, and the create/sync/rebase/merge recipes; this skill only
reports status.
