# Rust Design Patterns — Enforcement Strategy for AI-Assisted Development

## Purpose

This document defines a set of high-value Rust design patterns and prescribes **where in the development lifecycle** each should be enforced by Claude Code agents, skills, or commands. The goal is to catch design-level issues before they become code-level churn.

## Guiding Principles

1. **Patterns that prevent churn belong in design review.** If retrofitting a pattern requires significant refactoring, catch it before code exists.
2. **Patterns that improve existing code belong in code review.** If a pattern can be injected with a localized refactor, a review-stage agent is appropriate.
3. **Don't mix concerns.** A code-review agent proposing typestate refactors generates noise. A design agent worrying about `Cow` optimization is premature.

## Severity Definitions

- `Blocking`: must be fixed before the work can progress to the next lifecycle stage.
- `Important`: should be fixed before broad rollout; may be deferred only with explicit
  approval and documented follow-up.
- `Minor`: an effort to fix minor violations should be made unless significant effort is
  necessary. A one-line fix is easier to fix and review than it is to create and track a
  GH issue to fix later. If another pass is being made anyway to fix blocking/important
  issues, fix minor issues in that same pass if doing so takes less than a few minutes
  (Claude time). Do not defer a trivial fix to a separate issue unless the fix is
  contested.

---

## Pattern Inventory

### 1. Error Context + Recovery ⭐ TOP 3

**What:** Structured error types that carry cause chains, recovery steps, and documentation links — not just "what happened" but "why" and "how to fix it."

**Enforcement point:** Library-first, then design review, then code review, then CI.

**Cross-language applicability:**

| Language | Native support | Approach |
|----------|---------------|----------|
| Rust | `thiserror` + custom `RecoverableError` struct | Enum variants with `#[error]` + recovery fields |
| C# / .NET | `Exception` inheritance | Custom exception base with `Recovery` property |
| Python | Exception chaining (`raise X from Y`) | Custom exception class with `recovery_steps` |
| TypeScript | `Error` + custom classes | `RecoverableError` class with structured JSON |
| Go | `errors.Wrap` / `fmt.Errorf` | Sentinel errors + structured error types |

**Impact:** Highest churn-reduction of all patterns. Bad errors cascade across agent boundaries, cause debugging spirals, and generate user-filed issues.

**See:** `error-context-recovery-plan.md` for full implementation plan.

---

### 2. Typestate Pattern ⭐ TOP 3

**What:** Encode state machine transitions in the type system so invalid states are unrepresentable. The compiler rejects illegal transitions.

**Enforcement point:** Design review / plan review. By code review, retrofitting is expensive.

**Cross-language applicability:**

| Language | Feasibility | Approach |
|----------|-------------|----------|
| Rust | Native (PhantomData + generics) | Zero-cost, compiler-enforced |
| C# / .NET | Partial (generic constraints) | Generics with marker interfaces; less ergonomic |
| TypeScript | Good (branded types + generics) | Branded types simulate phantom types |
| Python | Weak (runtime only) | Protocol classes + `@overload`; no compile-time enforcement |
| Go | Weak (no generics until 1.18, limited) | Interface-per-state; verbose but works |

**Impact:** Eliminates entire categories of runtime state-machine bugs. High value for protocol handlers, connection lifecycles, build pipelines, authentication flows.

**See:** `typestate-plan.md` for full implementation plan.

---

### 3. Sealed Trait Pattern ⭐ TOP 3

**What:** Prevent external implementations of your traits. Maintain control over behavior evolution without breaking downstream consumers.

**Enforcement point:** API design phase / crate boundary review. Must be decided when defining public trait surfaces.

**Cross-language applicability:**

| Language | Feasibility | Approach |
|----------|-------------|----------|
| Rust | Idiomatic (private supertrait) | `mod sealed { pub trait Sealed {} }` |
| C# / .NET | Native | `internal` interface inheritance or `sealed` keyword |
| TypeScript | Partial | Module-scoped symbols as brand markers |
| Python | Weak | `abc.ABC` + `__init_subclass__` guard |
| Go | Natural (unexported interface method) | Add lowercase method to interface |

**Impact:** Critical for crate/package ecosystems. Prevents downstream breakage when evolving trait/interface surfaces.

**See:** `sealed-traits-plan.md` for full implementation plan.

---

### 4. Newtype / Zero-Cost Abstraction Pattern

**What:** Wrap primitives in domain-specific types to enforce invariants and prevent unit confusion. `Kilometers(f64)` vs `Miles(f64)` — the compiler catches misuse.

**Enforcement point:** Design phase for new types; code review for retrofitting.

**Cross-language applicability:**

