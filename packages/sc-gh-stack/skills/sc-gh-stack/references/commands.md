# Command guide for gh stack

Read this when you need the exact flags, behavior, or exit codes for a `gh stack` subcommand — the operational reference behind `sc-gh-stack`'s workflow. `gh stack <command> --help` is authoritative for flags; this file adds behavior, side effects, and field-verified failure modes `--help` doesn't cover.

## Non-interactive rules

**Read with the model in mind.** `init`, `add`, `submit`, `sync` and `rebase`
are documented for completeness; the sc-gh-stack recipes use one worktree per
layer, `gh pr create` on the first push and `gh stack link --base`. `link`,
`unstack`, `sync`, `rebase` and `merge` are stack-writer only; `merge`,
`unstack` and `gh pr close` are confirmed with the user unless directed
(`SKILL.md` precondition 10).


Every invocation must be shaped so it cannot prompt or open a TUI — a prompt hangs an agent indefinitely. **Never do:**

- `gh stack view` or `--short` — always `--json` (bare/`--short` render for humans, may open a TUI)
- `gh stack submit` without `--auto` (otherwise opens an interactive title/description editor)
- `gh stack init` / `add` / `checkout` with no argument — always pass branch names / a stack#, PR#, PR URL, or branch
- `gh stack checkout <pr#>` when a different local stack already covers those branches — unbypassable conflict prompt; `gh stack unstack --local` first, then retry
- `gh stack switch` — TUI picker; use `up`/`down`/`top`/`bottom`/`checkout` instead
- `gh stack modify` — TUI-only, no non-interactive form at all
- `gh pr merge` on a stacked PR — refused; use `gh stack merge`

## Quick reference

| Task | Command |
|---|---|
| Create a (multi-layer) stack | `gh stack init auth api frontend` |
| Custom trunk | `gh stack init --base develop branch-a` |
| Add a branch | `gh stack add api-routes` |
| Add + stage all + commit | `gh stack add -Am "message" api-routes` |
| Push branches | `gh stack push` |
| Push + create draft PRs | `gh stack submit --auto` |
| Create PRs ready for review | `gh stack submit --auto --open` |
| Sync (fetch, rebase, push) | `gh stack sync` / `gh stack sync --prune` |
| Rebase (all / upstack / continue / abort) | `gh stack rebase` · `--upstack` · `--continue` · `--abort` |
| View stack (JSON) | `gh stack view --json` |
| Move / jump | `gh stack up [n]` / `down [n]` / `top` / `bottom` / `trunk` |
| Check out by stack#/PR#/branch | `gh stack checkout 7` |
| Link PRs, no local tracking | `gh stack link --base main a b c` |
| Tear down a stack | `gh stack unstack [7]` |
| Merge whole/partial stack | `gh stack merge --yes` / `gh stack merge 42 --yes` |

## init

`gh stack init [flags] <branches...>` — `-b, --base <branch>` trunk (default: repo default branch).

Processes branches bottom to top: existing ones adopted, missing ones created (first from trunk, later ones from the branch before). Checks out the **last** branch listed. Enables `git rerere` — first run under a TTY may prompt; pre-set `git config rerere.enabled true` to skip it.

## add

`gh stack add [flags] <branch>` — `-m, --message <string>`; `-A, --all` (stage all incl. untracked, requires `-m`); `-u, --update` (tracked only, requires `-m`, exclusive with `-A`).

Must run from the **top** branch (or trunk if empty), else exits **5** `can only add branches on top of the stack` — `gh stack top` first. Without `-Am`, uncommitted changes carry onto the new branch (working tree untouched). `add -Am` commits in place (no new branch) when the current branch has no commits yet (e.g. right after `init`). Prefer plain `git add`/`git commit` for deliberate staging; reserve `-Am`/`-um` for simple single-commit layers.

## push

`gh stack push [flags]` — `--remote <name>`. Pushes every active (non-merged, non-queued) branch in one multi-ref push, per-branch `--force-with-lease`. **Not atomic** — one rejection doesn't block others; fix and rerun. Never creates/updates PRs — that's `submit`.

## submit

`gh stack submit [flags]` — `--auto` (required non-interactively), `--open` (new+existing PRs ready for review), `--remote <name>`.

