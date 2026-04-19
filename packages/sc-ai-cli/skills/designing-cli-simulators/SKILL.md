---
name: designing-cli-simulators
version: 0.10.0
description: Design stateful simulators for AI-facing CLIs that integrate with devices, networks, services, or databases. Use when a CLI needs realistic simulator-backed testing, configurable fault injection, persistent state, and a swappable adapter boundary so the same business logic runs against live and simulated backends. Do not use for shallow mocks, stateless test doubles, or CLIs with no external integration.
---

# Designing CLI Simulators

Use this skill when the CLI depends on an external system and the simulator needs to be designed as a real component rather than a one-off fake.

## Scope

Use this skill for:
- stateful simulators behind a CLI or MCP-facing tool
- serial, USB, TCP, HTTP, RPC, or protocol-backed device/service integrations
- database-backed CLIs that need local persistent simulation
- fault injection and edge-condition design for routine tests

Do not use this skill for:
- simple unit-test stubs with no persistent state
- pure formatting or argument-parsing tests
- CLIs that do not integrate with external systems or persistent stores

## Core Rules

Keep these top-level rules in mind:
- the simulator must preserve the same business contract as the real integration
- the simulator must maintain realistic state across calls and support behavior mutation for negative-path testing
- the live backend and simulator must sit behind the same adapter seam

The detailed guidance lives in the reference files below.

## References

- `references/simulator-requirements.md` — baseline simulator properties and validation targets
- `references/adapter-boundaries.md` — how to keep simulator and live backends interchangeable
- `references/device-simulators.md` — device, transport, and protocol simulation patterns
- `references/database-simulators.md` — JSON-backed and SQLite-backed database simulation patterns
- `references/simulator-examples.md` — concrete code patterns for simple stateful simulators

Read `simulator-requirements.md` first. Then load `adapter-boundaries.md`. Load `device-simulators.md` for serial, USB, network, or service-style integrations. Load `database-simulators.md` for persistence-backed integrations. Load `simulator-examples.md` when you need a concrete starting pattern.

## Agent Delegation

This skill operates directly in the main session on simulator design artifacts. It does not delegate to background agents or sub-agents.

## Workflow

When designing a CLI simulator:

1. Identify the real integration boundary and define the adapter seam first.
2. Decide what state the real system owns and make that state explicit in the simulator.
3. Define the behavior-mutation controls needed for error paths, timing issues, degraded states, and edge conditions.
4. Choose the persistence model that best matches the integration: in-memory state, JSON-backed persistence, SQLite-backed persistence, or protocol-state simulation.
5. Ensure the same operation layer runs against both live and simulated backends without conditional business logic branches.
6. Define how tests observe resulting state, including read-after-write verification and partial-success scenarios.
7. Verify that routine unit and integration tests can run without live infrastructure.
8. Before declaring the simulator design complete, verify that:
   - state persists across relevant calls
   - failure modes and alternate behaviors are injectable without patching test code
   - the simulator matches the real contract closely enough for routine verification
   - the CLI and MCP stack can exercise the same JSON fixtures against the simulator

## Output Expectations

When using this skill, report:
- the chosen adapter boundary
- the simulator state model
- the persistence model
- the supported behavior-mutation controls
- the fidelity goals and known limitations
- how routine tests avoid live infrastructure

Use `reviewing-ai-clis` as the validation counterpart when the simulator design needs a contract-level review against the CLI and MCP expectations.
