# Refactory Design

**Status:** Draft  
**Author:** Codex  
**Created:** April 28, 2026  
**Package:** `sc-refactory`  
**Related:** `sc-startup`, `sc-codex`, `sc-manage`

## Purpose

`refactory` should primarily be a design skill for creating constrained refactoring systems like the one we just designed.

The skill should help an agent:

- design the rule system first
- define the policy boundaries for approved fixes
- choose the runtime layout and hook model
- scaffold the toolkit package and installed repo layout
- then bootstrap the operational scripts, skills, and agents

The resulting package must be able to install the same system we just proved out manually:

- concise startup trigger injection
- explicit startup policy constraints
- graph-backed lookup of approved fixes
- curated authoring flow for new rules
- orchestration of authorized change waves
- QA verification of rule compliance
- background agents that isolate lookup/write/orchestration/QA work
- local scripts for preflight, startup, repair, logging, and graph maintenance

This is not a generic refactoring assistant. It is a policy-system design and deployment workflow for approved fixes only.

## Problem

In large migrations, coding agents are dangerous when left to infer fixes from partial context. The common failure modes are:

- making many superficially plausible but incorrect edits
- forgetting repeated migration rules across repos
- blowing up context with build logs, example fixes, and tool output
- re-discovering the same fix shape repeatedly

The system needs a local memory layer with strict guardrails:

- startup must remind the agent which fix patterns are approved
- startup must state what is and is not allowed
- lookup must retrieve the exact rule document and sample fixes
- write must let humans or trusted agents add new approved rules
- QA must verify that every edit is explained by approved rules
- only committed source-of-truth rules should matter

## Design Goals

- Package the toolkit as a reusable skill bundle, not ad hoc repo code.
- Install into a target repo with a predictable layout.
- Use the existing global Claude/Codex startup dispatcher model.
- Follow the Claude skills/agents architecture guidelines v0.6.
- Keep startup injection extremely compact.
- Keep heavy logic out of session context and in scripts/agents.
- Treat approved rules as versioned source of truth.
- Support a future central graph with subset download to a local cache.
- Allow typed prompt fragments to live beside rules and examples.

## Non-Goals

- Autonomous open-ended refactoring.
- Unbounded fix suggestion from LLM reasoning alone.
- Storing runtime DB files in git.
- Requiring repo-local hook registration.
- Treating `oxigraph` as the product boundary instead of an implementation detail.

## Product Shape

There are two layers:

1. a design skill that helps create a refactoring policy system
2. an installable runtime package produced from that design

The runtime installable unit should be `packages/sc-refactory/`.

Within the Synaptic Canvas repository, package source files live under `packages/`.

At install time, package artifacts are copied out of `packages/sc-refactory/` into one of two destinations:

- global install:
  - `~/.claude/agents/`
  - `~/.claude/skills/`
  - `~/.claude/commands/`
  - `~/.claude/scripts/`
- local install:
  - `<repo>/.claude/agents/`
  - `<repo>/.claude/skills/`
  - `<repo>/.claude/commands/`
  - `<repo>/.claude/scripts/`

The package source tree is not itself a `.claude/` tree. It is a package definition that installs artifacts into `.claude/` locations.

It contains:

- a design skill for planning a refactoring toolkit
- an installer/bootstrap skill
- an orchestration skill
- runtime lookup and write skills
- lookup, write, orchestration, and QA background agents
- deterministic scripts for startup, preflight, repair, sync, and graph operations
- reference templates for rule docs and rule graph entries

The installed toolkit materializes a repo-local runtime under `.refactor/` and a repo startup provider under `.startup/`.

## Guidelines Alignment

This design should follow `/Users/randlee/Documents/github/synaptic-canvas/docs/claude-code-skills-agents-guidelines.md` closely.

The main consequences are:

- skills are the discovery and orchestration layer
- agents are the execution layer
- tool-heavy work stays inside agents
- agent outputs must be fenced JSON
- every agent must have YAML frontmatter with version
- every agent must be registered in `agents/registry.yaml` in the package source, which installs to `.claude/agents/registry.yaml`
- skills should use progressive disclosure and keep the top-level `SKILL.md` concise
- registry validation should be external rather than encoded into runtime prompts

The orchestration layer in this system should use the named teammate pattern from v0.6, not a standard one-shot background agent.

Required named teammates:

- `refactor-orchestrator`
  - persistent execution coordinator for plan and wave control
