# Simulation and Auditability

AI-first CLIs should be verifiable without real infrastructure and should make state changes observable after the fact.

## Simulator Requirement

If the CLI integrates with external systems, build a simulator at the lowest practical boundary:
- below the CLI command layer
- below the protocol adapter when possible
- close to the real transport or device abstraction

The goal is to run realistic end-to-end tests without:
- external hardware
- shared environments
- live services
- fragile network dependencies

Prefer one simulator that exercises the real business flow over many shallow mocks.

This skill requires the simulator contract to exist during CLI design. If the simulator itself needs detailed design work, use the separate `designing-cli-simulators` skill.

## Required Simulator Properties

For an AI-first CLI, the simulator should meet these baseline requirements:

- fidelity: match real behavior as closely as reasonable for the test purpose
- state: preserve state across calls so read-after-write and multi-step workflows are testable
- behavior mutation: allow controlled injection of failures, edge cases, alternate timing, and unusual backend responses
- test completeness: make routine unit and integration tests pass without requiring live infrastructure
- swapability: sit behind the same adapter boundary used by the real integration so the same business logic runs in both modes

Stateless per-call fakes are not enough when the real system has persistent state, sequencing constraints, or observable side effects.

## What the Simulator Should Cover

The simulator should support:
- expected success flows
- not-found and invalid-state scenarios
- retries/timeouts where relevant
- deterministic seeded test data
- observation of resulting state for verification
- partial-success or degraded-mode scenarios where the real backend can produce them
- configurable failure injection for negative-path tests

Starter templates in this package include a simple file-backed simulator control seam so tests can force read failures, write failures, or degraded status without branching the operation layer. Treat that as a baseline hook, not the full limit of simulator behavior.

## Mutation Auditability

Every mutating command must have a corresponding read command.

Examples:
- `set-config` -> `get-config`
- `apply-profile` -> `get-profile`
- `create-device` -> `get-device`
- `delete-job` -> `get-job` or `list-jobs`

The read command should make it possible to verify:
- what state exists now
- whether the mutation took effect
- whether the state matches the requested change

This does not require a separate audit log product for every CLI. It does require observable state verification.

## Mutation Response Guidance

Mutating commands should return enough JSON to support automation, such as:
- target identifier
- requested change
- applied change when it differs from requested input
- resulting status or summary
- warnings if partial application occurred

Do not make automation infer success from prose like "updated successfully".

## Adapter Boundary Guidance

Use a swappable adapter pattern when the CLI talks to devices, services, or databases:

- Rust: trait-based adapter boundary
- .NET: interface-based adapter boundary
- Go: interface-based adapter boundary

The CLI and operation layer should depend on the abstraction, not on the simulator or the live implementation directly. Avoid separate conditional code paths that make simulator mode behave differently from production mode.

## Database Simulator Guidance

Database-backed CLIs also need simulator-backed testing. In these cases, the simulator may be a local persistence implementation rather than a fake device or service.

Choose the lowest-fidelity option that still preserves the important behavior:

- JSON-backed local store for simpler persistence and state-verification scenarios
- SQLite-backed simulator with a matching or near-matching schema when relational behavior, constraints, or query semantics matter

The simulator should still preserve:
- persistent state across commands and tests
- realistic mutation and readback behavior
- failure injection such as conflicts, missing rows, lock-like conditions, or invalid-state transitions
- the same adapter contract used by the live database path

Do not treat a stateless repository mock as a sufficient database simulator when the CLI behavior depends on stored state or query behavior.

## Verification Pattern

For each state-changing operation:
1. execute the mutation in JSON mode
2. execute the corresponding read command in JSON mode
3. assert that the read result reflects the intended change
4. run the same verification through the simulator-backed path

## Warning Signs

- mutations with no readback path
- tests that only assert exit code
- tests that require live hardware or servers
- state changes visible only in logs or human-readable text
- simulator mode with separate business logic branches
- stateless fakes standing in for stateful systems
- no way to inject negative-path behavior without patching test code
