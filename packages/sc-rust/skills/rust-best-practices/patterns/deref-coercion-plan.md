# Implementation Plan: Deref Coercion for Wrapper Ergonomics

## Overview

Use `Deref`, `AsRef`, or `Borrow` to make wrapper types ergonomic when the wrapper is intentionally meant to behave like a borrowed view of its inner value.

This pattern is not about hiding meaning. It is about reducing boilerplate when the wrapper’s read-only behavior is intentionally close to the inner type.

## Design Goals

1. Preserve the semantic value of the wrapper type
2. Avoid unnecessary pass-through boilerplate
3. Keep wrapper behavior unsurprising
4. Avoid hiding materially different semantics behind familiar interfaces

---

## Core Pattern: Rust

```rust
use std::ops::Deref;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NonEmptyString(String);

impl NonEmptyString {
    pub fn new(value: impl Into<String>) -> Result<Self, &'static str> {
        let value = value.into();
        if value.trim().is_empty() {
            return Err("string must not be empty");
        }
        Ok(Self(value))
    }
}

impl Deref for NonEmptyString {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<str> for NonEmptyString {
    fn as_ref(&self) -> &str {
        &self.0
    }
}
```

This gives the wrapper ergonomic borrowed-string behavior without giving up the wrapper’s construction invariant.

---

## When to Use

Good fits:
- validated string-like wrappers that should still behave like `&str`
- path-ish or slice-like wrappers used primarily for reading/borrowing
- wrappers where callers repeatedly need read-only access to the inner borrowed view

Weak fits:
- wrappers with nontrivial behavior or policy
- wrappers whose semantics should stay explicit at call sites
- wrappers where implicit access would make misuse easier

## Review Signals

Look for:
- many trivial forwarding methods
- callers repeatedly reaching into `.0` or `inner()`
- wrappers that are semantically transparent for reads but awkward to use
- resistance to wrapper adoption purely because the API feels cumbersome

## Common Violations

- adding `Deref` to make a wrapper “feel easier” when the type should remain explicit
- exposing the wrapper as if it were identical to the inner type when invariants or semantics differ materially
- using `Deref` where `AsRef` would be clearer and safer
- adding mutable deref when mutation should stay controlled

## Decision Ladder

Use this order:

1. Can callers live with explicit methods?
2. If not, would `AsRef` or `Borrow` be enough?
3. Only then consider `Deref`.

`Deref` should be the most deliberate choice because it changes how the type participates in method lookup and coercion.

---

## Review Questions

Ask:
- Is the wrapper meant to be read as its inner borrowed type?
- Would transparent borrowing make misuse easier?
- Would `AsRef` cover the needed ergonomic improvement with less implicitness?
- Is the wrapper carrying business meaning that should remain visible?

If the wrapper’s semantics are materially richer than the inner type, default away from `Deref`.

---

## Good and Weak Outcomes

Good outcome:
- callers can use borrowed read-only APIs naturally
- the wrapper still controls construction and invariants
- the transparency feels expected, not magical

Weak outcome:
- callers forget they are working with a semantic wrapper
- important invariants become less visible
- unrelated behavior is smuggled in under a familiar borrowed API

---

## Remediation

- prefer `AsRef` or `Borrow` first
- use `Deref` only when the wrapper is intentionally transparent
- document why transparent coercion is correct for the wrapper
- avoid `DerefMut` unless mutability of the inner value truly preserves the wrapper’s invariants
