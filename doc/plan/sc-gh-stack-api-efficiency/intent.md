# Intent — sc-gh-stack API efficiency

Written 2026-10-14 from randlee's planning instructions.

Version 2: recipe boundary clarified and statements explicitly locked by the
user on 2026-10-15 UTC (2026-10-14 local). Version 1 is preserved in
`anchor-runs/authority-history/intent-v1.md`; its prior run evidence is unchanged.

## What this plan is for

Redesign the scripts and recommendations in `sc-gh-stack` and
`sc-gh-stack-view` to conserve GitHub GraphQL quota, particularly burst quota,
while preserving the information needed to operate stacks of 100+ layers.
The current scripts exhaust the available budget in ordinary use. The goal is
to remove the excessive request patterns causing that exhaustion, not to
introduce a requirement that every operation work without API budget.

Start with the information each call is intended to obtain. Identify redundant
or unnecessarily conservative information gathering, determine what can be
established from local git and stack metadata, and choose economical remote
calls for the remaining information. Consider both current and stale local
refs. Prefer inexpensive REST calls where they conserve GraphQL budget without
creating equivalent request fanout elsewhere.

## What success looks like

- Routine use on 100+ layer stacks avoids per-worktree remote discovery and
  repeated gathering of information already available for the operation.
- Local state is evaluated before deciding whether GraphQL is necessary.
- Necessary remote reads are scoped, batched or reused appropriately, with
  particular attention to request bursts across repeated/concurrent use.
- Mergeability remains a first-class result. Prefer determining conflict
  mergeability for the entire stack locally where possible; distinguish that
  result from GitHub checks, approvals, and policy eligibility.
- The design explains what information requires refreshing when local refs
  are stale, without using staleness as a reason to re-query everything.
- Established recipes retain their stacking strategies and intended outcomes,
  including handling challenging conditions. Their git calls may be changed
  to achieve those same goals with less unnecessary information gathering.
- Automated tests cover the redesign using local git fixtures and mocked API
  responses; live GraphQL verification is separately constrained by quota.

## What is deliberately out of scope

- Changes that discard or alter the established stacking strategies or intended
  outcomes of recipes. Equivalent git-call substitutions are in scope.
- Implementation and live GitHub experiments in this current planning session.
  Tests are wanted for the implementation; the present quota shortage makes
  live GraphQL verification difficult, rather than excluding automated tests.
- New operating requirements inferred from the temporary budget exhaustion,
  such as requiring all GitHub operations to function with zero API budget.

## Provenance and anchors

User's intent, verbatim:

> ok, let's start plan anchoring w/ the intent.  we need to redesign the scripts & recommended sc-gh-stack and sc-gh-stack-view to be more conservative on gh graphql budget, particularly burst.  We want to eliminate redundant/conservative information gathering.  we want to determine state locally if possible before graphql calls.  use cheap rest calls to conserve budget.  is-mergeable is important and if it can be determined for entire stack locally is preferred.  do not plan modifications of recipies that were carefully designed.

Testing clarification, verbatim:

> we want tests, graphql tests will be hard due to quota

Recipe clarification, verbatim (supersedes the earlier document-immutability
interpretation):

> untouched may be a bit strong.  the recipe are strategies for stacking in challenging conditions.  we can change the git calls and accomplish the same goals.

Lock instruction, verbatim:

> yes, lock down the approved statements

The locked anchor register is `anchors.json`, with `anchors.md` rendered from
it. Prior inconclusive capture evaluations remain historical evidence, not
passes. User approval establishes authority; question calibration and the
production planning gate are separate evidence. This intent supersedes
conflicting scope or workflow recommendations in the earlier design draft.