| Language | Feasibility | Approach |
|----------|-------------|----------|
| Rust | Native (tuple structs, `Deref`) | Zero-cost after compilation |
| C# / .NET | Good (`readonly record struct`) | Value types; near-zero overhead |
| TypeScript | Good (branded types) | `type UserId = string & { __brand: 'UserId' }` |
| Python | Moderate (`NewType` from `typing`) | Runtime class or `NewType` for static checkers |
| Go | Good (type aliases with methods) | `type Kilometers float64` |

**Recommended agent integration:**
- **Design agent** proposes newtypes when plans mention validated inputs, physical quantities, or semantic IDs.
- **Code review command** (`/newtype-audit`) scans for repeated validation on the same primitive type across call sites — if `.trim()` appears on the same `String` in 3+ places, that's a newtype candidate.

---

### 5. Cow (Clone-on-Write) Pattern

**What:** Defer cloning until mutation is actually needed. `Cow::Borrowed` avoids allocation on the common path; `Cow::Owned` allocates only when data must change.

**Enforcement point:** Code review / performance review. This is a refactoring opportunity, not a design concern.

**Cross-language applicability:**

| Language | Feasibility | Approach |
|----------|-------------|----------|
| Rust | Native (`std::borrow::Cow`) | Zero-cost abstraction |
| C# / .NET | Partial | `ReadOnlySpan<T>` / `Memory<T>` for similar semantics |
| Python | N/A | Reference semantics; not applicable |
| TypeScript | N/A | Reference semantics; not applicable |
| Go | Manual | Copy-on-write via pointer + flag |

**Recommended agent integration:**
- **`/perf-audit` command** identifies functions accepting owned types (`String`, `Vec<u8>`) on hot paths where most inputs pass through unmodified. Suggests `Cow` refactoring.

---

### 6. Interior Mutability Pattern

**What:** Mutate through shared references (`&self`) when runtime borrowing rules are acceptable. `RefCell`, `Cell`, `Mutex`, `RwLock`.

**Enforcement point:** Code review, with mandatory justification.

**Cross-language applicability:**

| Language | Feasibility | Notes |
|----------|-------------|-------|
| Rust | Native (`RefCell`, `Cell`, `Mutex`) | Runtime borrow checks; panic on violation |
| Other languages | N/A | Mutable-by-default; pattern doesn't apply |

**Recommended agent integration:**
- **Code review hook** (sc-hooks): If `RefCell` or `Cell` appears, require a comment explaining why shared mutability is needed. For concurrent code (`Send + Sync` contexts), flag `RefCell` and suggest thread-safe alternatives.

---

### 7. Infallible Pattern

**What:** Use `Result<T, Infallible>` to document that an operation cannot fail. Makes `unwrap()` auditable.

**Enforcement point:** Code review (lint-level).

**Cross-language applicability:** Rust-specific. Other languages lack the type-level expressiveness to make this meaningful.

**Recommended agent integration:**
- **Code review hook**: Flag `Result<T, E>` return types where the error variant is never constructed. Suggest simplifying to `T` or `Result<T, Infallible>`.

---

### 8. Trait Object Safety Pattern

**What:** Design traits for dynamic dispatch compatibility — no generic methods, no `Self` in return position.

**Enforcement point:** Design phase for plugin/extension traits. The compiler catches violations, but the design agent should verify intent upfront.

**Cross-language applicability:** Rust-specific (other languages use virtual dispatch by default).

**Recommended agent integration:**
- **Crate boundary agent**: For any `pub trait` intended for plugin use, verify object safety during API design review.

---

### 9. PhantomData Lifetime Pattern

**What:** Use `PhantomData` to tie lifetimes without storing references. Creates zero-size tokens that enforce borrowing invariants.

**Enforcement point:** Design phase for resource guards and capability tokens.

**Cross-language applicability:** Rust-specific.

**Recommended agent integration:**
- Document as a design pattern in workspace CLAUDE.md files. Too specialized for a generic agent — trigger manually when designing resource access patterns.

---

## Agent / Skill / Command Summary

| Tool | Type | Trigger Point | Patterns Enforced |
|------|------|---------------|-------------------|
| `design-review` | Agent | Plan doc creation | Typestate, Sealed, Newtype, Error inventory |
| `crate-boundary` | Agent | Crate extraction / API changes | Sealed, Trait object safety |
| `/error-audit` | Command | Pre-commit / CI | Error Context + Recovery |
| `/newtype-audit` | Command | Code review | Newtype, Zero-cost units |
| `/perf-audit` | Command | Performance review | Cow, Infallible cleanup |
| `refcell-gate` | Hook | Post-commit | Interior mutability justification |

## Priority

1. **Error Context + Recovery** — foundation layer; everything else benefits from better errors
2. **Typestate** — catches the most expensive bugs (invalid state transitions) at zero runtime cost
3. **Sealed Traits** — critical for any multi-crate / multi-package ecosystem
4. **Newtype** — steady value; prevents unit confusion and validation duplication
5. **Cow / Interior Mutability / Infallible** — incremental improvements; build as needed
