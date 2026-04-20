# Implementation Plan: Trait Object Safety

## Overview

If a trait is intended for dynamic dispatch, object safety must be part of the API design rather than a late discovery after implementation has started.

This is a design-review pattern because the pain comes from discovering too late that a “plugin” or “handler” trait cannot actually be used as `dyn Trait`.

## Design Goals

1. Align trait shape with intended dispatch style
2. Detect object-safety problems at design time
3. Avoid publishing APIs that look like plugin surfaces but cannot be used as `dyn Trait`

---

## Strong Candidates

Use this review when the design mentions:
- plugins
- handlers
- backends
- drivers
- processors
- heterogeneous registries
- boxed trait objects
- runtime-selected implementations

## Review Signals

Look for:
- generic methods on candidate plugin/handler traits
- `Self` in return position where `dyn Trait` is expected
- no explicit statement whether dispatch is static or dynamic
- trait bounds that make object use awkward or impossible

## Common Violations

- generic methods on a trait intended for dynamic dispatch
- `Self` in return position where `dyn Trait` is expected
- no clear decision between static and dynamic dispatch
- traits presented as extension points but only usable monomorphically

---

## Design Review Questions

Ask:
- Is `dyn Trait` actually intended here?
- Will downstream users need heterogeneous collections of implementors?
- Are generic methods or `Self` returns preventing the intended usage?
- Would splitting the API into an object-safe core plus generic extension methods make the design clearer?

## Example Failure Modes

- registry of handlers cannot compile because the trait is not object-safe
- trait meant for runtime plugin loading only works with generics
- downstream code forced into awkward enums or wrappers because the trait shape is wrong

---

## Remediation

- redesign the trait for object safety
- split generic/static behavior into separate traits
- or document clearly that static dispatch is the intended design

## Boundary Review Guidance

For crate-boundary review:
- verify object safety before publishing a plugin-like API
- pair this check with the sealed-trait review when the trait is both dynamic and controlled
- require the design to state whether downstream consumers are expected to box/store trait objects
