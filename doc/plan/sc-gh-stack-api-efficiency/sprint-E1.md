# Sprint E1 — Economical stack state

## Scope boundary

Redesign sc-gh-stack's status and chain-check scripts and the sc-gh-stack /
sc-gh-stack-view recommendations to reduce burst GraphQL request volume for
equivalent stack operations. Support stacks exceeding 100 layers. Preserve
mergeability reporting and prefer local computation across the entire stack.
Existing recipe stacking strategies and intended outcomes for challenging
conditions are preserved; equivalent git-call substitutions are permitted.

Do not replace the extension's mutation implementation or add new authorization
for branch rewrites. Reporting does not switch worktrees, rewrite refs, or
migrate the extension catalog. There is no requirement that every operation
work without API budget. This sprint is future implementation work; the present
session designs and tunes its plan, not a live GitHub load test.

## Authoritative deliverables

1. T1, local discovery: resolve common/per-worktree git directories, repository
   identity and ownership locally; read common and legacy gh-stack catalogs
   without invoking remote-refreshing extension views. Validate and deduplicate
   tracked stacks, reject conflicting metadata, apply scope filters, and batch
   ref reads before selecting any API calls. Missing catalogs do not prove the
   absence of remote stacks. T1 unblocks T2, T3 and T4.
2. T2, local mergeability: use the intended immutable base/head pair for every
   layer and a combined top/trunk check to compute git content-conflict results
   locally when sufficient objects and refs exist. Report clean, conflicting
   or unknown per layer and for the whole requested stack. Keep ancestry,
   recorded-base consistency, pushedness, and content conflicts separate.
   Neither ancestry nor clean tip/trunk results replace intermediate-layer
   checks. Local conflict results never establish hosted approvals, checks or
   policy eligibility. T2 depends on T1 and unblocks T4 and T6.
3. T3, economical acquisition: every remote read names the consumer and missing
   required information. Reuse sufficient local/cached observations and mutation
   responses. Prefer REST when it supplies equivalent required fields more
   economically without replacing GraphQL bursts with equivalent REST fanout.
   Use scoped stack/PR REST reads for structural data and bounded GraphQL batches
   for required bulk fields that REST cannot economically supply. Do not fetch
   unused fields, scan unrelated PRs, or fall back to per-PR calls after a failed
   batch. T3 depends on T1 and unblocks T4 and T5.
4. T4, shared observations and burst control: share snapshots across worktrees,
   keyed by repository/auth/scope and catalog/ref fingerprints. Track source,
   observation age, exact SHAs, completeness and unknown reasons. Coalesce
   concurrent refreshes, recheck scope, atomically publish results, invalidate
   affected observations after writes, and expire mutable hosted data even when
   refs are unchanged. Serialize bounded API batches and honor shared cooldowns,
   Retry-After and deadlines. Throttle/auth failures stop further acquisition;
   no automatic protocol-switch bypass. No per-report auth lookup is added.
   T4 depends on T1–T3 and unblocks T5 and T6.
5. T5, integrate both reports: local derivation occurs before GraphQL selection.
   Warm or locally sufficient reports reuse observations without networking;
   missing/stale remote fields needed by the requested report are acquired
   selectively, not omitted behind a mandatory offline-only default. Preserve
   strict no-PR/no-fetch controls. Document current-ref and stale-state paths:
   coordinate a relevant fetch once, qualify failed/old observations, handle
   missing objects/history, and use scoped hosted refresh only for missing
   nonlocal facts. Git fetch does not refresh checks, approvals or lifecycle.
   Render bounded summaries with counts/freshness and explicit truncation;
   retain complete JSON/full output. Rendering an acquired snapshot does no I/O.
   T5 depends on T3/T4 and unblocks T6/T7.
6. T6, recommendations and recipe calls: eliminate precautionary repeated scans,
   checkout-as-status, and before/after/finish reads that obtain no missing
   information. Keep necessary verification and recovery outcomes, not ritual
   commands. For each recipe call substitution record its original stacking
   strategy and goal, replacement evidence/action, and equivalent success and
   challenging-condition recovery behavior. Preserve ownership, authorization,
   expected-head checks and hosted executor enforcement. Do not add wrapper
   readiness scans duplicating sufficient observations or the executor's own
   preflight. Async polling targets only its outstanding operation with bounded
   completion/failure handling. T6 depends on T2/T4/T5 and unblocks T7.