- `quality-manager`
  - persistent QA coordinator that manages compliance review waves

These teammates should load skill content as behavioral spec and spawn background sub-agents directly.

## Package Inventory

Recommended package structure:

```text
packages/sc-refactory/
├── manifest.yaml
├── agents/
│   ├── registry.yaml
│   ├── refactor-lookup-agent.md
│   ├── refactor-write-agent.md
│   ├── refactor-dev-agent.md
│   └── refactor-qa-agent.md
├── skills/
│   ├── refactory-design/
│   │   └── SKILL.md
│   ├── refactory-install/
│   │   └── SKILL.md
│   ├── refactor-orchestrate/
│   │   └── SKILL.md
│   ├── quality-manager/
│   │   └── SKILL.md
│   ├── refactor-lookup/
│   │   ├── SKILL.md
│   │   └── workflows.md
│   └── refactor-write/
│       ├── SKILL.md
│       └── workflows.md
├── scripts/
│   ├── install_refactory.py
│   ├── session_start.py
│   ├── preflight.py
│   ├── repair.py
│   ├── lookup.py
│   ├── write_rule.py
│   ├── rebuild_db.py
│   └── sync_subset.py
├── references/
│   ├── rule-doc-template.md
│   ├── rule-ttl-template.ttl
│   ├── install-and-troubleshooting.md
│   └── runtime-layout.md
└── assets/
    └── startup-wrapper-template
```

Installed artifact mapping:

- `packages/sc-refactory/skills/...` -> `~/.claude/skills/...` or `<repo>/.claude/skills/...`
- `packages/sc-refactory/agents/...` -> `~/.claude/agents/...` or `<repo>/.claude/agents/...`
- `packages/sc-refactory/scripts/...` -> `~/.claude/scripts/...` or `<repo>/.claude/scripts/...`

## Skills

### `refactory-design`

This is the primary skill.

Its job is not to look up one rule or install one script. Its job is to design a refactoring system for a repo family or migration campaign.

The first phase of this skill must be rule-design discovery.

Required first-step questions:

- What changes are approved vs prohibited?
- What kinds of triggers are useful?
- What should count as one rule versus multiple related rules?
- Which fixes must be performed in tandem?
- What contextual distinctions matter for execution but do not need to appear in startup injection?
- What examples are canonical?
- What prompts or checklists should be attached to a rule?

The skill should produce:

- rule authoring guidelines
- trigger guidelines
- sample fix selection guidelines
- startup injection guidelines
- agent and script boundary decisions
- package and runtime layout decisions

Only after those are clear should it move on to scaffolding the toolkit.

### `refactory-design` SKILL.md Draft

Recommended frontmatter:

```yaml
---
name: refactory-design
description: Design a constrained refactoring toolkit for a repo family or migration campaign, starting with approved-rule design, startup policy, agent boundaries, and execution-wave architecture before scaffolding scripts, skills, and agents.
---
```

Recommended body shape:

```markdown
# Refactory Design

Use this skill when the user wants to design or package a rule-driven refactoring system rather than perform one specific refactor.

## When to use

- Designing a new approved-fix rule catalog
- Converting repeated migration knowledge into lookupable rules
- Defining startup trigger injection and authorization boundaries
- Designing QA gating for refactoring changes
- Packaging a reusable refactoring toolkit

## Phase 1: Rule System Discovery

Work through these questions first:

1. What changes are explicitly allowed?
2. What changes are explicitly prohibited?
3. What should count as a rule?
4. Which fixes must always occur together?
5. What trigger forms are useful?
6. What should appear at startup versus only after lookup?
7. What examples are canonical?
8. What QA checks are required?

Produce:
- Rule boundary guidelines
- Trigger guidelines
- Sample-fix guidelines
- Startup policy text
- QA criteria

## Phase 2: Runtime Architecture

Decide:

- repo layout under `.refactor/`
- startup provider path
- rule doc and graph entry format
- preflight/repair/startup responsibilities
- agent boundaries
- named teammate responsibilities and sub-agent boundaries

## Phase 3: Execution Model

Design:

- plan item schema
- development wave model
- QA wave model
- commit gates
- escalation path for non-rule work

## Phase 4: Packaging Outputs

Produce:

- package manifest
- agent registry
- skill list
- agent list
- runtime script inventory
- installation and validation requirements
```

This skill should be high-judgment in phase 1, then progressively more deterministic in phases 2 through 4.

### Named Teammate Skills

