# Implementation Plan: Interior Mutability Justification

## Overview

Interior mutability is powerful and sometimes necessary, but it should be a deliberate design choice rather than a convenience escape hatch from ownership design.

This pattern exists to make reviewers ask whether shared mutation is truly part of the design or whether the code is fighting Rust’s ownership model.

## Design Goals

1. Make the reason for shared mutation explicit
2. Match the mutation primitive to the concurrency model
3. Avoid hiding mutation behind innocent-looking shared methods without good reason
4. Prefer ownership redesign where that is clearer

---

## Common Primitives

| Primitive | Typical Use | Risk |
|---|---|---|
| `Cell<T>` | copyable interior updates | easy to hide mutation |
| `RefCell<T>` | single-threaded runtime borrow checking | panic on borrow rule violation |
| `Mutex<T>` | cross-thread exclusive mutation | contention, lock scope mistakes |
| `RwLock<T>` | mostly-read, occasionally-write shared state | upgrade/downgrade complexity, starvation depending on impl |

## Review Signals

Look for:
- `RefCell`, `Cell`, `Mutex`, `RwLock`
- mutation behind `&self`
- caches, lazy init, counters, registries, or shared state
- concurrent code using the wrong primitive
- code comments that imply “Rust wouldn’t let me otherwise”

## Common Violations

- `RefCell` used because normal borrowing was inconvenient
- shared mutation with no explanation of why ownership flow was not used
- `RefCell` used in contexts that are or may become cross-thread
- locking or borrowing primitives chosen without relation to actual usage semantics
- mutation hidden in methods that look observational

---

## Review Questions

Ask:
- Why is shared mutation necessary here?
- Would a different ownership boundary remove the need?
- Is the chosen primitive safe for the concurrency model?
- Is mutation visible enough to future readers and reviewers?
- What is the failure mode if this primitive is misused: panic, deadlock, race, contention?

## Strong Justifications

Acceptable reasons often include:
- memoization or caching on a genuinely read-oriented API
- lazy initialization
- counters or metrics where shared mutation is the point
- shared state behind a thread-safe boundary whose ownership is genuinely distributed

Weak reasons:
- “this was the fastest way to make the borrow checker happy”
- “moving ownership around was annoying”
- “we may need concurrency later” without actual design support

---

## Code Review Smells

| Smell | Concern | Likely Direction |
|---|---|---|
| `RefCell` inside a type later shared across tasks | wrong concurrency primitive | redesign or use `Mutex`/`RwLock` |
| mutation in an `&self` method with no docs | hidden behavior | add rationale or redesign |
| deeply nested `borrow_mut()` patterns | ownership model mismatch | redesign ownership |
| lock spans around broad work | contention and hidden coupling | narrow lock scope |

---

## Remediation

- add explicit rationale in code or design docs
- redesign ownership if it simplifies the code materially
- replace the primitive with the correct one for single-threaded vs multi-threaded access
- narrow mutation scope so shared mutation is explicit and local

## QA Review Output

When reporting a finding:
- name the primitive
- explain why the current use is weak or risky
- say what ownership or primitive change should be considered
- state whether the problem is design-level or code-level
