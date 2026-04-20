# Rust Best Practices Inventory

This file is the canonical practice inventory for `rust-best-practices`.

Every practice has a stable id. Agents and reviewers must use these ids instead of maintaining a separate hardcoded list.

Use this file for:
- stable ids and naming
- what each practice is trying to prevent
- when a practice applies
- what reviewers should look for
- what kinds of findings should be reported

Use `enforcement-strategy.md` for lifecycle-stage mapping and overall review heuristics.

## Practice Table

| Id | Practice | Primary Stage | Applies To |
|----|----------|---------------|------------|
| `RBP-001` | Error Context + Recovery | Design review, code review, CI | plans, CLIs, APIs, libraries, services |
| `RBP-002` | Typestate | Design review | plans, protocols, state machines, resource lifecycles |
| `RBP-003` | Sealed Trait | Design review, crate-boundary review | public traits, extension points, published crates |
| `RBP-004` | Newtype / Zero-Cost Abstraction | Design review, code review | semantic ids, validated primitives, physical quantities |
| `RBP-005` | Deref Coercion for Wrapper Ergonomics | Design review, code review | wrapper/newtype APIs where transparent borrowing is intended |
| `RBP-006` | Interior Mutability Justification | Code review | `RefCell`, `Cell`, `Mutex`, `RwLock`, shared mutation |
| `RBP-007` | Infallible Usage | Code review | functions returning `Result<T, E>` where failure is impossible |
| `RBP-008` | Trait Object Safety | Design review, crate-boundary review | plugin/extension traits, dynamic dispatch surfaces |
| `RBP-009` | `Cow` / Clone-on-Write | Code review, performance review | hot paths, APIs that often borrow but sometimes allocate |
| `RBP-010` | `PhantomData` Lifetime / Capability Token | Design review | borrowing invariants, resource guards, capability tokens |

## Practice Details

### `RBP-001` Error Context + Recovery

**Goal**

Make errors explain:
- what happened
- why it happened
- how to fix it
- where to learn more when documentation exists

**Use when**

- a plan introduces new failure modes
- a CLI or service returns machine-readable errors
- an API surface needs stable error codes
- users or automation must be able to recover without reading source code

**Reviewer should look for**

- opaque `String`-based errors
- error paths with no stable code
- missing recovery steps
- missing cause/context as errors cross abstraction layers
- inconsistent JSON error shape across commands/endpoints

**Common violations**

- `map_err(|e| format!(...))` that loses structure
- “config invalid” with no explanation of what is wrong
- user-facing errors that cannot tell the caller what to do next
- errors that are human-readable but not machine-parseable

**Good finding shape**

- identify the missing context or recovery guidance
- point to the specific error path
- recommend a structured error variant or stable envelope

**Primary remediation**

- adopt a structured error type
- add stable error codes
- add cause, recovery steps, and docs link where useful

**Deep reference**

- `error-context-recovery-plan.md`

### `RBP-002` Typestate

**Goal**

Make illegal state transitions impossible at compile time instead of checking them at runtime.

**Use when**

- the design has explicit phases or lifecycle transitions
- operations are only valid after a previous step succeeds
- resources move through a strict protocol

**Reviewer should look for**

- “must X before Y” plans
- runtime boolean/state checks guarding methods
- `InvalidState` style errors that the type system could prevent
- state enums repeatedly matched in many methods

**Common violations**

- methods that begin by checking connection/auth/init state
- state machines represented only by booleans or enums in runtime logic
- plans that describe strict transitions but do not encode them in the type model

**Do not force this pattern when**

- the state space is highly dynamic or combinatorial
- states must be stored heterogeneously
- retrofitting would add large complexity for low value

**Primary remediation**

- introduce marker types and transition methods
- encode shared-state behavior with traits or generic impls

**Deep reference**

- `typestate-plan.md`

### `RBP-003` Sealed Trait

**Goal**

Keep public traits usable by downstream consumers while preventing external implementations when the implementation set should stay under crate control.

**Use when**

- the trait is public
- the implementor set is fixed or should remain controlled
- you need freedom to evolve the trait later

**Reviewer should look for**

- new `pub trait` definitions
- plugin-like APIs with unclear extension boundaries
- public traits where downstream implementation is not actually intended

**Common violations**

- open public trait where all implementations are internal
- trait evolution risk created by allowing external implementation accidentally
- public trait with no explicit seal/open decision

**Do not force this pattern when**

- the trait is intentionally a public extension point
- the whole point is downstream implementation

**Primary remediation**

- add the sealed-supertrait pattern
- document whether the trait is intentionally open or intentionally sealed

**Deep reference**

- `sealed-traits-plan.md`

### `RBP-004` Newtype / Zero-Cost Abstraction

**Goal**

Encode invariants and semantic meaning in the type system instead of relying on repeated primitive validation and developer memory.

**Use when**

- semantic ids are represented as `String`, `Uuid`, or integers
- validated strings or parsed values are passed around as raw primitives
- physical quantities/units can be confused

**Reviewer should look for**

