# sc-gh-stack question and plan alignment

Current result: ten approved statements locked, ten anchor-specific planning
question sets calibrated, complete Sprint E1 planning gate passed all ten
anchors at unchanged production threshold 0.6. Question calibration and plan
judgment are separate runs. Implementation and live GitHub verification have
not started. See `anchor-runs/0.5.0/coverage.md` and
`anchor-runs/0.5.0/planning-gate-E1/run.json`.

## Authority

The approved intent and ten approved candidate obligations govern this design.
The user clarified that recipe git calls may change while their stacking
strategies and intended outcomes for challenging conditions are preserved.
The earlier interpretation that recipe text/calls were immutable is superseded.
Temporary GitHub quota exhaustion is not a permanent zero-budget
operating requirement. Automated tests are required; live GraphQL tests are
separately quota-constrained.

## Plan corrections made before a planning gate

| Existing draft problem | Correction | Controlling intent |
|---|---|---|
| The draft alternated between rewriting recipe strategies and forbidding all call changes | Preserve recipe strategies/outcomes; allow equivalent local/REST/read-reuse substitutions and prove their challenging-condition behavior | User's clarified recipe boundary |
| All default reports were forced offline even when requested remote information was missing | Derive local state and reuse sufficient observations first, then acquire only missing/stale fields needed by the requested report | Local-first and economical remote acquisition, not zero API budget |
| A wrapper pre-merge scan of all hosted-readiness fields was required in addition to executor checks | Retain server enforcement and expected heads; no extra wrapper read without a consumer and a missing observation | Eliminate redundant/conservative information gathering |
| Proposed verification illustrated only 60 layers | Future mocked request-count and output coverage now uses 120 layers; no live load test or 500-layer experiment is run | Operate on stacks of 100+ layers; tests despite live quota constraints |
| Whole-stack mergeability could be mistaken for ancestry plus a tip/trunk check | Require every intended layer base/head conflict result, explicit unknowns, combined result, and intermediate-conflict fixtures | Preserve mergeability and prefer whole-stack local computation |
| Stale-state table still said refresh policy/lifecycle before merge | Limit refresh to consumed fields missing sufficient observations/executor checks | Gather only necessary information |

The detailed requirements and design remain in
`plans/2026-10-14-sc-gh-stack-api-efficiency.md`. These edits fix visible drift;
they are not evidence that the independent planning gate has passed.

## Question-tuning boundaries

The first frozen rubric corpus passed, but every project candidate capture was
inconclusive. The independent tuner diagnosed possible gaps in proper-name,
conditional-policy, and mergeability handling without treating low confidence
as proof of a defect. Its expanded generic corpus preserves all original cases
and adds independently labeled positive, negative, and ambiguous examples.
The live calibration request and evidence are under
`anchor-runs/0.5.0/rubric-domain-01/`.

The user explicitly instructed locking the approved statements after these
diagnostics. `anchors.json` now contains ANC-001 through ANC-010; `anchors.md`
is rendered by the skill. Locking records approved authority and does not
convert capture scores to passes. Intent version 2 incorporates the recipe
clarification; version 1 and all prior evidence remain unchanged in history.

Formal, per-anchor planning-question tournaments are under
`anchor-runs/0.5.0/plan-tuning/ANC-*/`. Their strict requests use only the locked
anchor and approved intent, with no diagnostic plan. The earlier question
proposals were preparatory, not sealed, and their old C07 recipe interpretation
is superseded; do not deploy those proposals as the current recipe policy.

Do not lower production thresholds, relabel probes after responses, or tune
against a desired current-plan verdict. A genuine plan defect is fixed in the
plan; an oracle-proven question defect is independently retuned. Clarity-only
changes to approved authority remain proposals until approved. Tuning workers
derive independent probes from the locked authority; draft fixture sentences
are not silently represented as approved fixtures.
