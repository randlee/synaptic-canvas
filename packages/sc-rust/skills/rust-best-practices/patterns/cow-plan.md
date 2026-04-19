# Implementation Plan: `Cow` / Clone-on-Write

## Overview

Use `Cow` when the common path should borrow and only the uncommon path should allocate or clone.

This is primarily a code-review and performance-review pattern. It should improve hot-path behavior without making APIs harder to reason about.

## Design Goals

1. Avoid eager allocation on read-mostly paths
2. Keep APIs flexible for borrowed and owned callers
3. Only pay for ownership when mutation or transformation actually requires it

---

## Strong Candidates

Good fits:
- text or byte processing where most inputs pass through unchanged
- APIs that often borrow and only occasionally normalize/transform
- performance-sensitive code where cloning dominates the common path

Weak fits:
- APIs that always need owned data
- code paths where mutation is guaranteed
- simple non-hot code where `Cow` would add complexity without benefit

## Review Signals

Look for:
- functions taking owned `String` or `Vec` where most calls only inspect data
- transformations that only occasionally modify input
- repeated cloning before it is known to be necessary
- hot paths that allocate by default for convenience

## Common Violations

- always allocating for convenience on hot paths
- cloning “just in case”
- APIs that force ownership despite a strong borrow-first use case
- introducing `Cow` into cold code where clarity would be better with plain ownership

---

## Review Questions

Ask:
- Is the common path actually borrow-only?
- Is the code on a hot path or just generally performance-sensitive?
- Will `Cow` simplify caller behavior or make the API harder to understand?

`Cow` is valuable when the answer is:
- yes, common path borrows
- yes, allocations matter
- yes, the API still reads naturally

## Example Direction

Weak:
```rust
fn normalize(input: String) -> String {
    if input.contains("  ") {
        input.replace("  ", " ")
    } else {
        input
    }
}
```

Better:
```rust
use std::borrow::Cow;

fn normalize(input: Cow<'_, str>) -> Cow<'_, str> {
    if input.contains("  ") {
        Cow::Owned(input.replace("  ", " "))
    } else {
        input
    }
}
```

---

## Remediation

- adopt `Cow` when the borrow-first/own-on-change model is natural
- keep the API honest about when mutation actually occurs
- do not force `Cow` where ownership is already clearly required
- document or benchmark the hot path when the change is performance-motivated