The execution side of this system should use two named teammates:

- `refactor-orchestrate`
  - loaded as required reading by the `refactor-orchestrator` teammate
- `quality-manager`
  - loaded as required reading by the `quality-manager` teammate

Per the v0.6 guidelines, these skills should behave as behavioral specs, not normal Agent Delegation wrappers.

### `refactory-install`

This is the bootstrap skill. It installs the toolkit into a target repo and verifies the runtime is usable.

Responsibilities:

- create `.refactor/` layout
- create repo startup wrapper `.startup/team-lead` or equivalent configured provider
- install repo-local copies of runtime scripts when the model is “self-contained repo runtime”
- install repo-local runtime skills and agents when required
- create `.refactor/.gitignore`
- verify `oxigraph` installation
- run first-time DB build
- print the exact startup text preview

This skill should be low freedom. Installation must be deterministic.

### `refactor-lookup`

This is the runtime consumption skill.

Responsibilities:

- run cheap local preflight first
- if preflight passes, invoke `refactor-lookup-agent`
- surface the rule document, examples, and typed prompt fragments
- stop if the toolkit is unhealthy

The skill must explicitly tell the agent:

- do not edit until lookup completes
- do not bypass approved fixes
- do not invoke the background agent if preflight fails

### `refactor-write`

This is the runtime curation skill.

Responsibilities:

- create or update rule docs
- create or update graph entries
- add curated sample fixes
- keep sample paths repo-root relative
- validate structure before publishing

This skill is for authoring approved knowledge, not autonomous repair.

### `refactor-orchestrate`

This is the behavioral spec for the named `refactor-orchestrator` teammate.

Responsibilities:

- load a refactoring plan made only of approved rule-backed items
- partition work into waves
- dispatch development sub-agents to perform only authorized changes
- coordinate with the named `quality-manager` teammate after each development wave
- stop, rework, or escalate when QA finds non-compliant edits
- allow commit only after QA approval

This skill should not use a normal Agent Delegation table. It should describe the lifecycle, teammate responsibilities, background sub-agent spawning, and the structured status messages sent back to the lead.

### `quality-manager`

This is the behavioral spec for the named `quality-manager` teammate.

Responsibilities:

- receive wave handoff from `refactor-orchestrator`
- spawn QA sub-agents to inspect diffs and repo state
- ensure 100% of changes are justified by approved rules
- report pass/fail status with remediation requirements
- refuse approval when unauthorized edits, missed tandem edits, or rule drift are present

## Rule Design Guidelines

The design skill should explicitly walk the user through these guidelines before any package generation.

### Rule Boundary Guidelines

- A rule should represent one approved fix policy.
- Closely related triggers may point to one shared rule document.
- If multiple edits must always be applied together, they belong to one rule.
- If two triggers share rationale but not execution shape, use one shared document with separate trigger entries.
- Exceptions that require materially different handling should be called out explicitly in the rule, not left implicit.

### Trigger Guidelines

- Triggers should be concise and operator-recognizable.
- Triggers should be the minimal surface needed to recall a rule.
- Startup injection should prefer plain values, not typed prefixes.
- Broad canonical aliases are acceptable if they improve recall.
- Structural execution details should live in the rule document or prompt fragments, not in startup injection.

### Rule Document Guidelines

Each rule document should capture:

- what the trigger means
- why the rule exists
- when it applies
- when it does not apply
- exact approved fix shape
- tandem fix requirements
- exceptions and non-goals
- sample fix references

### Sample Fix Guidelines

- Use real committed examples.
- Prefer a small cross-repo set over many redundant examples.
- Keep paths repo-root relative.
- Link examples from the rule; do not inject them at startup.

### Prompt Fragment Guidelines

- Attach only bounded operational guidance.
- Prefer checklists, exception notes, and false-positive notes.
- Do not store broad free-form behavioral prompts as rule content.

### Startup Injection Guidelines

- Keep it short.
- Emit explicit allow/deny policy lines before the trigger list.
- Emit only operator-facing trigger values.
- Never inject full rules, examples, or graph metadata.
- Treat startup as a policy reminder, not a knowledge dump.

### Authorization Guidelines

- Only changes represented by committed `.refactor/` content are authorized.
- A trigger hit authorizes lookup, not direct editing.
- If a needed fix is not present in `.refactor/`, the agent must stop, escalate, or add the rule through the write flow before editing.
- Tandem fixes required by a rule are part of the authorization boundary.
- “Mostly similar” fixes are not authorized unless they are covered by the existing rule set.

