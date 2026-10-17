## Anchor gate: dev · sc-stack-review-p68 - E1 — Economical stack state development review

Run `dev-20261017T185300Z-sc-stack-review-p68`, model `jev-1.13.0`, threshold 0.6. Counts: satisfied 10.

> **sc-stack-review-p68 · ANC-001 · satisfied** Anchor: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we need to redesign the scripts & recommended sc-gh-stack and sc-gh-stack-view to be more conservative on gh graphql budget, particularly burst." The directive was followed and evidenced.
>   Pair with the deterministic check: Compare documented request paths and mocked request counts for equivalent operations.

> **sc-stack-review-p68 · ANC-002 · satisfied** Anchor: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "We want to eliminate redundant/conservative information gathering." The directive was followed and evidenced.
>   Pair with the deterministic check: Trace each planned remote read to a consumer and identify whether existing sufficient observations can supply it.

> **sc-stack-review-p68 · ANC-003 · satisfied** Anchor: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we want to determine state locally if possible before graphql calls." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect call ordering and branch conditions for local state resolution before GraphQL selection.

> **sc-stack-review-p68 · ANC-004 · satisfied** Anchor: The sc-gh-stack redesign must prefer REST to GraphQL when REST supplies the required information at lower quota cost. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "use cheap rest calls to conserve budget." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect source selection decisions for equivalent required information and their documented request costs.

> **sc-stack-review-p68 · ANC-005 · satisfied** Anchor: The sc-gh-stack redesign must preserve reporting of stack mergeability. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "is-mergeable is important and if it can be determined for entire stack locally is preferred." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect the resulting report contract for a mergeability result rather than its removal to save quota.

> **sc-stack-review-p68 · ANC-006 · satisfied** Anchor: The sc-gh-stack redesign must prefer local computation of whole-stack mergeability when the required state can be determined locally. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "is-mergeable is important and if it can be determined for entire stack locally is preferred." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect local mergeability coverage across the stack and reasons retained remote information cannot be derived locally.

> **sc-stack-review-p68 · ANC-007 · satisfied** Anchor: The sc-gh-stack redesign must preserve the stacking strategies and intended outcomes of established recipes when changing their git calls. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "untouched may be a bit strong.  the recipe are strategies for stacking in challenging conditions.  we can change the git calls and accomplish the same goals." The directive was followed and evidenced.
>   Pair with the deterministic check: Compare each changed recipe with its baseline strategy and intended outcome; prove git-call substitutions retain those goals and challenging-condition behavior.

> **sc-stack-review-p68 · ANC-008 · satisfied** Anchor: The sc-gh-stack redesign must support stacks with more than 100 layers. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we are using this on stacks w/ 100+ layers, do you see a problem there?" The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect limits and pagination for assumptions that exclude stacks exceeding 100 layers.

> **sc-stack-review-p68 · ANC-009 · satisfied** Anchor: The sc-gh-stack design must document how to obtain the required information when local repository state is out of date. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "3.b. how to get same info if repo is out of date." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect the design's stale-state acquisition path for each required information category.

> **sc-stack-review-p68 · ANC-010 · satisfied** Anchor: The sc-gh-stack redesign must include automated tests. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we want tests, graphql tests will be hard due to quota." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect planned test coverage and eventual test artifacts; distinguish mocked/local tests from quota-constrained live checks.

## Paired deterministic checks

Reviewed implementation: `dc526cc` (baseline `fc702b1`). All checks below were
completed by the parent reviewer; the gate agent only judged the account.

