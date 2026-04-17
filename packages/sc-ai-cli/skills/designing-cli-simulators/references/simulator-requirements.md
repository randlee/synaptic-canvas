# Simulator Requirements

Design the simulator as part of the product contract, not as disposable test scaffolding.

## Baseline Requirements

Every simulator for an AI-facing CLI should satisfy these properties:

- fidelity: match real behavior as closely as reasonable for the test purpose
- statefulness: preserve state across calls and command sequences
- behavior mutation: support configured failures, edge conditions, and alternate backend behavior
- routine-test completeness: enable routine unit and integration tests without live infrastructure
- adapter compatibility: run behind the same interface or trait used by the live backend

## What to Model Explicitly

Make these decisions explicit:
- what state exists
- what operations can mutate it
- what read paths expose it for verification
- what invalid states or transitions can occur
- what timing, ordering, retry, or contention issues matter

## Minimum Negative-Path Coverage

The simulator should support at least:
- validation failures caused by backend rules
- not-found scenarios
- unavailable or timeout scenarios when the real system can produce them
- conflicts or invalid state transitions
- partial success when the real integration can partially apply work

## Anti-Patterns

Do not rely on:
- stateless fakes for stateful systems
- top-level mocks that skip the real operation flow
- simulator-only command paths
- hidden magic state that tests cannot inspect
- manually patched test doubles for each failure instead of reusable mutation controls; use the simulator-control patterns in `adapter-boundaries.md` instead