## Agents

### `refactor-lookup-agent`

Contract:

- one graph query path
- return fenced JSON only
- never rebuild or repair the runtime
- return the primary rule doc and sample fixes
- return no-match cleanly

### `refactor-write-agent`

Contract:

- write tracked source files only
- create docs and graph entries in the correct layout
- return fenced JSON only
- never write runtime DB artifacts into git

### `refactor-qa-agent`

Contract:

- inspect a proposed diff against the active approved rules
- verify that 100% of edits are justified by `.refactor/` content
- detect missing tandem edits, unauthorized edits, and drift from approved fix shape
- return fenced JSON only
- block commit when compliance is incomplete

### `refactor-dev-agent`

Contract:

- execute one authorized work item or a tightly bounded batch of same-rule items
- make only the edits covered by the assigned rules
- return fenced JSON only
- never expand scope beyond the assigned authorization

### Named Teammates

The primary coordinators in this system should be named teammates, not one-shot background agents.

Required named teammates:

- `refactor-orchestrator`
- `quality-manager`

Their responsibilities are described by teammate-oriented skills, not normal Agent Delegation wrappers.

### Named Teammate Messaging Contract

Named teammates should:

- receive structured assignments
- spawn background sub-agents as needed
- aggregate sub-agent results
- send structured status messages back to the controlling lead or session

These messages may include fenced JSON blocks.

Minimum teammate status fields:

- `role`
- `wave`
- `status`
- `summary`
- `next_action`

Suggested embedded JSON block:

```json
{
  "success": true,
  "data": {
    "role": "quality-manager",
    "wave": "wave-03",
    "status": "pass",
    "approved": true,
    "blocked_items": [],
    "next_action": "commit-approved-wave"
  },
  "error": null
}
```

### Why This Split

This workflow needs:

- persistent coordination state across waves
- teammate-to-teammate handoff
- repeated background sub-agent spawning
- durable QA gating before commit

That fits the named teammate pattern better than a one-shot orchestrator agent.

### Deprecated Pattern

Do not model the main orchestrator as a standard `refactor-orchestrator-agent`.

That pattern is too short-lived for the intended workflow.

### Agent Output Contract

Per the guidelines, all runtime background agents should return fenced JSON and use a standard minimal or standard envelope.

Minimum acceptable envelope:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Recommended standard envelope for orchestration and QA:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {},
  "error": null,
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

## Installed Repo Layout

After installation, a target repo should contain:

```text
.startup/
└── team-lead

.refactor/
├── .gitignore
├── docs/
├── rules/
├── reports/
├── scripts/
├── db/
├── logs/
└── temp/
```

Rules for each directory:

- `docs/`: committed markdown rule documents
- `rules/`: committed graph source files
- `reports/`: optional committed analysis output
- `scripts/`: committed runtime helper scripts
- `db/`: local runtime graph store, ignored
- `logs/`: local runtime logs, ignored
- `temp/`: scratch space, ignored

Required ignore policy:

```gitignore
/db/
/logs/
/temp/
```

## Hook Model

`refactory` must rely on the existing global dispatcher pattern for both Claude and Codex.

The intended flow is:

1. CLI emits `startup`, `resume`, `clear`, or `compact`.
2. Global hook receives the event payload.
3. Global hook injects session id and ATM context automatically.
4. Global hook detects repo startup provider.
5. Repo startup provider runs `session_start.py`.
6. `session_start.py` emits only compact refactor context.

The package must not require repo-local startup registration.

## Startup Injection Contract

Startup output must be concise and policy-focused.

Required shape:

```text
# REFACTOR TRIGGERS
# Only changes covered by approved .refactor/ rules are allowed.
# If a needed fix is not in .refactor/, stop or add the rule before editing.
# Approved fix patterns only. On match -> invoke refactor-lookup.
# Use /refactor-lookup <trigger> <additional-context-error-logs> when one of these items appears in a build error.
#
<trigger 1>
<trigger 2>
...
```

Do not inject:

- rule bodies
- sample fix paths
- graph metadata
- trigger type prefixes like `string:` or `namespace:`

Required policy meaning:

- startup context is an allowlist reminder
- lookup is mandatory before edits when a trigger appears
- only committed `.refactor/` content can authorize edits
- anything outside the rule catalog must be escalated or authored first

## Runtime Scripts

