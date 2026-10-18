## Anchor gate: dev · sc-stack-review-p68 - E1 — Economical stack state development review

Run `dev-20261017T185026Z-sc-stack-review-p68`, model `jev-1.13.0`, threshold 0.6. Counts: underspecified 1, satisfied 9.

> **sc-stack-review-p68 · ANC-004 · underspecified** Anchor: The sc-gh-stack redesign must prefer REST to GraphQL when REST supplies the required information at lower quota cost. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "use cheap rest calls to conserve budget." Jev was not confident (min confidence 0.37); the anchor or the work may be underspecified. (leaning: satisfied)
>   Low: compliance `implemented` answered yes at 0.58.
>   Low: conflict `violated` answered no at 0.37.

> **sc-stack-review-p68 · ANC-001 · satisfied** Anchor: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we need to redesign the scripts & recommended sc-gh-stack and sc-gh-stack-view to be more conservative on gh graphql budget, particularly burst." The directive was followed and evidenced.
>   Pair with the deterministic check: Compare documented request paths and mocked request counts for equivalent operations.

> **sc-stack-review-p68 · ANC-002 · satisfied** Anchor: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "We want to eliminate redundant/conservative information gathering." The directive was followed and evidenced.
>   Pair with the deterministic check: Trace each planned remote read to a consumer and identify whether existing sufficient observations can supply it.

> **sc-stack-review-p68 · ANC-003 · satisfied** Anchor: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL. You said (Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., Oct 14): "we want to determine state locally if possible before graphql calls." The directive was followed and evidenced.
>   Pair with the deterministic check: Inspect call ordering and branch conditions for local state resolution before GraphQL selection.

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
