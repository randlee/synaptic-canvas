# Implementation Plan: Newtype / Zero-Cost Abstraction

## Overview

Wrap raw primitives in domain-specific types so invariants, semantic meaning, and units are enforced by the type system instead of repeated validation and developer memory.

This pattern prevents:
- semantic confusion between same-shaped primitives
- validation logic duplicated across call sites
- unit bugs that the compiler could have caught
- APIs that rely on comments instead of types to communicate meaning

## Design Goals

1. Prevent semantic confusion between same-shaped primitives
2. Move validation to construction time
3. Keep runtime overhead effectively zero
4. Make invalid values impossible or difficult to construct accidentally

---

## Core Pattern: Rust

```rust
use std::fmt;
use std::str::FromStr;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct UserId(String);

#[derive(Debug, thiserror::Error)]
pub enum UserIdError {
    #[error("user id must not be empty")]
    Empty,
    #[error("user id must be lowercase ascii plus '-'")]
    InvalidFormat,
}

impl UserId {
    pub fn new(value: impl Into<String>) -> Result<Self, UserIdError> {
        let value = value.into();
        if value.is_empty() {
            return Err(UserIdError::Empty);
        }
        if !value
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
        {
            return Err(UserIdError::InvalidFormat);
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for UserId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

impl FromStr for UserId {
    type Err = UserIdError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::new(s.to_owned())
    }
}
```

**What the type system now prevents:**
- passing arbitrary `String` values where a validated `UserId` is required
- mixing `UserId` with other semantic ids that happen to also be strings
- re-validating the same format at every boundary

---

## Strong Candidates

Use a newtype when you see:
- semantic ids represented as `String`, `Uuid`, `u64`, or `i32`
- validated text values reused across many call sites
- units or physical quantities
- user input that must always satisfy a format, range, or normalization rule
- distinct concepts that happen to share the same primitive shape

Examples:
- `UserId`, `ProjectSlug`, `RepositoryName`
- `Miles`, `Kilometers`, `Milliseconds`
- `EmailAddress`, `NonEmptyString`, `NormalizedPath`

## Weak Candidates

Avoid forcing a newtype when:
- the value has no durable semantic distinction
- the value is extremely local and will never cross a boundary
- the wrapper adds more ceremony than protection
- callers legitimately need many ad hoc primitive operations and the invariant is weak

---

## Review Signals

Look for:
- repeated parse/trim/validate logic on the same primitive
- many function parameters of the same primitive type with different meaning
- comments explaining semantic meaning that the type system could encode
- raw units that could be mixed up
- constructors and service boundaries rechecking the same invariant

## Common Violations

- `String` used for multiple domain ids
- same regex or validation logic repeated in several places
- plain `u64` or `f64` with no unit distinction
- constructor and call-site validation duplicated across modules
- public APIs taking raw primitives even though only a validated subset is acceptable

## Code Review Smells

Treat these as strong newtype signals:

| Smell | Example | Better Shape |
|---|---|---|
| Same parse logic repeated | `Uuid::parse_str(id)?` in five handlers | `UserId` newtype |
| Same trim/non-empty rule repeated | `.trim().is_empty()` everywhere | `NonEmptyString` |
| Same primitive with different meaning | `fn link(a: String, b: String)` | `ParentId`, `ChildId` |
| Units passed as `f64` | `timeout_secs`, `distance_km` | unit-specific wrappers |

---

## Design Review Questions

Ask:
- Is this primitive carrying domain meaning that should survive across module boundaries?
- Will the same invariant be checked in multiple places?
- Is there a risk of mixing two conceptually different values of the same underlying type?
- Does the wrapper make the API safer without making it unusable?

If the answer to two or more of those is yes, the default should usually be to propose a newtype.

---

## Migration Strategy

For new code:
1. Define the wrapper type first.
2. Centralize validation in constructor or parser impls.
3. Make downstream APIs accept the wrapper, not the raw primitive.

For existing code:
1. Identify the invariant and all repeated validation sites.
2. Introduce the wrapper type with conversion helpers.
3. Migrate API boundaries first.
4. Remove duplicate validation from call sites once the wrapper is threaded through.

---

## Relationship to Deref

If the wrapper should feel transparent for borrowed/read-only use, review `deref-coercion-plan.md` as a secondary design choice. Do not add `Deref` by reflex; first confirm that transparent borrowing matches the wrapper’s semantics.
