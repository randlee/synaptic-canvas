# sc-gh-stack: local discovery and API efficiency plan

Date: 2026-10-14 (America/Los_Angeles)
Status: requirements/design with an anchor-aligned implementation sprint;
all ten planning-question sets calibrated and Sprint E1 passed its planning
gate at production threshold 0.6. Implementation has not started.
The [anchored intent](../doc/plan/sc-gh-stack-api-efficiency/intent.md) governs
further design. Recipe strategies and intended outcomes are preserved, while
equivalent git-call substitutions are in scope. Tests are required for
the redesign; live GraphQL verification is quota-constrained. This session is
design work, with no implementation or live GitHub experiments. Acceptance
criteria below describe future implementation verification.
Branch: `feature/sc-gh-stack-api-efficiency`
Base: `origin/develop`, `fc702b1` at worktree creation.
Scope: design for `packages/sc-gh-stack` scripts and the `sc-gh-stack` and
`sc-gh-stack-view` skill recommendations. Recipe changes may optimize git calls
without changing their stacking strategies or intended outcomes.

The complete implementation sprint for the planning gate is
[Sprint E1](../doc/plan/sc-gh-stack-api-efficiency/sprint-E1.md), enumerated by
the [phase index](../doc/plan/sc-gh-stack-api-efficiency/plan-phase-api-efficiency.md).
This document retains the detailed call inventory, source evidence, alternatives
and engineering rationale; none is silently truncated into a review request.

## Objective and boundaries

Preserve useful stack coherence, conflict detection, CI visibility, and landing
verification while eliminating repeated remote discovery and redundant status
reads. Optimize both GitHub quota usage and agent context/output tokens under
many worktrees, stacks of 100+ layers, frequent edits, and concurrent readers.

This document follows the requested order: (1) information requirements for
calls, (2) current methods, (3) alternatives with current local refs, (3.b)
alternatives with stale refs, and (4) recommended fixes and validation.

Do not replace the extension's mutation implementation in this change. Do not
rewrite branches, import stacks, or edit upstream catalogs as a side effect of
status. Do not treat an absence of API calls as proof of GitHub merge readiness.
No upstream fork, service, webhook deployment, or additional dependency is
required for the first implementation.

## Evidence and terminology

Reviewed package scripts at `fc702b1`; their runtime code is unchanged from the
initial checkout `b063b85`. Installed extension reports v0.1.0. Upstream was cloned
to `/Users/randlee/github/gh-stack`; current checkout is v0.2.1, `29a36d3`.
Historical behavior was also checked with `git show v0.1.0:<path>`.

Upstream source links are pinned to a version so future changes do not silently
change the evidence:

