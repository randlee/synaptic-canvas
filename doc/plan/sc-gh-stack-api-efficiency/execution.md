# E1 implementation evidence

Implemented and pushed on `feature/sc-gh-stack-api-efficiency` at `dc526cc`;
baseline `fc702b1`.
The locked intent/anchors and the reviewed sprint remain the design authority.
This execution record supersedes their historical planning-only status, not
their requirements. No live GitHub API or load test was run.

| Task | Delivered evidence |
|---|---|
| T1 | Common/legacy catalog reader, locally parsed remote identity, batched refs, scope-first selection, conflicting branch/PR identity rejection |
| T2 | Every active intended parent/head pair plus top/trunk; separate ancestry, recorded base, pushedness and hosted eligibility; unknowns retained |
| T3 | Small targeted REST metadata reads; bulk metadata/status and missing branch mappings in serial batches of at most 50; no repository-wide PR scan or per-worktree API discovery |
| T4 | Atomic shared observations, auth partitions, exact-head invalidation, TTLs, coalesced refreshes, shared cooldowns and shrinking request timeouts within a 30-second acquisition allowance |
| T5 | Both CLIs use the shared client and scoped relevant-ref fetches; strict no-PR/no-fetch paths, complete JSON, bounded ten-row summaries and epoch revalidation |
| T6 | Repeated precautionary scans removed; recipe strategies and safety conditions preserved in `recipe-evidence.md` |
| T7 | Deterministic git fixtures, fake transports and timestamped baseline traces; temporary installed entrypoints both import and show help |

## Reproduce

```bash
SC_STACK_EVIDENCE_PATH="$PWD/doc/plan/sc-gh-stack-api-efficiency/execution-evidence.json" \
  python3 -m pytest packages/sc-gh-stack/tests -q
```

The suite includes 120 layers, synthetic inventories of 1/10/60 worktrees,
ten real linked worktrees, ten concurrent readers, cold/warm/forced scopes,
same-SHA hosted expiry, failed fetches, intermediate conflicts with a clean
tip, missing history, numeric offline cache misses, partial errors, throttles,
auth partitions, pagination, deadlines, and snapshot changes. Git fixtures
verify refs/index/work files remain unchanged by reporting.

Result: **135 tests passed** locally on 2026-10-17 (37.62 seconds); compilation, installed-entrypoint smoke
checks and `git diff --check` also passed. A dedicated Linux CI job is
configured for this quota-independent suite; that hosted job has not run yet.

Development gate: **passed all ten anchors**, run
`dev-20261017T185300Z-sc-stack-review-p68`, at production threshold 0.6.
All forty raw role confidences meet that threshold; paired deterministic checks
were completed. [Report and checks](anchor-runs/0.5.0/development-gate-E1-r4/posted-report.md)
retain the earlier failures and their triage. Independent authority-only tuning
calibrated ANC-004/008 development questions without changing intent, scope or
threshold. Paired review added API-free catalog recovery diagnostics and removed
one residual mandatory post-link report, preserving affected-base verification.
The focused source-selection test distinguishes equivalent metadata REST reads
from CI rollup acquisition and bulk batching.

## Observed comparison

`execution-evidence.json` retains timestamped subprocess-boundary traces.
For the same 120 known PRs, old acquisition issued 1/10/60 extension views,
one repository-identity subprocess and one unbounded 120-alias detail query.
New acquisition issued zero extension/identity calls, three serial detail
queries (50/50/20), and zero additional GitHub calls on warm reports. Both
retain all 120 layers; default new text shows ten, with explicit truncation.
The fixture measured 4,480 old text bytes versus 1,455 new summary bytes;
complete JSON and full text are separately measured.

These are observed mocked subprocess counts, not a measurement of HTTP calls
inside the old extension. Real quota cost and production concurrency remain
unmeasured. Recorded lexical token counts are not model tokenizer counts.

## Freshness and compatibility

