# Implementation Plan: `PhantomData` Lifetime / Capability Token

## Overview

Use `PhantomData` to encode lifetime or capability relationships without storing a live reference. This is especially useful for guards, tokens, and APIs where type-level proof matters more than runtime data.

This pattern is most useful in designs where access should require proof, not just convention.

## Design Goals

1. Encode borrowing or capability invariants in the type system
2. Prevent illegal resource access through explicit proof types
3. Keep the runtime representation zero-sized when the token carries no data

---

## Strong Candidates

Use when the design has:
- capability tokens
- guards that authorize access to a resource
- APIs that should only work while a lifetime or borrow relationship is active
- proof objects that carry no runtime data but do carry invariants

## Review Signals

Look for:
- token or guard APIs
- resource acquisition/release protocols
- comments describing lifetime/capability relationships that are not enforced by types
- zero-sized markers or proof types implied by the design

## Common Violations

- capability relationships enforced only by comments
- tokens that do not actually prove anything about access
- borrowed/resource invariants left informal
- APIs that rely on “call X before Y” but have no type-level proof object

---

## Core Pattern Direction

Typical design:
- resource owner issues a token
- token is tied to the owner or borrow lifetime via `PhantomData`
- privileged operations require the token
- no token means no access

This is especially good for:
- single-acquisition guarantees
- temporary capability grants
- resource guard APIs

## Review Questions

Ask:
- Is there a capability or lifetime relationship the API is currently describing only in prose?
- Would a zero-sized token or guard eliminate a class of misuse?
- Is `PhantomData` actually the right proof mechanism, or would a more explicit ownership redesign be clearer?

## Remediation

- introduce token or guard types
- tie those types to the relevant lifetime or capability with `PhantomData`
- make illegal access impossible without the required proof object

## Output Guidance

When reporting this finding:
- identify the capability relationship currently enforced informally
- explain what misuse the current API allows
- recommend token/guard types with lifetime or capability encoding