- [v0.1.0 view implementation](https://github.com/github/gh-stack/blob/v0.1.0/cmd/view.go)
- [v0.1.0 PR refresh and concurrency](https://github.com/github/gh-stack/blob/v0.1.0/cmd/utils.go)
- [v0.1.0 API implementation](https://github.com/github/gh-stack/blob/v0.1.0/internal/github/github.go)
- [v0.2.1 catalog schema](https://github.com/github/gh-stack/blob/v0.2.1/internal/stack/schema.json)
- [v0.2.1 legacy migration discovery](https://github.com/github/gh-stack/blob/v0.2.1/internal/stack/migration.go)

“Current git refs” means local remote-tracking refs were successfully fetched
for the relevant remote/refspec at a recorded time. It does not mean the local
branches were reset, the stack catalog matches GitHub, or CI/reviews are fresh.
“Local” means no network. “Git refresh” means git transport only. “Remote status”
means GitHub API data. These must be separate modes and freshness dimensions.

Quota points, GraphQL nodes, HTTP requests, and agent tokens are different units.
GitHub documents a typical user primary GraphQL budget of 5,000 points/hour,
secondary GraphQL limits of 2,000 points/minute, and additional concurrency/CPU
limits. Mutation-free GraphQL requests generally cost one secondary point;
primary query cost depends on connections and has a minimum of one. A query's
node count is not its point cost. Use actual response headers and optionally
`rateLimit.cost` in an existing query to measure costs. REST has its own primary
budget and secondary limits; switching protocols does not eliminate throttling.
[GitHub rate-limit rules](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)

## 1. Information requirements for all calls

### 1.1 Required data and freshness

| ID | Information / consumer | Required fields or evidence | Freshness requirement | Locally derivable? |
|---|---|---|---|---|
| R01 | Tool/environment preflight | git availability/version; extension availability/version only for extension operations | Once per executable/version change or failure | Yes; no auth/network probe for local reporting |
| R02 | Repository identity | common git directory, selected remote, host, owner, repo | Recompute when remote/config changes | Yes, from git/config/catalog; support SSH aliases and explicit overrides |
| R03 | Worktree ownership | paths, branches, detached/missing worktrees | At report time | Yes, `git worktree list --porcelain -z` and git directory resolution |
| R04 | Tracked stack structure | identity/number, trunk, ordered branches, PR numbers, recorded base/head | At report time from catalog; remote reconciliation explicit | Yes for tracked stacks; remote-only stacks need API |
| R05 | Actual local and fetched heads | local branch SHA, remote-tracking SHA, trunk SHA | At report time; remote observation timestamp retained | Yes after fetch; catalog heads are historical observations |
| R06 | Chain coherence / rebase hint | recorded base vs parent head; parent ancestor of child; missing refs | Keyed to exact compared SHAs and catalog fingerprint | Yes; ancestry and recorded-base equality are separate results |
| R07 | Pushedness | local vs fetched remote head; remote ref absence | Requires successful relevant fetch to claim current remote state | Yes with freshness qualification |
| R08 | Local conflict prediction | merge-tree exit status for each relevant base/head pair and top/trunk | Exact immutable SHA pair and git merge semantics | Yes; no GitHub policy inference |
| R09 | PR identity and lifecycle | number, head/base branch and SHA, OPEN/CLOSED/MERGED, draft | Cached for routine reads; refreshed after lifecycle/base mutations | Catalog partly; authoritative current state needs API |
| R10 | Remote stack membership | stack number/ID, ordered PR numbers, trunk, remote head refs/SHAs | Refresh after link/unstack/remote change or explicit request | Catalog snapshot only; authoritative reconciliation needs API |
| R11 | CI summary | rollup state, observed head SHA, observation time | Refresh on demand while running; head change invalidates old-head result | No; checks may change with unchanged git refs |
| R12 | Reviews and GitHub readiness | Only readiness fields consumed by the requested report or authorized landing path | Time-sensitive; reuse sufficient observations and the extension's own preflight instead of adding a blanket readiness scan | No; local clean merge is only conflict evidence |
| R13 | Merge execution | selected PR range, full expected SHA when supported, merge method, queue requirements | Fresh for the authorized operation | GitHub required; delegate execution to extension/API |
| R14 | Async operation completion | UUID, pending/success/failure and returned SHA/message | Poll only the outstanding operation with deadline/backoff | API required; refs alone cannot identify operation outcome |
| R15 | Human/agent report | scope, issues, changed rows, timestamps, snapshot ID, unknown reasons | Render an existing snapshot without additional I/O | Yes |

For every field, preserve source, observation time, compared head/base SHA where
applicable, and whether the value is fresh, cached, stale, or unknown. Missing
data is not success. A field unused by a verdict or requested report should not
be fetched just because an upstream response supports it.

### 1.2 Operation requirements, including writes

| Operation | Minimum information before execution | Verification after execution |
|---|---|---|
| Local status / dispatch context | R02–R08; optional cached R09–R12 | None; rendering cannot refresh |
| Cut branch/worktree | Intended parent SHA and ownership; preserve existing workflow freshness requirements rather than adding a new pushedness preflight | Local ref and ancestry check; no full CI scan |
| Pre-link check | Ordered branches/PR mapping, fetched heads, chain/local conflicts; lifecycle if needed | One scoped outcome for the logical link operation |
| PR create / ready / edit / close | Explicit target, intended base/state, existing observed head | Reuse mutation response; invalidate only affected metadata |
| Link / unstack / restack | Scope, order, intended bases, fresh relevant heads, known lifecycle | Reconcile affected stack once after the operation sequence |
| Checkout/import | Actual navigation/import need and worktree ownership | Local ownership/catalog validation; never invoke to obtain status |
| Rebase / sync / submit | Existing authorization, ownership, intended rewrite, relevant fetched refs | Local chain/head validation plus scoped remote outcome |
| Merge | Exact range and expected heads; only additional readiness information required by the existing landing workflow and not already supplied by its executor | Poll returned operation; reuse response and verify the affected outcome without a full-stack rescan |
| Environment installation/auth recovery | Failure-specific evidence | Run auth/install commands only when needed, not every status |

The skill's “QA/CI on the top” workflow is not permission to report lower layers
as eligible: GitHub may enforce requirements on every PR in a stack. Retain
server enforcement as final authority. Do not introduce a second wrapper scan
of all policy/CI/review fields when the existing executor already performs the
necessary checks. Local conflict evidence and hosted eligibility remain distinct.
[Stack rules](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests)

## 2. Current methods and amplification

### 2.1 Script call inventory

Paths below are relative to `packages/sc-gh-stack/scripts/`.

| Site / method | Current call(s) | Data requirement | Problem / cost behavior |
|---|---|---|---|
| `gh_stack_view.py:preflight` | `which` via Python, `gh stack --help`, `git rev-parse --git-dir` | R01 | Repeated subprocess overhead; extension should not be needed to read local catalog |
| `worktree_paths` | `git worktree list --porcelain`, `git rev-parse --show-toplevel` | R03 | Local; line-based parser has path edge cases; cwd sorting not needed for shared catalog |
| `stack_json_at` | `gh stack view --json` in each worktree | R04, R09, R10 | Hidden API refresh and catalog save; not a purely local reader |
| `discover_stacks` | Four parallel extension processes; dedup/filter afterward | R04 | Worktrees multiply scans of identical stacks; trunk filter is too late |
| `run_report` | One `git fetch --quiet origin` unless disabled | R05, R07 | Shared refs make per-worktree fetching unnecessary; origin hardcoded |
| `pr_details` repository resolution | `gh repo view --json owner,name` | R02 | Additional remote lookup for identity already available locally |
| `pr_details` detail batch | Aliased `gh api graphql` for all selected PRs, including merged layers | R09, R11, R12 | Good batching, but repeats discovery data and lacks cross-invocation reuse |
| Detail fields | `number isDraft mergeable mergeStateStatus baseRefName headRefOid reviewDecision state commits(last:1){...statusCheckRollup{state}}` | R09–R12 | `reviewDecision` is requested but currently not consumed by rendered verdicts |
| `build_rows`, shared helpers | Repeated `git rev-parse origin/<branch>` and `merge-base --is-ancestor` | R05–R07 | No API cost; batch ref reads and memoize immutable comparisons |
| `landing_verdict` | Local ancestry checks and `git merge-tree --write-tree` top/trunk | R08 | Already avoids GitHub; currently answers combined landing conflicts only |
| `gh_stack_chain_check.py:preflight` | `which`, git repository/remote checks | R01, R02 | Local and appropriate; remote configurable in proposed implementation |
| `list_prs` | `gh pr list --state open --limit 500 --json ...` | R09 | Repository-wide list for a scoped chain; one CLI process may paginate HTTP requests |
| `view_pr`, `resolve_layers` | Individual `gh pr view N --json ...` for missing numeric IDs | R09 | Per-PR fallback; masks auth/throttle failures as “not found” |
| `run_check` with `--no-pr` | Skips list but still resolves numeric IDs remotely | R09 | Offline contract violated, possibly even when preflight skips requiring gh |
| `run_check` fetch | One git fetch unless disabled | R05, R07 | On failure warns but still evaluates refs without freshness metadata |
| `evaluate`, `merge_clean` | Origin ref reads, ancestry, merge-tree | R05–R08 | Local; reuse snapshot instead of repeating pre-link work |
| `gh_stack_shared.py:run` | subprocess timeout; no automatic retry | All | No wrapper retry storm, but no request-budget controller |
| `hint_for` | Fixed 30-minute stop advice, recommends `--no-pr` | Recovery | No persisted cooldown; recommended mode is not actually API-free |

`gh stack view --json` in v0.1.0 and v0.2.1 calls `syncStackPRs` before
rendering and saves metadata. A remote stack refresh calls REST `ListStacks`,
then GraphQL `FindPRByNumber` once per remote PR. The fallback also queries
branches individually and may do a second lookup for a closed/missing tracked
PR. Each extension process permits six concurrent requests. Neither version
has a local-only view flag. JSON includes `needsRebase` computed by git ancestry,
but does not include `mergeable` or `mergeStateStatus`; our wrapper adds those.

Let W be worktree views with tracked stacks, N_i the PRs fetched by view i, and
U unique selected PRs. Discovery GraphQL traffic is approximately sum(N_i), plus
fallback lookups; the wrapper adds repository resolution and its detail batch.
With W views of the same N-PR stack, this is O(W*N), not O(1). Four processes
times six internal workers gives up to 24 concurrent API requests per wrapper,
before other agents/repositories sharing credentials are considered.

A mocked check reproduced 60 extension calls yielding one deduplicated stack.
If each view refreshes 60 PRs, discovery implies about 3,600 GraphQL requests.
This is a modeled case, not a measurement of the reported Phase K incident.
Binary strings alone do not establish request counts or quota consumption.

### 2.2 Skill, recipe, and extension calls

| Pattern | Current location / behavior | Recommended treatment |
|---|---|---|
| Full status before/after writes and before dispatch | Main skill Step 2 and workflow step 8 | Reuse scoped observations; reconcile the affected outcome only if the write response and existing observations are insufficient |
| Repeated finish/paste requirement | Link/restack/other recipe endings | Reuse sufficient observations or equivalent cheaper checks; preserve the verification goal and required evidence, not redundant remote reads |
| Extra `gh stack view --json` to inspect branches | Restack/landing recipes | Use local discovery for equivalent branch information; preserve the strategy for challenging conditions |
| `gh stack checkout` as recovery/status preparation | Stale-tracking/link recipes | Keep checkout where navigation/import recovery is required; replace a status-only use with equivalent local discovery |
| `gh stack link` full ordered list on each append | Link recipe | Preserve recipe operations; account for their necessary API cost |
| `gh pr create/edit/ready/close` | Link/restack/landing recipes | Preserve requested writes; reuse returned identifiers and changed state |
| `gh pr view --json headRefOid` | Async landing fallback | Reuse a sufficient head observation or targeted REST while preserving exact-head verification |
| `gh api .../merge-async` PUT/GET | Landing fallback | Preserve authorized execution, completion/failure detection, and recovery goals; poll only the outstanding operation |
| `gh pr list --state merged --limit 10` | Post-merge verification | Verify the affected PR/range through scoped observations rather than unrelated recent merges; preserve the landing-verification goal |
| `gh stack sync/rebase/submit/merge/unstack` | Command guide and recipes | Real operations with their own API traffic; do not wrap each with duplicate scans |
| `gh auth status`, extension list/install/upgrade | Installation/recovery guidance | Failure-driven/setup only; do not run routinely for local status |

Upstream checkout can fetch PR details per PR; link resolves supplied PRs and
can re-fetch them to repair bases; sync/submit can refresh PR metadata multiple
times; merge reads remote stack/configuration and polls async completion.
The exact path depends on command arguments, version, and remote state. Count
these as separate mutation-workflow costs in instrumentation; do not claim all
verbs always issue the same GraphQL calls. Source audit covers
`cmd/{checkout,link,sync,submit,unstack,merge}.go` and `internal/github/merge_async.go`.

## 3. Alternatives when relevant git refs are current

### 3.1 Local discovery algorithm

1. Resolve repository root, common git directory, per-worktree git directories,
   selected remote and repository identity using git commands/config only.
   Use git-resolved paths; `.git` may be a file, and separate git dirs are valid.
2. Read `<common-dir>/gh-stack`. For v0.1.0 compatibility, inspect actual
   worktree git directories for legacy `gh-stack` catalogs as well. Do not infer
   a worktree path from an administration directory. Do not invoke upstream
   loaders that can migrate state as a side effect.
3. Validate schema version 1, shapes, PR numbers, and branch references.
   Missing catalogs mean “no locally tracked stack,” not “no GitHub stacks.”
   Unsupported/malformed catalogs produce actionable local errors.
4. Normalize catalogs and deduplicate identical stacks by repository plus
   remote identity when present. Treat conflicting IDs/orders/membership as
   unresolved; do not silently choose the longest prefix. Legacy prefix union
   is only allowed with demonstrated identity and compatible ordered content.
5. Apply requested trunk/stack/branch filters before any optional API operation.
   Shared catalogs allow discovery even if no layer is currently checked out.
6. Batch local and remote-tracking ref reads (`git for-each-ref` or equivalent).
   Keep recorded catalog base/head distinct from actual current ref SHAs.
7. Compute ancestry and conflict results keyed to exact immutable SHA pairs.
   Recheck catalog/ref fingerprints at report completion; if changed, bounded
   local retry once or return “snapshot changed,” never mix epochs silently.

Local reporting must neither save/migrate the extension catalog nor acquire
upstream mutation locks for the duration of git computations.

### 3.2 Same information through cheaper sources

| Information | Local/current-ref alternative | Remaining remote requirement |
|---|---|---|
| Stack/layer/PR identity | Catalog, filtered and deduplicated locally | REST reconciliation only for absent/stale membership |
| Repo host/owner/name | Catalog repository identity and configured remote URL | Explicit override for ambiguous aliases/forks; no default API probe |
| Recorded base vs parent | Catalog plus actual refs | None |
| `needsRebase` ancestry | `git merge-base --is-ancestor parent child` | Lifecycle/queue state can change effective parent; mark cached lifecycle |
| Pushed heads | Compare local ref to fetched selected-remote ref | Fetch must cover refs and have successful timestamp |
| Layer conflict prediction | `git merge-tree --write-tree baseSHA headSHA` | None for local prediction; error other than 0/1 means unknown |
| Combined landing conflicts | Every open layer contained in top, then merge-tree trunk/top | Does not establish every intermediate GitHub merge is allowed |
| Lifecycle/draft/head metadata | Cached catalog/API snapshot | REST stack detail or targeted PR GET to refresh |
| CI/reviews/queue/policy | Reuse clearly timestamped API snapshot | One scoped GraphQL batch when freshness is required |

`merge-tree` uses local git behavior/attributes; shallow/missing history,
unavailable merge drivers, and GitHub implementation differences limit parity.
It may write tree objects, but does not change refs, index, or working files.
Describe the result as “local merge clean/conflicting,” separate from “GitHub
ready/blocked/unknown.” An ancestor result alone is not conflict detection.

### 3.3 REST versus GraphQL choices

Use `GET /repos/{owner}/{repo}/stacks/{number}` for an explicit structural
refresh. The response contains ordered PRs, lifecycle/draft, head refs/SHAs,
and trunk; it can replace many per-PR lookups. It does not supply every PR's
actual current base, CI/review rollup, or merge queue/policy state. Do not infer
these missing values from array order. List stacks only for remote discovery;
follow pagination links and distinguish 404/unavailable from an empty result.
[Stacks REST contract](https://docs.github.com/en/rest/pulls/stacks)

For one or a few missing PR mappings/base/head fields, use targeted PR REST GETs
or a filtered branch lookup. Preserve fork owner identity when applicable;
never scan 500 unrelated open PRs by default. For many missing PRs, an aliased
GraphQL batch may use fewer total requests than REST per PR.
[Pull request REST contract](https://docs.github.com/en/rest/pulls/pulls)

Retain GraphQL for requested bulk `statusCheckRollup`, `reviewDecision`, and
GitHub readiness fields. REST CI needs both check runs and legacy commit
statuses, with pagination, so it is not a drop-in one-call rollup replacement.
Fetch only fields actually used by the selected report/verdict.
[Check runs](https://docs.github.com/en/rest/checks/runs),
[commit statuses](https://docs.github.com/en/rest/commits/statuses)

Use conditional REST requests with stored ETags where supported. Authenticated
304 responses can avoid primary REST charges, but still entail network traffic;
do not describe them as free of secondary-limit impact. Reuse mutation response
fields before considering any follow-up GET.
[REST best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

## 3.b. Alternatives when local refs or metadata are out of date

| Situation | Action | What remains unknown |
|---|---|---|
| Fetch age unknown/expired | One coordinated git fetch for the selected remote and relevant refspec; then recompute local snapshot | Current API lifecycle/CI/reviews |
| Local branch behind/ahead/diverged | Compare local/fetched SHAs; report exact relationship | Never reset/rebase/checkout to make a status report work |
| Fetch fails/offline | Use cached refs with age/error; current pushedness becomes unknown | Do not label stale remote refs “fresh” |
| Shallow clone/missing objects | Report incomplete history; explicit git refresh may deepen/fetch necessary history within a bounded policy | Ancestry/conflicts until objects available |
| Catalog stale after remote restack | One scoped REST stack refresh; reconcile in wrapper snapshot | Do not write upstream catalog/import branches during status |
| Stack number no longer exists | Use known PR's filtered stack lookup once to find replacement; distinguish permission/API failure | Missing remote stack is not permission to unstack/recreate |
| No catalog but explicit remote discovery requested | REST stack list/detail, scoped and paginated; compute locally once necessary refs exist | Local tracking remains absent unless user separately requests import |
| Numeric PR under `--no-pr` | Resolve catalog/cache mapping or return local actionable unknown | Never quietly call `gh pr view` |
| Git refs unchanged but CI still running | Refresh only requested PR/CI fields after status TTL | Git SHA equality cannot prove status unchanged |
| Approval/draft/queue changes without commits | Refresh only consumed policy/lifecycle fields not already supplied by sufficient observations or the executor's required preflight | Git fetch cannot refresh these facts |
| Rate limit reached | Record shared cooldown; return cached/local results with age, or actionable incomplete landing result | Do not retry through REST as an automatic quota bypass |

One successful fetch updates shared refs for all linked worktrees. Do not fetch
per worktree. A concurrent operation can move a ref immediately after fetch;
snapshots pin observed SHAs, and merge execution must retain expected-head
checks/server validation rather than promise a race-free preflight.

## 4. Recommended fixes for heavy usage

### 4.1 Runtime and cache contract

Proposed CLI behavior (new option names remain implementation proposals):

- Default: local discovery and derivation first, then reuse sufficient cached
  observations. If the requested report needs missing or stale remote fields,
  acquire only those fields through the cheapest suitable scoped source.
  Preserve the report's useful information rather than making users opt in
  to every remote column. A sufficient warm snapshot makes no network calls;
  a cold or stale remote-dependent report may make bounded calls.
- `--refresh-git`: fetch once, then local analysis; no API requests.
- `--refresh-status`: refresh scoped GitHub observations; does not imply fetch.
- `--refresh`: combine those two explicit refreshes.
- `--no-pr`: strict zero-API contract in every code path, including numeric IDs.
  `--no-fetch --no-pr` is fully offline; retain `--no-fetch` compatibility.
- `--stack`, existing `--trunk`/`--phase`: scope discovery and remote selection.
- `--json`: stable structured snapshot; `--full`: full table; concise summary
  and changed/problem rows by default. Rendering never invokes a subprocess.

Do not impose an offline-only default or a requirement that every operation
work without API budget. Update command/skill documentation for observation
reuse and freshness, and retain the meaning of existing `--no-fetch` and
`--no-pr` controls. Rendering an already acquired snapshot remains I/O-free.

Cache design: repository-shared snapshots live under the canonical repository's
`.sc/sc-gh-stack/output/` per storage conventions, keyed by common git directory,
host/repository, auth context, scope, and schema version. Resolve the canonical
root from git worktree ownership; support separate git dirs/explicit override.
Do not place independent caches in every worktree or modify `gh-stack` itself.
Ignore generated artifacts in git. This introduces runtime state where the
current skill says there is none; update that claim explicitly.

Pin each snapshot to catalog fingerprint and local/remote SHA maps. Suggested
initial TTLs are policy defaults to validate, not GitHub guarantees: share git
refresh observations for 60 seconds, running CI for 60 seconds, other API status
for 120 seconds. Cache local merge computations by SHA pair and git semantics,
bounded by entry count. CI success may change on rerun at the same SHA; reviews
and lifecycle may change without any SHA change. Do not cache these indefinitely.

Coalesce concurrent refreshes with a short per-repository lock and atomic
snapshot replacement; waiters consume the completed result or report bounded
in-progress/stale state. Recheck scope after locking so disjoint requests are
not incorrectly treated as satisfied. Invalidate changed PR/base/membership
entries after known writes, without discarding unrelated observations.

Serialize wrapper API requests and use bounded batches (initial cap 50 unique
PRs, measured and adjustable). Stop a sequence on throttle/auth errors; handle
GraphQL errors even with HTTP 200/partial data. No automatic per-PR fallback
after a failed batch. Missing individual data stays unknown.

Persist cooldown/rate observations at user scope under `~/.sc/sc-gh-stack/`,
partitioned by host and nonsecret auth identity, so participating repositories
share pressure signals. Do not record tokens or secret-bearing commands. Exact
credential fingerprints may separate multiple tokens for one quota-sharing
user; prefer a resolved user identity when already available, without adding
an auth API lookup for each report. Unknown identity uses conservative host
coordination. External gh/agents remain outside this controller; state that
limitation instead of promising a global quota guarantee.

Honor `Retry-After`, primary reset headers, and GitHub's documented minimum
secondary wait; use bounded exponential backoff with jitter and deadline.
Record next permitted refresh time. Normal reporting returns local/cached data
instead of blocking for the cooldown. Explicit landing verification returns
incomplete if fresh required observations cannot be obtained.

### 4.2 Workflow and output token reductions

Revise the top-level skill recommendations and script behavior to reuse
observations for the same operation instead of repeatedly gathering identical
data. Preserve established recipes' stacking strategies and intended outcomes,
including challenging-condition recovery. Equivalent git-call substitutions
are permitted; document each substitution's original goal, replacement evidence,
and failure/recovery equivalence. A repeated wrapper invocation must not imply repeated
network discovery; distinguish rendering a snapshot from acquiring observations.
Do not bypass existing authorization or branch ownership requirements.

Record a snapshot ID, scope, head SHAs, observation times, verdict, and
changed/problem rows. Top-level recommendations can reference existing results
instead of mandating additional reads or full-table output. Full tables/JSON
remain available when they supply necessary recipe evidence. Do not replace a
necessary verification outcome with a merely shorter report. Wrapper fanout
removal delivers savings even before equivalent recipe-call substitutions.

Suggested concise output:

```text
stack #42: 120 layers; local chain clean; local top/trunk merge clean
GitHub: cached 75s, 2 pending; snapshot abc123; heads unchanged
changed: #123 CI pending -> success
```

Summaries must distinguish an entirely clean scope from hidden failures/unknowns.
Keep counts and explicit truncation; never hide a blocking layer merely to save
tokens. Bound conflict messages and repeated notes in default output. Avoid
dumping PR bodies, raw API payloads, and expanded command output into agent
context. Debug/request metrics are opt-in and separate from normal reports.

Bound async polling by deadline and terminal states, honor retry guidance, and
poll only the returned UUID. Never run full-stack discovery/status in its loop.
Treat full restack/import as real operations with their own costs. Preserve
the documented recipe strategies and outcomes; necessary writes still consume quota and
must be included in the design's request accounting.

### 4.3 Implementation sequence and dependencies

| Task | Deliverable | Depends on | Unblocks |
|---|---|---|---|
| T1 | Local catalog/ref snapshot reader with legacy fixtures, schema validation, identity/conflict handling | This requirements/design review | T2, T3, T4 |
| T2 | Shared local ancestry/conflict evaluator; separate clean merge from GitHub readiness | T1 | T4, T6 |
| T3 | Scoped REST/GraphQL adapter, strict offline paths, correct API error classification | T1 | T4, T5 |
| T4 | Snapshot cache, refresh coalescing, freshness/invalidation, cooldown and counters | T1–T3 | T5, T6 |
| T5 | View and chain-check CLI integration, filtered/delta/full output | T3–T4 | T6, T7 |
| T6 | Revise skill recommendations and equivalent recipe git calls around observation reuse; preserve stacking strategies, outcomes, and challenging-condition handling | T2, T4, T5 | T7 |
| T7 | Scaling/concurrency/call-budget verification and package release documentation | T5–T6 | Implementation handoff/release |

First ship discovery/offline correctness before tuning API transport. Keep
compatibility rendering as a full-output option. No version bump or production
code edits are part of this planning-only change. Backlog/beads conversion and
independent design reviews remain follow-up work, not claimed as completed.

### 4.4 Acceptance criteria and evidence to collect

1. Discover equivalent common/legacy fixtures from any branch with zero gh
   processes, API calls, catalog writes, or worktree switches. Report conflicting
   definitions and unsupported schemas explicitly.
2. Both scripts with `--no-pr` make zero API calls, including numeric PR args,
   missing mappings, malformed catalogs, partial failures, and cache misses.
3. Locally sufficient reports and warm reusable snapshots make zero network
   requests. Missing required remote fields trigger scoped acquisition, not
   an offline-only default. Git-refresh-only mode performs at most one
   coordinated fetch per remote freshness interval and zero API calls.
4. For W=1/10/60 worktrees exposing the same 120 PRs, a mocked cold status
   refresh sends at most ceil(120/50)=3 explicit GraphQL detail requests when
   all 120 require those fields, zero per-worktree views,
   and zero repository-identity API calls. A requested structural refresh adds
   one targeted REST stack GET; extra pagination/missing mappings are separately
   counted. These are wrapper budgets, excluding extension mutations.
5. Ten concurrent readers for the same scope produce one shared refresh sequence;
   warm repeats within TTL make no network requests. Different scopes/auth
   contexts cannot reuse incomplete or unauthorized cached data.
6. Ref changes, base changes, membership changes, CI reruns, and review changes
   invalidate or expire the right observations. A failed fetch never produces
   current remote-head claims; a cached green CI never proves fresh readiness.
7. Local conflict fixtures cover clean/conflicting merges, ancestry-only cases,
   merged parents, missing objects, shallow history, missing refs, and unexpected
   merge-tree exit codes. With sufficient local state, evaluate the intended
   base/head merge pair for every layer in the requested stack and the combined
   top/trunk pair. Report each result or explicit unknown and aggregate without
   hiding intermediate conflicts. Ancestry or a clean top/trunk result cannot
   substitute for every-layer conflict results or prove hosted eligibility.
   Include an intermediate-layer conflict/unknown fixture whose top/trunk result
   is clean. Local evaluation never changes refs/index/worktree files.
8. Simulated 403/429, HTTP-200 GraphQL errors/partial data, auth failures,
   Retry-After, resets, and timeouts stop further requests appropriately and
   preserve useful local output. Cooldown is shared across participating repos.
9. Landing preserves exact observed heads and server-side enforcement. Any
   wrapper-owned preflight read has a named consumer and is not duplicated by
   a sufficient existing observation or the executor's own required preflight.
10. Async polling is bounded and terminal failures stop it; no status/discovery
    calls occur inside the poll loop. Transport changes cannot repeat writes.
11. Measure API requests by endpoint/operation, GraphQL reported cost, remaining
    budget, cache hit/coalescing counts, fetch count, output bytes, and token
    count using a named tokenizer when available. Do not infer tokens from lines.
12. Synthetic 120-layer unchanged output includes at most 10 layer rows plus
    scope/counts/freshness; full mode returns all rows. All blockers/unknowns are
    counted, and truncation is explicit. Record baseline versus new output size.
13. For each recipe git-call substitution, record the original stacking goal
    and challenging-condition strategy, the replacement evidence/action, and
    equivalence tests for success and recovery/failure paths. Cheaper calls
    cannot remove a necessary outcome check or turn an unknown into success.

Use mocked transports and local git fixtures for deterministic call budgets;
do not spend production quota on a load test. An optional explicitly requested
small live smoke check can confirm schema/headers later. Tests must inspect
actual subprocess/request counts so “one CLI invocation” cannot hide pagination
or extension fanout again.

The comparison baseline is the reviewed scripts at `fc702b1`, not an unspecified
future version. Replay the same logical operation, stack/ref snapshots, worktree
inventory, requested fields, and cold/warm cache condition against both paths.
Record timestamped requests, counts by endpoint, maximum requests in flight,
and counts within the provider's documented burst windows. Request counts,
primary GraphQL cost, secondary pressure, and agent output tokens are separate
measurements; a smaller GraphQL total does not excuse an equivalent REST
fanout or a more concentrated request burst. The proposed three-batch bound
is a mocked request-count target, not a claim of measured live quota savings.

## Remaining implementation decisions

Validate the proposed 50-PR batch size and TTLs with fixtures and response
metrics. Confirm GitHub Enterprise host/API capability handling and the stable
auth-identity mechanism before enabling cross-repository coordination. Preserve
unknown queue state when operating offline; the catalog does not persist it.
These are bounded engineering choices, not reasons to retain remote discovery.
