---
name: refactory-design
version: 0.1.0
description: >
  Use this skill to design a constrained refactoring system before any package
  or runtime is built. It walks through approved-rule design, trigger and
  sample-fix guidelines, startup authorization policy, named-teammate
  responsibilities, QA gating, and package/runtime layout.
---

# Refactory Design

Use this skill when the goal is to create or package a rule-driven refactoring
toolkit, not to apply one specific refactor.

## When To Use

- designing a new approved-fix catalog
- converting repeated migration knowledge into reusable rules
- deciding what startup should and should not inject
- defining QA and commit-gate policy for large refactors
- packaging the system for reuse in other repos

## Phase 1: Rule Discovery

Work through these questions first:

1. What changes are explicitly allowed?
2. What changes are explicitly prohibited?
3. What should count as one rule versus several related rules?
4. Which fixes must always happen in tandem?
5. What trigger values are concise and operator-recognizable?
6. What belongs in startup context versus only after lookup?
7. Which examples are canonical and cross-repo?
8. What QA checks must always pass before commit?

Produce:

- rule boundary guidelines
- trigger guidelines
- sample-fix guidelines
- startup allow/deny policy text
- QA criteria

Do not skip this phase. If the rules are underspecified, the graph, startup
context, teammates, and QA layer all become noisy or unsafe.

## Rule Design Checklist

For each proposed rule, decide:

- what exact change is approved
- what exact change is prohibited
- what trigger or trigger set should surface the rule
- whether multiple triggers should share one document
- whether multiple edits must happen in tandem
- what examples best demonstrate the approved fix shape
- what false positives should be ignored
- what QA assertions must be true before commit

Minimum startup policy text should include:

```text
# Only changes covered by approved .refactor/ rules are allowed.
# If a needed fix is not in .refactor/, stop or add the rule before editing.
```

## Phase 2: Runtime Design

Decide:

- installed runtime layout under `.refactor/`
- startup provider path under `.startup/`
- package source layout under `packages/sc-refactory/`
- rule doc and rule graph formats
- preflight, repair, startup, and logging responsibilities
- named teammate responsibilities
- background sub-agent boundaries

Runtime decisions must be explicit about source-of-truth:

- committed docs live in `.refactor/docs/`
- committed Turtle rules live in `.refactor/rules/`
- runtime DB is `.refactor/db/` and is disposable
- logs live in `.refactor/logs/`
- temp artifacts live in `.refactor/temp/`

## Phase 3: Execution Model

Design:

- plan item schema
- development wave model
- QA wave model
- handoff between `refactor-orchestrator` and `quality-manager`
- commit gates
- escalation path for work not covered by `.refactor/`

The intended execution model is:

1. build a plan where every item cites approved rule ids
2. `refactor-orchestrator` launches bounded development waves
3. `quality-manager` launches QA review waves
4. failed waves return to rework or escalation
5. only QA-approved waves are committable

## Phase 4: Package Outputs

Produce:

- package manifest
- plugin metadata
- background-agent registry
- skill list
- teammate prompts
- runtime script inventory
- installation steps
- validation plan

## Recommended Output Shape

When you finish the design pass, provide:

1. a short summary of the policy model
2. the rule-design guidelines
3. the startup allow/deny text
4. the teammate and sub-agent boundaries
5. the package skeleton plan
6. open issues that need a human decision

## Larger Design Risks To Surface

Always call out:

- rules that are too broad or too vague
- startup trigger lists that are too long
- teammates that would need to coordinate mutable shared state
- QA expectations that cannot be checked mechanically
- missing examples for high-risk rules

## Core Policy

- Only changes covered by committed `.refactor/` content are authorized.
- Trigger hits authorize lookup, not immediate editing.
- If a needed fix is not represented in `.refactor/`, stop, escalate, or add
  the rule through the write flow before editing.
- QA must verify that 100% of changes are justified by approved rules before
  commit.

## Constraints

- Do not jump straight to graph schema or scripting before rule design.
- Do not treat “similar” fixes as equivalent without explicit rule coverage.
- Do not recommend startup injection of full docs or examples.
