# Adapter Boundaries

The adapter boundary is what lets the CLI and MCP stack run the same business logic against both the real integration and the simulator.

## Baseline Pattern

Structure the system so:
- CLI and MCP handlers build typed requests
- an operation layer owns business rules
- the operation layer depends on an abstraction
- live and simulated backends both implement that abstraction

The adapter boundary should sit below command parsing and below human-readable formatting.

## Language Baselines

- Rust: trait
- .NET: interface
- Go: interface

The exact language mechanism matters less than the invariant: the simulator and live backend must be substitutable without changing business logic.

## What the Boundary Should Expose

The adapter contract should expose:
- typed requests and responses
- typed domain errors or stable error unions
- enough read methods to verify mutations
- cancellation or timeout inputs where the real integration supports them

Avoid boundaries that expose:
- raw CLI parsing types
- direct console writers
- provider-specific DTOs as the canonical contract
- simulator-only control methods mixed into the production interface

## Fault Injection

Do not pollute the production adapter interface with test-only switches.

Instead:
- configure the simulator through constructor state, test fixtures, or dedicated simulator controls
- keep those controls separate from the live backend contract
- ensure tests can inject failures without changing the operation layer