### `session_start.py`

- rebuilds or refreshes local DB from committed rules
- logs to `.refactor/logs/session_start.log`
- fails silently to the agent if startup work fails
- never prints stack traces into injected context

### `preflight.py`

- validates required paths
- validates `oxigraph`
- if `db/` is missing, rebuilds it from committed rules
- prints one of two messages:

Success:

```text
oxigraph v X.Y.Z checks pass
```

Failure:

```text
tools are not installed or working to use this skill. please read ./.refactor/docs/install-and-troubleshooting.md
```

### `repair.py`

- attempts bounded local repair
- re-runs preflight
- never mutates committed rules

### `sync_subset.py`

Future script for central-graph deployments.

Responsibilities:

- download only relevant rules/prompts/examples
- build local `.refactor/rules/` from a filtered export
- keep local runtime small and deterministic

## Data Model

The source-of-truth model should be store-agnostic even if the first backend is RDF/Oxigraph.

Core entities:

- `Rule`
  - canonical approved-fix unit
- `Trigger`
  - string, symbol, file name, error code, namespace, or pattern that surfaces a rule
- `RuleDocument`
  - markdown how-to and rationale
- `SampleFix`
  - repo-root-relative path to a known good example
- `PromptFragment`
  - typed operational guidance linked to a rule
- `Campaign`
  - migration initiative or workstream
- `SubsetProfile`
  - filter definition for local sync

## Prompt Fragments

Agent prompts in the database are useful, but only if typed and bounded.

Allowed prompt fragment types:

- `startup-summary`
- `lookup-guidance`
- `fix-checklist`
- `exception-notes`
- `false-positive-notes`
- `write-curation-notes`
- `qa-checklist`
- `orchestration-notes`

Do not store opaque broad agent personalities or unconstrained system-prompt replacements.

## Sample Fix Rules

Sample fixes must be:

- repo-root relative
- drawn from real committed fixes
- preferably spread across multiple repos
- linked to the rule rather than duplicated in the startup injection

If four repos all show the same fix shape, use a diverse subset, not all four.

## Installation Story

The design assumes `oxigraph` is installed from crates.io, not Homebrew.

Normative installation path:

```bash
cargo install oxigraph-cli
```

The toolkit must document the tested version explicitly. Current known-good note:

- tested with `oxigraph 0.5.7`

Installer validation should confirm:

- `oxigraph --version` works
- repo layout exists
- startup provider exists
- preflight passes
- first startup output renders

## Packaging Strategy

`sc-refactory` should depend on the existing session-start infrastructure rather than replacing it.

Expected package dependencies:

- `sc-startup` for shared startup/hook conventions
- `sc-codex` if Codex-specific global integration helpers are required
- `sc-manage` if package discovery/installation helpers are shared there

## Skill/Agent Split

Following the guidelines, the recommended split is:

- `refactory-design`
  - public design skill
- `refactory-install`
  - public install skill
- `refactor-lookup`
  - public runtime lookup skill
- `refactor-write`
  - public runtime curation skill
- `refactor-orchestrate`
  - teammate-oriented execution skill for `refactor-orchestrator`
- `quality-manager`
  - teammate-oriented QA skill for `quality-manager`

Private implementation:

- `refactor-lookup-agent`
- `refactor-write-agent`
- `refactor-dev-agent`
- `refactor-qa-agent`

This keeps discovery space small while still allowing a rich internal workflow.

## General-Purpose vs Application-Specific

The toolkit itself should be general-purpose. The rule content should be application-specific.

That means:

- skills are general-purpose
- agents are general-purpose
- scripts are general-purpose
- rule schema is general-purpose
- startup injection format is general-purpose
- rule docs, triggers, examples, and prompt fragments are application-specific

This boundary is important. If the skills or agents are edited to hard-code domain rules like `Radiant.RPC.Annotations` or `GlobalUsings.cs`, the package stops being deployable and becomes a single-project artifact.

### What Must Stay General

- `refactory-install`
  - installs layout, scripts, skills, agents, and templates
- `refactor-lookup`
  - runs preflight and lookup flow
- `refactor-write`
  - writes validated rule content into the local knowledge store
- `refactor-lookup-agent`
  - queries by trigger and returns rule artifacts
- `refactor-write-agent`
  - creates or updates docs, rules, and sample references
- `session_start.py`
  - rebuilds, queries, logs, and emits compact trigger text