Pushes each active branch sequentially (not atomic — a rejection leaves earlier pushes standing; fix and rerun), creates a PR for every branch lacking one (base = first non-merged ancestor), links into a Stack on GitHub. If every PR is already merged, forks unmerged branches into a **new** stack rooted at trunk. Exits **9** non-interactively if stacks aren't enabled. Title: single commit → its subject/body; multiple commits → humanized branch name; no custom-title flag — `gh pr edit` after.

## link

`gh stack link [flags] <stack# | branch-or-pr>...` — `--base <branch>`, `--open`, `--remote <name>`.

Bottom-to-top arguments; each a branch name, PR#, or PR URL (numeric tries PR# first, falls back to branch). Branch args auto-push (non-force, atomic). Missing PRs are created with correct chained bases; wrong bases on existing PRs are corrected. A numeric first arg is a **stack#** only if that stack exists, then the rest append to its top. Additive only.

**Field note:** always pass `--base <trunk>` explicitly. Without it the bottom PR is retargeted to the repo's default branch, and GitHub then refuses `gh pr edit --base` on it afterward.

**Field note:** `gh stack link <stack#> <new>` appends on TOP and retargets the new PR onto the current top — it cannot insert mid-stack. Attempting one fails with `HTTP 422 PullRequest.base is invalid`, then `new PRs must be added to the top of the existing stack`. To insert: `unstack`, `gh pr edit --base`, full re-link.

**Field note:** `link` never removes a PR — dropping a layer means `unstack` and re-link with the reduced list. Every `unstack` + re-link mints a **new** stack number.

## sync

`gh stack sync [flags]` — `--remote <name>`, `--prune`.

Order: fetch → reconcile GitHub's stack (pulls remotely-added branches; non-interactive divergence aborts) → fast-forward trunk → cascade-rebase (handles squash-merges via `--onto`; conflict restores all branches, exits **3**) → push atomically → refresh PR state → sync stack object (additive, 2+ PRs only) → prune (only with `--prune`, non-interactive).

**Field note:** on divergence, sync prints `ℹ Sync aborted`, changes nothing, and **exits 0** — not a success signal here. Check stderr for that message, or diff `view --json` before/after.

## rebase

`gh stack rebase [flags] [branch]` — `--upstack`, `--downstack`, `--no-trunk` (skip fetch/trunk), `--continue`, `--abort`, `--remote <name>`, `--committer-date-is-author-date`/`--preserve-dates`.

Use `--upstack` after editing a lower layer, or when `sync` reports a conflict. Squash-merged parents detected and replayed via `--onto` automatically. `rerere` (enabled by `init`) auto-resolves previously-seen conflicts. Starting while one is in progress exits **7**.

## view

`gh stack view --json` — always `--json`; bare/`--short` are for humans, may open a TUI.

```json
{
  "trunk": "main", "currentBranch": "api-routes",
  "branches": [{
    "name": "auth", "head": "abc1234...", "base": "def5678...",
    "isCurrent": false, "isMerged": true, "isQueued": false, "needsRebase": false,
    "pr": { "number": 42, "url": "https://github.com/o/r/pull/42", "state": "MERGED" }
  }]
}
```

Fields: `name` · `head`/`base` current/parent HEAD SHA · `isCurrent` · `isMerged` · `isQueued` (merge queue) · `needsRebase` (base not an ancestor) · `pr` (omitted if none; `state` is `OPEN`/`MERGED`/`QUEUED`). `view` refreshes PR state from GitHub best-effort.

## Navigation — up / down / top / bottom / trunk

All fully non-interactive, no flags besides `-h`; `up`/`down` accept a count. Movement clamps to stack bounds; merged branches are skipped, so `bottom` lands on the lowest **unmerged** branch. `gh stack switch` is a TUI picker — don't use it.

## checkout

`gh stack checkout <stack# | pr# | pr-url | branch>` — no flags; relies on `remote.pushDefault` with multiple remotes.

A bare number resolves stack# → locally-tracked PR# → GitHub-discovered PR# → branch name. Stack/PR#/URL fetches from GitHub and sets up locally. If a local stack already covers those branches with a different composition, checkout can't force past it — `unstack --local` then retry.

## unstack

`gh stack unstack [<stack#>] [flags]` (alias `delete`) — `--local` (local only, never contacts GitHub).

