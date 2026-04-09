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

## What the Simulator Should Cover

The simulator should support:
- expected success flows
- not-found and invalid-state scenarios
- retries/timeouts where relevant
- deterministic seeded test data
- observation of resulting state for verification

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