- `preflight.py`, `repair.py`, `rebuild_db.py`, `sync_subset.py`
  - operate on the runtime, not on one application domain

### What Must Be Repo or Campaign Specific

- markdown rule documents in `.refactor/docs/`
- graph rule entries in `.refactor/rules/`
- sample fix paths
- trigger values
- typed prompt fragments linked to a rule
- subset profiles for a particular repo family or migration campaign

### Design Consequence

The package should ship:

- empty or example templates
- perhaps a small demo fixture set for tests
- no production application rules baked into the package itself

Production rules should be installed by one of these models:

1. copied from a seed bundle selected during installation
2. synced from a central registry
3. authored locally with `refactor-write`

The skills and agents should understand any compliant rule set, not one specific application.

## Implementation Specification

This section describes the first concrete implementation shape for `sc-refactory`.

### Package Manifest

Recommended initial `manifest.yaml` shape:

```yaml
name: sc-refactory
version: 0.1.0
description: >
  Install and operate a graph-backed refactoring policy toolkit with startup
  trigger injection, approved-fix lookup, and curated rule authoring.
author: synaptic-canvas
license: MIT
tags:
  - refactoring
  - graph
  - oxigraph
  - startup
  - policy
  - agents

artifacts:
  skills:
    - skills/refactory-design/SKILL.md
    - skills/refactory-install/SKILL.md
    - skills/refactor-orchestrate/SKILL.md
    - skills/quality-manager/SKILL.md
    - skills/refactor-lookup/SKILL.md
    - skills/refactor-write/SKILL.md
  agents:
    - agents/refactor-lookup-agent.md
    - agents/refactor-write-agent.md
    - agents/refactor-dev-agent.md
    - agents/refactor-qa-agent.md
    - agents/registry.yaml
  scripts:
    - scripts/install_refactory.py
    - scripts/session_start.py
    - scripts/preflight.py
    - scripts/repair.py
    - scripts/lookup.py
    - scripts/write_rule.py
    - scripts/rebuild_db.py
    - scripts/sync_subset.py

install:
  scope: local-only

requires:
  - python3
  - cargo
  - git
  - pydantic

dependencies:
  - "sc-startup >= 0.10.0"
```

### Agent Registry

Recommended initial `registry.yaml` shape:

```yaml
version: "1.0"

agents:
  refactor-lookup-agent:
    path: agents/refactor-lookup-agent.md
    version: "0.1.0"
    description: Query the local refactor knowledge store for approved rules.

  refactor-write-agent:
    path: agents/refactor-write-agent.md
    version: "0.1.0"
    description: Create or update tracked refactor rule artifacts.

  refactor-dev-agent:
    path: agents/refactor-dev-agent.md
    version: "0.1.0"
    description: Execute one authorized refactor work item or bounded batch.

  refactor-qa-agent:
    path: agents/refactor-qa-agent.md
    version: "0.1.0"
    description: Verify that proposed edits comply 100% with approved rules.

skills:
  refactory-design:
    path: skills/refactory-design/SKILL.md
    version: "0.1.0"

  refactory-install:
    path: skills/refactory-install/SKILL.md
    version: "0.1.0"

  refactor-lookup:
    path: skills/refactor-lookup/SKILL.md
    version: "0.1.0"
    depends_on:
      - refactor-lookup-agent@0.1.x

  refactor-write:
    path: skills/refactor-write/SKILL.md
    version: "0.1.0"
    depends_on:
      - refactor-write-agent@0.1.x

  refactor-orchestrate:
    path: skills/refactor-orchestrate/SKILL.md
    version: "0.1.0"
    depends_on:
      - refactor-dev-agent@0.1.x
      - refactor-qa-agent@0.1.x

  quality-manager:
    path: skills/quality-manager/SKILL.md
    version: "0.1.0"
    depends_on:
      - refactor-qa-agent@0.1.x
```

### Installer Behavior

`install_refactory.py` should perform these steps:

1. Resolve repo root.
2. Verify required tools.
3. Install `oxigraph-cli` guidance if missing.
4. Create `.startup/` and `.refactor/` directory layout.
5. Copy runtime scripts into `.refactor/scripts/`.
6. Write `.refactor/.gitignore`.
7. Write the repo startup wrapper.
8. Seed `.refactor/docs/` and `.refactor/rules/` with either:
   - nothing
   - demo fixtures
   - a selected seed bundle
9. Run `preflight.py`.
10. Run `session_start.py --mode startup`.
11. Show the exact startup context preview.