Removes the stack **grouping** only — never deletes PRs/branches. No argument → active stack (current branch's). A stack# works from anywhere via the API, tracked or not. Queued/auto-merge PRs stay stacked; if any remain, the whole grouping is kept. Unknown stack# exits **2**.

## merge

`gh stack merge [<stack# | pr#>] [flags]` — `--squash`, `--rebase`, `--merge`, `--merge-method <string>`, `-y, --yes`.

No arg → current stack; PR# → that PR + everything below; stack# → every unmerged PR in it. **All-or-nothing.** Only open/not-draft checked pre-merge; branch protection/rules evaluated by GitHub at merge time. A merge queue on the base overrides: queued instead, queue picks the method (flag ignored with a warning), PRs may land in separate groups.

**Field note:** `merge` blocks the whole set on "not a linear descendant" or "out-of-date with base" — it doesn't selectively skip a bad layer. A scoped `gh stack merge <lower-pr>` can sweep in an upper *empty* draft too (GitHub marks it merged, deletes its branch). Read full `branches[]` from `view --json` before scoping.

**Field note:** `gh pr merge` on a stacked PR: `must be merged using the asynchronous merge REST API`. Working fallback (poll until `"merged"`; an abbreviated SHA fails with the misleading `Pull request head branch was modified` — always pass the full 40-char `headRefOid`):
```bash
gh api -X PUT repos/{o}/{r}/pulls/{n}/merge-async -f merge_method=merge -f sha=<FULL headRefOid>
gh api repos/{o}/{r}/pulls/{n}/merge-async/<uuid>   # poll
```
After the parent merges, GitHub retargets/rebases the child branch within ~30s; once trees are confirmed identical, `git fetch && git reset --hard origin/<child>` — never force-push over it.

**Field note:** to check whether a PR's base was ever silently retargeted, filter `/events` (not `/timeline`, which misses it): `gh api repos/{o}/{r}/issues/{n}/events | jq '.[] | select(.event=="base_ref_changed")'`.

## Output conventions

Status messages go to **stderr** (`✓`/`✗`/`⚠`/`ℹ` prefixes); data output (`view --json`) goes to **stdout**. Pipe `2>/dev/null` to isolate data.

## Exit codes

| Code | Meaning | Agent action |
|---|---|---|
| 0 | Success | Proceed — but see sync divergence field note |
| 1 | Generic error | Read stderr |
| 2 | Not in a stack / unknown stack# | `gh stack init`, or check the number |
| 3 | Rebase conflict | Resolve, `git add`, `gh stack rebase --continue` |
| 4 | GitHub API failure | Check `gh auth status`, retry |
| 5 | Invalid arguments | Fix invocation (e.g. `add` off the top branch) |
| 6 | Disambiguation required | `gh stack checkout <non-shared-branch>` first |
| 7 | Rebase in progress | `--continue` or `--abort` |
| 8 | Stack file locked | Wait (~5s timeout), retry |
| 9 | Stacked PRs unavailable | Tell user; repo admin must enable |
| 10 | Modify recovery required | `gh stack modify --abort` (never invoke `modify` yourself) |

## Parsing `--json` with jq

```bash
output=$(gh stack view --json)
echo "$output" | jq '[.branches[] | select(.needsRebase)] | length'      # needs rebase?
echo "$output" | jq -r '.branches[] | select(.pr.state=="OPEN") | .pr.url'
echo "$output" | jq -r '.branches[] | select(.isMerged) | .name'         # merged branches
echo "$output" | jq -r '.currentBranch, .trunk'
echo "$output" | jq '[.branches[] | .isMerged] | all'                    # fully merged?
```

## Known limitations

1. Stacks are strictly linear (one parent, one child max) — use separate stacks for parallel work.
2. Stack disambiguation (exit 6) has no bypass flag.
3. Multiple remotes need `remote.pushDefault` or `--remote` (`push`/`submit`/`sync`/`rebase`/`link` only — `checkout`/`modify`/`trunk` have none).
4. `checkout` by branch name only resolves locally tracked stacks — use a stack#/PR# to pull from GitHub.
5. `submit` generates title/body from commits, no custom-title flag — `gh pr edit` after.
6. `link` never removes a PR and cannot insert mid-stack (see field notes above).
