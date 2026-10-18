# Anchors - sc-gh-stack-api-efficiency

Constraints captured during planning. Each anchor is a testable statement written by the orchestrator and approved by the user; the user's verbatim words are kept beneath it as provenance. Every anchor is judged at the planning gate and again at the development gate. Edit `anchors.json`, not this file; this file is rendered.

Intent: `doc/plan/sc-gh-stack-api-efficiency/intent.md`

| ID | Status | Summary | Stated |
| --- | --- | --- | --- |
| ANC-001 | locked | Reduce GraphQL bursts | 2026-10-14 |
| ANC-002 | locked | Gather only needed information | 2026-10-14 |
| ANC-003 | locked | Determine local state first | 2026-10-14 |
| ANC-004 | locked | Choose economical REST reads | 2026-10-14 |
| ANC-005 | locked | Preserve stack mergeability | 2026-10-14 |
| ANC-006 | locked | Prefer local whole-stack mergeability | 2026-10-14 |
| ANC-007 | locked | Preserve recipe strategies and outcomes | 2026-10-14 |
| ANC-008 | locked | Design for 100-plus layers | 2026-10-14 |
| ANC-009 | locked | Account for stale local state | 2026-10-14 |
| ANC-010 | locked | Include tests despite live quota constraints | 2026-10-14 |

## ANC-001

Anchor: The sc-gh-stack redesign must reduce burst GraphQL request volume for the same stack operations compared with the current scripts.

> we need to redesign the scripts & recommended sc-gh-stack and sc-gh-stack-view to be more conservative on gh graphql budget, particularly burst.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Reduce GraphQL bursts

Scope: Changes to API scheduling or status recommendations in sc-gh-stack scripts and the sc-gh-stack/sc-gh-stack-view skills.

Deterministic check to pair with the development gate: Compare documented request paths and mocked request counts for equivalent operations.

## ANC-002

Anchor: Remote information gathering in sc-gh-stack must be limited to information still required for the current operation.

> We want to eliminate redundant/conservative information gathering.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Gather only needed information

Scope: Adds or changes information gathering in stack scripts or the two stack skills' recommendations.

Deterministic check to pair with the development gate: Trace each planned remote read to a consumer and identify whether existing sufficient observations can supply it.

## ANC-003

Anchor: The sc-gh-stack scripts must evaluate locally derivable state before requesting that state through GraphQL.

> we want to determine state locally if possible before graphql calls.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Determine local state first

Scope: Changes stack discovery, state derivation, or a GraphQL request path in the stack scripts.

Deterministic check to pair with the development gate: Inspect call ordering and branch conditions for local state resolution before GraphQL selection.

## ANC-004

Anchor: The sc-gh-stack redesign must prefer REST to GraphQL when REST supplies the required information at lower quota cost.

> use cheap rest calls to conserve budget.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Choose economical REST reads

Scope: Selects REST or GraphQL for remotely acquiring stack information.

Deterministic check to pair with the development gate: Inspect source selection decisions for equivalent required information and their documented request costs.

## ANC-005

Anchor: The sc-gh-stack redesign must preserve reporting of stack mergeability.

> is-mergeable is important and if it can be determined for entire stack locally is preferred.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Preserve stack mergeability

Scope: Changes mergeability computation or the stack status report.

Deterministic check to pair with the development gate: Inspect the resulting report contract for a mergeability result rather than its removal to save quota.

## ANC-006

Anchor: The sc-gh-stack redesign must prefer local computation of whole-stack mergeability when the required state can be determined locally.

> is-mergeable is important and if it can be determined for entire stack locally is preferred.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Prefer local whole-stack mergeability

Scope: Chooses the source or algorithm for computing mergeability across stack layers.

Deterministic check to pair with the development gate: Inspect local mergeability coverage across the stack and reasons retained remote information cannot be derived locally.

## ANC-007

Anchor: The sc-gh-stack redesign must preserve the stacking strategies and intended outcomes of established recipes when changing their git calls.

> untouched may be a bit strong.  the recipe are strategies for stacking in challenging conditions.  we can change the git calls and accomplish the same goals.

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Preserve recipe strategies and outcomes

Scope: Plans or performs changes to established stacking recipes, including git-call substitutions in challenging-condition handling.

Deterministic check to pair with the development gate: Compare each changed recipe with its baseline strategy and intended outcome; prove git-call substitutions retain those goals and challenging-condition behavior.

## ANC-008

Anchor: The sc-gh-stack redesign must support stacks with more than 100 layers.

> we are using this on stacks w/ 100+ layers, do you see a problem there?

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Design for 100-plus layers

Scope: Chooses size limits, pagination, discovery, request batching, or output handling for stack scripts.

Deterministic check to pair with the development gate: Inspect limits and pagination for assumptions that exclude stacks exceeding 100 layers.

## ANC-009

Anchor: The sc-gh-stack design must document how to obtain the required information when local repository state is out of date.

> 3.b. how to get same info if repo is out of date

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Account for stale local state

Scope: Describes state acquisition, local-first alternatives, or refresh behavior in the sc-gh-stack redesign.

Deterministic check to pair with the development gate: Inspect the design's stale-state acquisition path for each required information category.

## ANC-010

Anchor: The sc-gh-stack redesign must include automated tests.

> we want tests, graphql tests will be hard due to quota

Said by randlee, Explicit user instruction: yes, lock down the approved statements; recipe git-call substitution clarification applies. Prior inconclusive capture results remain recorded, not passes., 2026-10-14. Status: locked. Version 1.

Summary: Include tests despite live quota constraints

Scope: Plans implementation verification for the sc-gh-stack redesign.

Deterministic check to pair with the development gate: Inspect planned test coverage and eventual test artifacts; distinguish mocked/local tests from quota-constrained live checks.