### Runtime File Ownership

The installed repo should have a clear ownership model:

- `.refactor/scripts/*`
  - owned by the toolkit runtime
- `.refactor/docs/*`
  - owned by rule authors
- `.refactor/rules/*`
  - owned by rule authors
- `.refactor/db/*`
  - owned by the local runtime only
- `.refactor/logs/*`
  - owned by the local runtime only

This split matters for update behavior. Toolkit upgrades must not overwrite user-authored rules or docs.

### Upgrade Behavior

Future package upgrades should:

- update runtime scripts
- update skills and agents
- preserve `.refactor/docs/`
- preserve `.refactor/rules/`
- preserve `.startup/team-lead` if unchanged or template-compatible
- never preserve stale `.refactor/db/`; it should be disposable

## Execution Model

The runtime should support plan-driven refactoring execution rather than ad hoc autonomous edits.

### Plan Requirements

Every plan item should include:

- target repo or repo set
- authorized rule or rules
- expected approved change shape
- validation notes
- wave assignment
- commit boundary

No plan item may exist without a backing approved rule.

### Wave Model

Recommended loop:

1. Orchestrator defines the next development wave.
2. Development agents execute only assigned authorized items.
3. QA agents review the resulting diff for full rule compliance.
4. Failed items return to rework or escalation.
5. Approved wave becomes eligible for commit.
6. Commit occurs only after QA approval for that wave.

### QA Gate

QA is mandatory in this system.

QA must answer:

- Is every change justified by a rule in `.refactor/`?
- Were all tandem edits required by the rule completed?
- Were any extra edits introduced?
- Does the implementation match the approved fix shape closely enough?
- Is a new rule required because the change fell outside the existing catalog?

If any answer is negative, the wave is not committable.

### Named Teammate Requirement

Per the v0.6 guidelines, this design should use named teammates for the long-running coordination layer.

Required teammate roles:

- `refactor-orchestrator`
- `quality-manager`

These teammates should:

- persist across waves
- coordinate via structured messages
- spawn background sub-agents directly
- own execution and QA lifecycle state

## Seed Content Model

To keep the package general while still useful, installation should support optional seed bundles.

Example models:

- `--seed empty`
  - install runtime only
- `--seed examples`
  - install demo rules for validation and onboarding
- `--seed <bundle-name>`
  - install a campaign-specific starter pack

Seed bundles should be separate from the runtime package and versioned independently where possible.

## Validation Requirements

The package should ship automated validation fixtures for:

- startup context emission
- preflight success
- preflight failure messaging
- lookup of a known trigger
- write of a new rule
- QA rejection of unauthorized edits
- orchestrator wave gating
- rebuild from committed rule files
- ignored runtime directories

Minimum acceptable validation surface:

```text
tests/
  fixtures/
    sample-refactor-repo/
  scripts/
    test_refactory_install.py
    test_refactor_lookup.py
    test_refactor_write.py
    test_session_start.py
```

## Long-Term Central Graph Model

The long-term architecture can support a large central graph, but local runtime should stay small.

Recommended model:

- central authoritative registry of rules, docs, prompts, and examples
- local subset sync based on repo, campaign, or active work
- local `.refactor/rules/` remains the immediate source used for local rebuild
- local `.refactor/db/` remains disposable compiled state

This preserves the fast local workflow:

- startup injects a compact trigger list
- lookup runs locally
- no network dependency during normal edits

## Recommendation

Make the toolkit runtime generic and keep all business or application intelligence in rule content.

That gives you:

- a package that can be deployed anywhere
- a rule set that can evolve independently
- a future central registry without rewriting the runtime
- agents that stay interpretable and bounded

## Rollout Plan

1. Package the current manual toolkit as `sc-refactory`.
2. Ship `refactory-install`, `refactor-lookup`, and `refactor-write`.
3. Freeze the local repo layout and script contracts.
4. Add validation fixtures for startup output and lookup results.
5. Add central graph export and subset sync later.

## Key Architectural Decision

The important abstraction is not “query Oxigraph.” The important abstraction is:

- approved fix knowledge is curated once
- startup injects a compact allowlist surface and explicit authorization boundaries
- lookup expands one trigger into exact instructions and examples
- write adds new approved knowledge without polluting runtime state
- orchestration turns approved rules into bounded execution waves
- QA enforces 100% rule compliance before commit

That is the system this package must install.
