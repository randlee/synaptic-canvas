# Implementation Plan: Infallible Usage

## Overview

Use `Infallible` or a direct return type when failure is not a real possibility. This makes error boundaries auditable and avoids fake error plumbing.

The point is not to add cleverness. The point is to make the code honest about what can actually fail.

## Design Goals

1. Make impossible failure explicit
2. Avoid meaningless error types
3. Make `unwrap()` safety auditable through the type system
4. Keep conversion and parser boundaries honest

---

## Core Cases

Use this practice when:
- a function returns `Result<T, E>` but `E` is never constructed
- a conversion/parser is structurally guaranteed to succeed
- a boundary expects a result type but the local implementation is infallible
- a code path uses `unwrap()` safely only because failure is impossible

## Review Signals

Look for:
- `Result<T, E>` where `E` is never constructed
- conversion/parsing code that cannot actually fail
- placeholder `String` or generic error types on guaranteed-success paths
- code where callers always unwrap because the error is not meaningful

## Common Violations

- returning `Result<T, String>` out of habit
- custom error enums with dead variants
- infallible conversions pretending to be fallible
- `unwrap()` justified socially instead of structurally

---

## Decision Rules

Ask:
- Can this operation actually fail in practice?
- Is the error type carrying real information?
- Is the surrounding abstraction the reason a result type exists?

Possible outcomes:

1. **Truly infallible and no result boundary needed**
   - return `T`

2. **Truly infallible but generic/result-based boundary expects it**
   - use `Result<T, Infallible>`

3. **Can fail, but current implementation does not yet expose it**
   - keep `Result<T, E>` only if the failure model is real and planned

## Example Direction

Weak:
```rust
fn normalize_name(s: &str) -> Result<String, String> {
    Ok(s.trim().to_lowercase())
}
```

Better:
```rust
fn normalize_name(s: &str) -> String {
    s.trim().to_lowercase()
}
```

Or, if a generic result boundary matters:
```rust
use std::convert::Infallible;

fn normalize_name(s: &str) -> Result<String, Infallible> {
    Ok(s.trim().to_lowercase())
}
```

---

## Remediation

- simplify to `T` when there is no meaningful error boundary
- use `Result<T, Infallible>` when the surrounding abstraction expects a result type
- remove dead error variants and fake error plumbing
- replace casual `unwrap()` with a shape that makes safety obvious to readers and reviewers

## Review Output

When reporting this finding:
- state why the failure path is not real
- point to the dead error path or dead error variants
- recommend either direct return or `Infallible`
