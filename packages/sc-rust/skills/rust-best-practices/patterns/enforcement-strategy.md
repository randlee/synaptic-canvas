# Rust Best Practices Enforcement Strategy

This document maps each canonical practice to the stage where enforcing it is cheapest and most reliable.

Read `practice-inventory.md` first for stable ids. Use this file to decide what to check in design review, code review, crate-boundary review, or performance review.

## Guiding Principles

1. Catch structural problems at the earliest stage where the correct shape is still cheap to adopt.
2. Keep style/lint concerns in `rust-development`; keep structural pattern concerns here.
3. Do not report speculative findings. Findings must tie back to a concrete practice and a specific review stage.
4. Report all real findings in scope. Severity affects ordering, not whether the finding exists.

## Stage Map

| Stage | Primary Practices |
|-------|-------------------|
| Design review | `RBP-001`, `RBP-002`, `RBP-003`, `RBP-004`, `RBP-005`, `RBP-008`, `RBP-010` |
| Code review | `RBP-001`, `RBP-004`, `RBP-005`, `RBP-006`, `RBP-007`, `RBP-009` |
| Crate-boundary review | `RBP-003`, `RBP-008`, `RBP-004` |
| Performance review | `RBP-009`, selective `RBP-006` |
| CI / hooks | error-shape checks from `RBP-001`, targeted audits for `RBP-006` and `RBP-007` |

## Review Cadence Matrix

Use this matrix to decide whether a practice should be reviewed during document review, sprint review, or phase-ending review.

Legend:
- `Run` — always review this practice in that mode
- `Skip` — do not normally review this practice in that mode
- `Trigger` — review only when the triggering conditions below are present

| Practice | Doc Review | Sprint | Phase End |
|----------|------------|--------|-----------|
| `RBP-001` Error Context + Recovery | `Run` | `Run` | `Run` |
| `RBP-002` Typestate | `Run` | `Skip` | `Trigger` |
| `RBP-003` Sealed Trait | `Trigger` | `Skip` | `Trigger` |
| `RBP-004` Newtype / Zero-Cost Abstraction | `Trigger` | `Run` | `Run` |
| `RBP-005` Deref Coercion for Wrapper Ergonomics | `Trigger` | `Skip` | `Run` |
| `RBP-006` Interior Mutability Justification | `Skip` | `Run` | `Run` |
| `RBP-007` Infallible Usage | `Skip` | `Run` | `Run` |
| `RBP-008` Trait Object Safety | `Trigger` | `Skip` | `Trigger` |
| `RBP-009` `Cow` / Clone-on-Write | `Skip` | `Trigger` | `Run` |
| `RBP-010` `PhantomData` Lifetime / Capability Token | `Trigger` | `Skip` | `Trigger` |

## Upstream Review Surface

In this matrix, `Doc Review` means upstream document-review agents such as `req-qa` and `arch-qa` should consider or trigger the practice. It does not mean those agents replace the specialized `rust-best-practices` review.

Use this split:
- `req-qa` and `arch-qa` identify missing or underspecified decisions in requirements/architecture docs
- `rust-best-practices` remains the specialized Rust pattern authority for design and code review

## Trigger Conditions

### `RBP-001` Error Context + Recovery

No trigger is needed. Always review this practice.

### `RBP-002` Typestate

Trigger when:
- architecture introduces explicit lifecycle or state transitions
- protocol/resource sequencing is central to the design
- invalid runtime states are currently prevented by convention rather than by type shape

### `RBP-003` Sealed Trait

Trigger when:
- a new or changed `pub trait` is introduced
- crate extraction or package API work is in scope
- an extension-point design question appears in requirements or architecture docs

### `RBP-004` Newtype / Zero-Cost Abstraction

Trigger in doc review when:
- semantic ids, units, or validated primitives appear in requirements or architecture docs
- raw primitives carry domain meaning across boundaries

Always run in sprint review when:
- repeated validation appears in touched code
- semantic ids or unit-bearing values are introduced or refactored in changed files

### `RBP-005` Deref Coercion for Wrapper Ergonomics

Trigger when:
- wrapper/newtype ergonomics are being designed or refactored
- many trivial forwarding methods or direct `.0` access patterns appear
- the design is deciding whether a wrapper should feel transparent in borrowed/read-only use

### `RBP-006` Interior Mutability Justification

Run whenever touched code includes:
- `RefCell`
- `Cell`
- `Mutex`
- `RwLock`

### `RBP-007` Infallible Usage

Run whenever touched code includes:
- `Result<T, E>` shapes that may be fake or dead
- conversions or parsers that cannot actually fail
- unwrap-safe-by-construction code paths

### `RBP-008` Trait Object Safety

Trigger when:
- dynamic dispatch, plugin systems, handlers, or registries are in scope
- a public trait is intended for `dyn Trait`
- heterogeneous collections of implementors are part of the design

### `RBP-009` `Cow` / Clone-on-Write

Trigger in sprint review when:
- touched code is performance-sensitive
- owned strings/vectors are used on borrow-mostly paths
- obvious eager cloning appears on a hot path

