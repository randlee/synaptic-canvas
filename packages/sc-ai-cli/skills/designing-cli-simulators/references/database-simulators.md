# Database Simulators

Use this reference when the external integration is a database or persistence layer rather than a device or network service.

## When a Database Simulator Is Needed

Database-backed CLIs need simulator design when behavior depends on:
- persisted state across commands
- query semantics
- relational constraints
- conflict handling
- transactional behavior
- read-after-write verification

Routine tests should not require a shared live database just to verify normal CLI behavior.

## Baseline Options

Choose the lowest-cost simulator that still preserves the important behavior:

- JSON-backed local store for simpler persistence and state verification
- SQLite-backed simulator with matching or near-matching schema when relational behavior, constraints, or query semantics matter

For a small CLI, a JSON store may be enough. For a richer data model, SQLite is often the correct baseline because it preserves real query and constraint behavior better than an in-memory map.

## What the Simulator Must Preserve

The database simulator should preserve:
- state across calls
- mutation and readback behavior
- identifiers and lookup semantics
- conflict or uniqueness behavior when relevant
- invalid state transitions when the real model rejects them

## Behavior Mutation Examples

Make it possible to inject or configure:
- missing rows
- duplicate keys or uniqueness conflicts
- invalid references
- lock-like contention or write denial
- stale reads when the real system can present them
- partial-apply failures when multi-step mutations can fail mid-flight

## Schema Guidance

If you use SQLite:
- keep the schema intentionally close to the real model
- preserve constraints that matter to CLI behavior
- avoid silently dropping important integrity rules

If you use a JSON store:
- model identifiers and relationships explicitly
- preserve persistence across calls and test phases
- avoid per-call reconstruction that hides sequencing bugs

## Review Standard

A database simulator is insufficient if:
- it only returns canned rows with no stored state
- it cannot reproduce important conflicts or invalid states
- tests still need a shared live database for routine CLI verification