7. T7, automated verification and handoff: build local git/catalog fixtures and
   mocked transports that inspect actual subprocess and request counts, not CLI
   invocation counts. Compare old/new acquisition and output for equivalent
   traces. Document freshness, compatibility, call budgets and recipe-goal
   equivalence. T7 depends on T5/T6. Live GraphQL smoke checks remain optional,
   explicitly scoped and quota-constrained; automated tests do not depend on
   available GitHub quota.

## Authoritative acceptance criteria

- ANC-001/002/003: no per-worktree API discovery. Acquire only required missing
  information after evaluating sufficient local state; warm repeated reads and
  concurrent readers reuse observations instead of repeating precautionary scans.
  Compare the same operations/inputs to scripts at fc702b1, recording timestamped
  request counts, burst pressure, concurrency and reported GraphQL quota cost
  separately. No fabricated numeric percentage or promise about external agents.
- ANC-004: cheaper REST supplies equivalent required fields where suitable;
  required bulk rollups may remain batched GraphQL. Assert that source selection
  does not create equivalent REST request fanout.
- ANC-005/006: every intended layer pair and top/trunk conflict result is present
  or explicitly unknown. Aggregate without hiding an intermediate conflict or
  unknown; keep hosted eligibility distinct. Local checks leave refs, index and
  working files unchanged, although merge-tree may create git objects.
- ANC-007: recipe strategies and intended outcomes are unchanged by call
  substitutions. Tests cover the same challenging-condition recovery and
  necessary verification outcomes, including cheaper local/status acquisition.
- ANC-008: mocked 120-layer stacks are complete, not silently capped at 100 or
  at the proposed 50-PR request-batch size. With 1/10/60 worktrees exposing the
  same 120 PRs, a cold all-required-field refresh uses at most three GraphQL
  detail batches, zero worktree views and zero repository-identity API calls.
  A necessary structural REST refresh/pagination is separately accounted for.
- ANC-009: document how to obtain each required information category with stale
  local state. Failed fetches never produce claims of fresh heads; unchanged
  SHAs never prove hosted checks/reviews unchanged. Refresh only needed refs or
  hosted fields, not the entire repository/status as a precaution.
- ANC-010: automated local and mocked tests are required. No live load test,
  quota-dependent test suite, or 500-layer experiment is required now.
- Ten same-scope concurrent readers coalesce into one shared refresh sequence;
  auth/scope changes cannot reuse incomplete or unauthorized data. Throttle,
  HTTP-200 GraphQL partial errors, auth failures and timeouts preserve useful
  local output with explicit unknowns and stop further requests appropriately.
- Default summaries show at most ten layer rows with counts, freshness and
  explicit truncation; full mode returns all 120. All blockers/unknowns are
  counted. Measure output bytes and tokens without hiding necessary evidence.

## Authoritative validation

Use deterministic git fixtures for common/legacy catalog discovery, conflicting
definitions, malformed schemas, unusual worktree paths, clean/conflicting layer
merges, recorded-base drift, ancestry-only cases, merged parents, shallow/missing
history, missing refs, and unexpected merge-tree errors. Include an intermediate
conflict or unknown with a clean top/trunk result.

Use mocked REST/GraphQL, git and clock boundaries for cold/warm observations,
120-layer pagination/batching, cross-worktree reuse, ten concurrent readers,
scoped invalidation, same-SHA CI/review changes, cooldown/deadline behavior,
partial GraphQL errors, 403/429/auth/timeout paths and async terminal outcomes.
Strict no-PR paths include numeric identifiers and cache misses. Recipe call
substitutions have before/after goal and recovery-equivalence evidence.

Keep all results, request traces and output comparisons. Any later live smoke
test is small, explicitly requested and separately reported; it is not evidence
from a production-quota load test. Perform no implementation or live GitHub
experiment merely to complete this planning review.

## Non-closure

This plan does not claim implementation, automated-test execution, live quota
measurements, release readiness or a production planning-gate pass. Question
seals, gate results and any unresolved findings are reported separately. No
task is closed until its artifacts and required verification exist.