Always run at phase end because broader context is usually needed to judge whether `Cow` is the right tradeoff.

### `RBP-010` `PhantomData` Lifetime / Capability Token

Trigger when:
- capability tokens, guards, or proof objects appear in design
- resource access invariants are described in docs but not encoded in types
- the design implies borrowing/capability proof without a concrete type-level mechanism

## Practice Guidance

### `RBP-001` Error Context + Recovery

**Check in design review:**
- does the plan define new failure modes?
- is there an error inventory for new commands, endpoints, or agent interactions?
- does each important failure mode define:
  - a stable code
  - cause
  - recovery steps
  - docs link or reference when applicable

**Check in code review:**
- are errors propagated as opaque strings or generic wrappers with no recovery guidance?
- are user-facing JSON errors consistent and machine-parseable?
- do error types provide actionable recovery rather than vague advice?

**Minimum contract:**
- stable error code
- clear message
- cause
- recovery steps
- docs link where useful

Use `error-context-recovery-plan.md` for detailed implementation guidance.

### `RBP-002` Typestate

**Check in design review:**
- are there explicit or implicit state transitions?
- does the plan describe illegal transitions that should be compile-time impossible?
- would retrofitting typestate later be expensive?

Use `typestate-plan.md` when a real state machine is present.

### `RBP-003` Sealed Trait

**Check in design review and crate-boundary review:**
- is a `pub trait` intended for downstream implementation?
- does the trait need future evolution without downstream breakage?
- does the trait represent a fixed internal implementation set?

Use `sealed-traits-plan.md` for the full review and migration logic.

### `RBP-004` Newtype / Zero-Cost Abstraction

**Check in design review:**
- validated primitives repeated across the API
- semantic ids represented as raw strings or integers
- physical quantities or units passed as plain numeric types

**Check in code review:**
- repeated `trim`/parse/validate logic on the same primitive type
- call sites manually preserving the same invariant over and over
- primitive-typed parameters where semantic confusion is likely

### `RBP-005` Deref Coercion for Wrapper Ergonomics

**Check in design review and code review:**
- is a wrapper type intended to feel like a borrowed view of its inner type?
- would `Deref`, `AsRef`, or `Borrow` improve ergonomics without obscuring meaning?
- is the wrapper truly transparent, or does it carry materially different semantics that should stay explicit?

**Review rule:**
- use this pattern for ergonomic transparency
- do not use it to hide surprising behavior behind familiar APIs

### `RBP-006` Interior Mutability Justification

**Check in code review:**
- any `RefCell`, `Cell`, `Mutex`, or `RwLock` should have a clear reason
- in `Send + Sync` or cross-thread contexts, verify the primitive is concurrency-safe
- challenge interior mutability when ownership refactoring would be clearer

### `RBP-007` Infallible Usage

**Check in code review:**
- functions returning `Result<T, E>` where `E` is never actually constructed
- parser or conversion code that cannot fail but preserves a meaningless error type
- `unwrap()` calls that are only safe because the error is structurally impossible

**Review rule:**
- prefer `Result<T, Infallible>` or a direct `T` return when failure is impossible

### `RBP-008` Trait Object Safety

**Check in design review and crate-boundary review:**
- is the trait intended for dynamic dispatch?
- are there generic methods or `Self` return positions that break object safety?
- is the object-safety requirement documented before the public API is committed?

### `RBP-009` `Cow` / Clone-on-Write

**Check in code review and performance review:**
- APIs that take owned types even when the common path only reads
- hot paths where most calls do not need allocation or mutation
- serialization or transformation paths that only occasionally need to own data

### `RBP-010` `PhantomData` Lifetime / Capability Token

**Check in design review:**
- APIs that must tie access to a borrowed capability or guard without storing a reference
- resource-acquisition protocols that should prevent illegal reuse or aliasing
- token-based access flows where the token carries invariants rather than data

## Review Heuristics

### Design Review Heuristics

Look for:
- “must X before Y”
- “only valid when”
- new `pub trait` or plugin boundaries
- repeated validated primitives in the plan
- new commands/endpoints with undocumented failure behavior
- guard/token/resource access semantics that imply capability types

### Code Review Heuristics

Look for:
- opaque error strings
- repeated validation on raw primitives
- wrappers with clumsy forwarding methods
- `RefCell`/`Cell` with no rationale
- `Result<T, E>` where the error never occurs
- owned inputs in paths that usually only borrow

### Crate-Boundary Review Heuristics

Look for:
- new `pub trait`
- traits intended for `dyn Trait`
- crate extraction or package publication work
- public ids/units/validated strings still represented as primitives

## Relationship to QA Review

`rust-best-practices-agent` should treat this document as the stage-mapping reference for dedicated structural review.

The best-practices QA path must:
- reference practices by stable id
- report all real findings in scope
- never use a smaller, stale hardcoded inventory
- keep lifecycle-cadence decisions in orchestration policy rather than in the worker prompt