Git freshness is shared per repository/remote/ref for 60 seconds; explicit
scopes do not inherit coverage from an arbitrary configured refspec. Hosted
metadata/status expires after 120 seconds, or 60 for running checks. Unchanged
heads do not extend hosted freshness. Failed refreshes never claim fresh
heads or relabel old green hosted data as fresh. Unavailable fields have a
60-second retry observation to prevent hot loops; explicit refresh or a new
expected head bypasses it. `--refresh-git` refreshes refs without API acquisition; `--refresh-status`
refreshes hosted fields without implying fetch; `--refresh` requests both.
`--full` does not force acquisition and `--json` remains complete.

After external writes, reuse sufficient mutation responses or explicitly
refresh the affected requested scope; these read-only scripts do not intercept
the extension's writes. The adapter exposes scoped invalidation for callers.
Local clean merges do not establish checks, reviews, approvals or policy.
Unknown/stale required evidence never authorizes linking or a green chain
verdict. Catalogs are not migrated, and reporting never imports/checks out a
stack. Python remains stdlib-only and uses `gh api`, not a new HTTP client.

Bulk branch lookup uses GitHub's documented
[head-ref filtering](https://docs.github.com/en/graphql/reference/repos).
Small equivalent REST lookups remain preferred without creating REST fanout.
Live endpoint compatibility and hosted mutation/recovery outcomes were not
exercised; recipe-equivalence evidence is a strategy/contract review, not a
production landing test. No release or PR had been created at that handoff.

## Post-review regression fixes

The critical-review follow-up corrects bulk GraphQL branch filters, reconciles
explicit view refreshes with verified remote membership, rejects catalog changes
both during fetch and after hosted acquisition, and selects the pushed top from
complete ordered composition rather than summary rows. Failed/incomplete
structural pages and stale cached lifecycle cannot certify old composition.
Ordinary reports add no structural scans; recipe strategy and write authorization
remain unchanged. Shell-side projections keep full JSON out of agent context.

Verification on 2026-10-17: **204 tests passed in 37.35 seconds**; compilation,
temporary package installation/both entrypoints, and whitespace checks passed.
Tests use local git, fake transports/clocks and the actual documented projection;
no live GitHub API or 500-layer experiment was run. The earlier Jev development
gate is historical evidence for `dc526cc`, not a rerun against this follow-up.
The review's medium-priority findings remain outside this focused patch.

## Remaining-review closure and hosted stack

PR #125 contains the original work above documentation PR #119 in stack #126.
Its hosted manifest validation exposed a missing shebang, fixed on its own
branch at `6d5e5d2`. Subsequent review hardening is a separate layer above #125.

The follow-up fixes failed branch-mapping retry suppression, independent git
and hosted deadlines, bounded shared adapter pacing, deleted-branch batched
fetch recovery, and exact-stack diagnostic/epoch isolation. Trunk-wide
discovery still detects newly added or conflicting stacks. Per-ref and
per-field freshness prevent stale observations from generating reset/push
advice or retiring an active layer; fresh sibling refs remain visible.

Both CLIs add `--compact-json` with explicit counts/truncation and bounded
rows, refs, commands and messages; complete `--json` is unchanged and remains
the composition evidence source. Parse errors and interruption preserve the
machine-output error envelope. Companion worktree handoffs now reuse sufficient
evidence and record returned numeric stack identity for any necessary scoped
refresh. Remaining retry/polling guidance is bounded; recipe strategies and
top-only hosted QA/CI stay intact. LANDING explicitly predicts top/trunk
content, not whole-stack eligibility.

Adapter pacing cannot intercept independent direct `gh`/extension commands;
the documented single coordinator remains responsible for those. No new HTTP
client, release, 500-layer experiment, or live GitHub API test was introduced.
Real API calls in this follow-up only create/inspect PRs, stacks and CI.
The historical Jev gate is not presented as a rerun against these fixes.

Verification on 2026-10-17: **453 tests passed in 63.47 seconds**, covering both
complete package suites. Compilation, both package artifact validators and
whitespace validation passed. The dedicated offline CI job now runs both suites.
Independent follow-up review caught and closed trunk-filter membership drift,
unbounded compact ref/command fields, and stale current-ref ancestry evaluation;
regressions cover these and stale hosted lifecycle/head/base observations.
