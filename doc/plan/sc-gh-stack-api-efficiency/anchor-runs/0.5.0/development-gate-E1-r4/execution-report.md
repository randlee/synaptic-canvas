# E1 implementation evidence

Implemented and pushed on `feature/sc-gh-stack-api-efficiency` at `dc526ccfb71855565ef2a6e223485e375847fa2b`; baseline `fc702b1`.
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

Development-gate status: pending. Independent authority-only development-question
calibration is complete for ANC-004 and ANC-008; intent, anchors and the 0.6
threshold are unchanged. The third run satisfied nine anchors but left economical
REST selection inconclusive. The account below now distinguishes required fields
and deterministic request counts. Paired review added API-free catalog diagnostics
and removed one residual mandatory post-link report while retaining affected-base
verification. No gate pass or acceptance is claimed.

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
production landing test. No release, commit, push or PR is implied by this record.