| Anchor | Check performed and observed result |
|---|---|
| ANC-001 | Inspected baseline/new acquisition paths and parsed `execution-evidence.json`: the 1/10/60-worktree cases replace 1/10/60 extension views plus identity/detail acquisition with three serial 50/50/20 detail batches; zero additional warm API calls. All 120 layers retained. Mocked subprocess counts only; extension-internal HTTP and production quota costs are unmeasured. Pass. |
| ANC-002 | Traced COMMON metadata to chain-check and STATUS fields to view, field/head/TTL reuse and cooldown paths, and reviewed both skills. Found and fixed the residual mandatory post-link view in `518b4d3`; affected-base verification remains. Warm reuse, missing-node suppression, concurrent coalescing and no-fallback tests passed. Pass. |
| ANC-003 | Inspected both report entrypoints: catalogs/refs and local conflicts precede hosted detail selection. Scoped numeric discovery is a prerequisite only when structure is absent. Ordering and numeric `--no-pr` cache-miss tests passed with zero API calls. Pass. |
| ANC-004 | Inspected `_prs`, branch mapping and scoped stack REST paths. `test_source_selection_preserves_fields_without_rest_fanout` passed: two metadata PRs use two REST/zero GraphQL calls; one CI status uses zero REST/one GraphQL call; three metadata PRs use one batch/zero REST calls. ETag/304 and 120-branch batching/reuse tests passed. Pass. |
| ANC-005 | Inspected JSON/report fields: per-layer and combined local results remain, separate from hosted eligibility/CI. Complete 120-layer output, stale/unknown icons, and intermediate conflict/unknown tests passed. Pass. |
| ANC-006 | Inspected immutable SHA-pair merge-tree probes for every active intended parent/head plus top/trunk. Real-git intermediate-conflict/no-mutation, merged-parent, missing-ref/error, and memo invalidation tests passed. Missing history is unknown, not clean. Pass. |
| ANC-007 | Reviewed changed recipes against `fc702b1` and `recipe-evidence.md`: pushed-top ancestry, append-only/frozen layers, full ordered link with explicit base, single writer, atomic landing, full expected SHA, async UUID failure/deadline, and child-tree comparison before reset remain. Catalog-conflict diagnostics now expose both source paths/compositions without accepting a disputed stack. Contract/diff review and deterministic fixtures passed; no production mutation/recovery test claimed. Pass. |
| ANC-008 | Inspected batch limits/pagination and all-layer iteration. Tests cover complete 120-layer JSON/full output and local results, 50/50/20 serial acquisition, ten real worktrees and 1/10/60 synthetic inventories; default summaries bound display only, not acquired membership. No 500-layer experiment. Pass. |
| ANC-009 | Inspected approved plan R01–R15 contracts and stale-state table against implementation: relevant-ref fetch coverage/coalescing, separate hosted refresh, same-SHA expiry, failed forced refresh, missing history, and scope-specific timestamps. Git-refresh/freshness tests passed. Pass. |
| ANC-010 | Ran `python3 -m pytest -q packages/sc-gh-stack/tests`: **135 passed in 37.62s**, Python 3.11.9. Only local git/fake transports; dedicated Linux CI configured but not executed here. Pass. |

Additional checks: all five scripts compiled; `git diff --check` passed;
`tools/sc-install.py install sc-gh-stack --dest /tmp/sc-stack-gate-install.oBeZO2/.claude`
installed the package and both installed entrypoints returned `--help` successfully.
No user installation was changed. The generic skill-creator validator rejects the
package's pre-existing `version`/`entry_point` frontmatter; this is not a newly
introduced schema failure, and those package-supported fields were preserved.

The parent additionally checked all 40 final raw Jev role answers: expected
choices and confidence at least 0.6, including evidence roles. No acceptance is
inferred solely from aggregate verdicts.

### Iterations and authority

Initial run: the agent omitted a supplied evidence map (report defect). The
second run restored it and left ANC-004/008 inconclusive. Independent evaluators
then calibrated development questions against frozen authority-only cases:
ANC-004 had nine cases and ANC-008 eleven, each repeated twice. Selected sets had
exact role/verdict matches, stable choices and zero regressions; raw candidates,
oracles, requests, responses, histories and acceptance tables are retained in
`../development-question-tuning/`. Intent, anchor versions and threshold never
changed. The third run left ANC-004 inconclusive; the fourth replaced that
underspecified account with field equivalence and actual routing-test counts.
No question was retuned against the delivered account.

Evidence growth is traced to existing authority: ANC-005/006/009 for restoring
the omitted map; ANC-007 for catalog recovery diagnostics; ANC-004 for source
selection detail; ANC-002 for removing the residual ritual; ANC-010 for test
counts/immutable file stats. See each iteration's triage and growth records.