- repeated validation/parsing of the same primitive shape
- multiple parameters of the same primitive type with different meaning
- unit confusion risk
- semantic ids represented as plain strings

**Common violations**

- `String` used for user id, workspace id, and path token with no distinction
- repeated `trim()`, parse, range check, or regex validation at many call sites
- raw numeric units where wrong-unit bugs are plausible

**Primary remediation**

- introduce domain-specific wrapper types
- move validation to constructors
- make invalid values impossible to construct

### `RBP-005` Deref Coercion for Wrapper Ergonomics

**Goal**

Make wrapper/newtype APIs ergonomic when they are intentionally meant to behave like borrowed views of their inner type.

**Use when**

- the wrapper is primarily semantic/validated but should still feel natural in read-only use
- explicit forwarding methods are adding noise without adding meaning

**Reviewer should look for**

- wrappers with many trivial pass-through accessors
- wrappers that obviously want string/slice-like ergonomics
- missing `AsRef`, `Borrow`, or carefully chosen `Deref`

**Common violations**

- ergonomic friction that causes callers to unwrap or reach into internals directly
- wrapper types bypassed because they are too awkward to use

**Do not force this pattern when**

- the wrapper has materially different semantics
- implicit access would hide surprising behavior
- the wrapper should remain explicit at call sites

**Primary remediation**

- add `AsRef`, `Borrow`, or `Deref` only when the transparency is intentional and safe

### `RBP-006` Interior Mutability Justification

**Goal**

Require deliberate justification when mutating through shared references or using runtime borrow checking.

**Use when**

- `RefCell`, `Cell`, `Mutex`, or `RwLock` appears
- shared mutation exists behind `&self`
- borrow rules are being relaxed at runtime

**Reviewer should look for**

- unexplained `RefCell` or `Cell`
- `RefCell` in concurrency-sensitive code
- mutation hidden inside seemingly cheap shared methods
- ownership design that could likely eliminate interior mutability

**Common violations**

- using `RefCell` as a convenience escape hatch
- mixing thread-safe and non-thread-safe mutation primitives carelessly
- no comment or design rationale for shared mutation

**Primary remediation**

- explain why shared mutation is necessary
- reconsider ownership flow
- choose the correct primitive for the concurrency model

### `RBP-007` Infallible Usage

**Goal**

Make “cannot fail” operations explicit and auditable instead of carrying meaningless error types.

**Use when**

- a function returns `Result<T, E>` but `E` is never meaningfully produced
- a conversion/parser is structurally guaranteed to succeed
- `unwrap()` is only safe because failure is impossible

**Reviewer should look for**

- dead error variants
- placeholder error types on obviously infallible paths
- unnecessary result wrapping that obscures what can actually fail

**Common violations**

- `Result<T, String>` where the function only ever returns `Ok`
- parser/conversion APIs carrying fake failure paths
- `unwrap()` defended only by convention instead of type shape

**Primary remediation**

- simplify to `T`
- or use `Result<T, Infallible>` when that boundary matters

### `RBP-008` Trait Object Safety

**Goal**

Ensure traits intended for dynamic dispatch actually support `dyn Trait` usage before the API is locked in.

**Use when**

- the design mentions plugins, handlers, processors, transports, or drivers
- trait objects or registry-based dispatch are intended

**Reviewer should look for**

- generic methods on traits intended for dynamic dispatch
- `Self` in return position where `dyn Trait` is expected
- unclear dynamic-vs-static dispatch intent

**Common violations**

- trait designed as an extension point but not object-safe
- object safety discovered only after implementation starts

**Primary remediation**

- redesign the trait for object safety
- or document that static dispatch is the intended model

### `RBP-009` `Cow` / Clone-on-Write

**Goal**

Avoid unnecessary allocations when most callers can borrow and only a minority need owned mutation.

**Use when**

- APIs often accept borrowed data and only sometimes transform it
- hot paths allocate eagerly despite a common no-copy path

**Reviewer should look for**

- owned `String`/`Vec` parameters on pass-through heavy paths
- frequent cloning before it is known to be needed
- transformation functions where most inputs remain unchanged

**Common violations**

- always-allocate API on a read-mostly path
- cloning inputs “just in case”

**Primary remediation**

- adopt `Cow` where the borrow-first/own-when-needed model fits naturally

### `RBP-010` `PhantomData` Lifetime / Capability Token

**Goal**

Encode borrowing, lifetime, or capability invariants without storing a live reference.

**Use when**

- a token or guard should prove access rights
- a resource should only be used while some lifetime/capability is in scope
- the type must carry a lifetime relationship without holding data

**Reviewer should look for**

- resource access protocols with capability tokens
- APIs where borrowing invariants are real but currently informal
- zero-sized proof types or guards implied by the design

**Common violations**

- capability relationships enforced only by comments
- resource access tokens with no type-level connection to the owning lifetime

**Primary remediation**

- introduce explicit token/guard types
- tie invariants to the type via `PhantomData`

## Review Rules

- Report all real findings in scope.
- Severity orders findings; it does not decide whether they exist.
- Use stable ids in review output and orchestration input.
- Do not dismiss findings as pre-existing or not worsened.
