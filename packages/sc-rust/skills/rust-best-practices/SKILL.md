---
name: rust-best-practices
version: 0.11.0
description: Review Rust architecture plans, crate boundaries, and code for structural design-pattern compliance. Use when the task involves typestate, sealed traits, error contracts, wrapper/newtype design, object safety, interior mutability, or other type-system-driven Rust correctness patterns that go beyond general style guidance.
depends_on:
  rust-best-practices-agent: 0.x
  rust-architect: 0.x
  rust-code-reviewer: 0.x
  rust-code-explorer: 0.x
---

# Rust Best Practices

This skill is the canonical source of truth for structural Rust pattern review in Synaptic Canvas. It complements `rust-development` by focusing on type-system-driven correctness, API-boundary design, and the lifecycle stage where each pattern should be enforced.

## Scope

Use this skill for:
- architecture and design review of Rust plans
- crate-boundary and public API review
- code review for structural Rust pattern compliance
- QA review when the goal is to enforce documented best-practice patterns

This skill does not cover service-runtime hardening such as timeouts, graceful shutdown, request IDs, retries, readiness probes, or backpressure. Those belong in `rust-service-hardening`.

## Canonical Inventory

Read these files in order:

- `patterns/practice-inventory.md` — canonical practice ids, names, lifecycle stage, and review applicability
- `patterns/enforcement-strategy.md` — enforcement heuristics, stage mapping, and review guidance

Read these additional pattern docs only when the practice under review requires them:
- `patterns/error-context-recovery-plan.md`
- `patterns/typestate-plan.md`
- `patterns/sealed-traits-plan.md`
- `patterns/newtype-zero-cost-plan.md`
- `patterns/deref-coercion-plan.md`
- `patterns/interior-mutability-plan.md`
- `patterns/infallible-plan.md`
- `patterns/trait-object-safety-plan.md`
- `patterns/cow-plan.md`
- `patterns/phantomdata-capability-token-plan.md`

## Review Modes

### Design Review

Use for plans, architecture documents, and implementation blueprints.

Focus on:
- error contracts and recovery inventory
- typestate opportunities
- sealed traits and crate extension boundaries
- newtype / deref / zero-cost wrapper design
- trait object safety when plugin-style dispatch is intended
- capability-token / `PhantomData` patterns for resource invariants

### Code Review

Use for implemented Rust code.

Focus on:
- missing structured error context and recovery guidance
- repeated primitive validation that should become newtypes
- unsafe or weakly justified interior mutability
- `Result<T, E>` shapes that should be simplified or made `Infallible`
- unnecessary ownership on hot paths where `Cow` fits
- wrappers whose ergonomics justify `Deref`/`AsRef`/`Borrow`

### Crate Boundary Review

Use when extracting crates or defining public traits and extension points.

Focus on:
- sealed traits
- trait object safety
- wrapper/newtype boundaries for semantic ids and validated values
- which patterns must be enforced before downstream API exposure

## Agent Delegation

This skill delegates pattern review work to existing Rust agents when specialized execution is needed:

| Operation | Agent | Returns |
|-----------|-------|---------|
| Dedicated structural pattern review | `rust-best-practices-agent` | Fenced JSON `{success,data,error}` with findings keyed by stable practice id |
| Architecture or plan review | `rust-architect` | Fenced JSON `{success,data,error}` blueprint or design findings |
| Code review for structural findings | `rust-code-reviewer` | Fenced JSON `{success,data,error}` findings summary |
| Pattern discovery across a codebase | `rust-code-explorer` | Fenced JSON `{success,data,error}` with located files and pattern usage |

Invoke these agents via Agent Runner using `.claude/agents/registry.yaml`. Require them to load `rust-best-practices` and the specific pattern references relevant to the requested review.

Dedicated `rust-best-practices-agent` assignment template:

```json
{
  "review_mode": "doc_review | sprint_review | phase_end",
  "worktree_path": "/absolute/path/to/worktree",
  "review_targets": [
    "src/",
    "Cargo.toml"
  ],
  "practice_mode": "all | selected",
  "practice_ids": [
    "RBP-001",
    "RBP-004"
  ],
  "notes": "optional context"
}
```

## Output Expectations

When using this skill for review:
- identify the practices reviewed by stable practice id
- report all real findings in scope
- include `file:line` and remediation guidance for each finding
- treat severity as ordering, not as permission to omit a real finding
- do not dismiss findings as pre-existing or not worsened

## Relationship to Other Skills

- `rust-development`: general Rust style, idioms, documentation, and implementation guidance
- `rust-best-practices`: structural correctness patterns and lifecycle enforcement
- `rust-service-hardening`: service-runtime production defaults for Tokio and similar Rust services
