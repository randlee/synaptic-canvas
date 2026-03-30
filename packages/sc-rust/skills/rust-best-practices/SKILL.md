---
name: rust-best-practices
version: 1.0.0
description: Enforce Rust design patterns at the right lifecycle stage — design review, code review, or CI. Use when reviewing architecture plans, crate API surfaces, or Rust code for pattern compliance. Complements rust-development (style/guidelines) by focusing on structural design patterns and when to apply them.
---

# Rust Best Practices

This skill enforces high-value Rust design patterns at the appropriate stage of the development lifecycle. Its primary purpose is to prevent churn by catching structural issues before they become expensive to fix.

## Scope

This skill covers **design patterns** — structural choices that affect API surfaces, state machines, error propagation, and crate boundaries. It does not duplicate the style and lint rules in `rust-development/guidelines.txt`.

## Pattern Documents

Pattern documentation lives in `patterns/`:

- [`enforcement-strategy.md`](patterns/enforcement-strategy.md) — Full pattern inventory with enforcement points, cross-language applicability, and agent integration recommendations

Additional per-pattern implementation plans (referenced from enforcement-strategy.md, added as available):
- `error-context-recovery-plan.md`
- `typestate-plan.md`
- `sealed-traits-plan.md`

## Enforcement Points

Patterns are enforced at the stage where catching them costs the least:

| Stage | Patterns |
|-------|----------|
| Design review | Typestate, Sealed Traits, Newtype (new types), Error inventory |
| Code review | Newtype (retrofit), Interior Mutability justification, Infallible |
| Performance review | Cow, allocation hot paths |
| CI / hooks | RefCell in `Send+Sync` contexts, `unwrap()` audit |

## Priority Order

When reviewing, apply in this order — higher priority patterns have greater churn-reduction impact:

1. Error Context + Recovery
2. Typestate
3. Sealed Traits
4. Newtype / Zero-Cost Abstraction
5. Cow, Interior Mutability, Infallible (incremental)

## Instructions

### Design Review Mode

When reviewing an architecture plan or design document:

1. Read `patterns/enforcement-strategy.md`
2. Identify state machines → apply Typestate check
3. Identify public trait surfaces intended for external use → apply Sealed Trait check
4. Identify validated primitives, semantic IDs, physical quantities → apply Newtype check
5. Identify error propagation paths → verify Error Context + Recovery is planned
6. Flag findings with pattern name, enforcement-strategy section reference, and concrete suggestion

### Code Review Mode

When reviewing Rust code:

1. Read `patterns/enforcement-strategy.md`
2. Check for `RefCell` / `Cell` in `Send + Sync` contexts → flag with justification requirement
3. Check for `unwrap()` on `Result<T, E>` where E is never constructed → suggest `Infallible`
4. Check for repeated primitive validation at call sites → suggest Newtype
5. Check for owned-type parameters (`String`, `Vec`) on hot paths → suggest `Cow`
6. Only report issues with clear, concrete impact — no speculative findings

### Crate Boundary Review Mode

When a new crate is being extracted or a public API is being defined:

1. For every `pub trait`: verify object safety if dynamic dispatch is intended
2. For every `pub trait` that must not be externally implemented: verify sealed pattern is applied
3. Flag missing sealed markers on extension points

## Relationship to Other Skills

- **rust-development**: Style, idioms, lint compliance, documentation standards. Use for code-level concerns.
- **rust-best-practices**: Structural design patterns, enforcement lifecycle, crate boundary contracts. Use for architecture-level concerns.

These skills are complementary and should both be active during full design + implementation reviews.

## Agent Delegation

For extended pattern analysis, delegate to existing agents:

- `rust-architect`: Architecture blueprints that incorporate pattern decisions
- `rust-code-reviewer`: Code-level pattern compliance (Infallible, Interior Mutability, Newtype retrofit)
- `rust-code-explorer`: Locate existing pattern usage across the codebase before designing new surfaces
