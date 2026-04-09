# Use Cases

## Design a new AI-facing CLI

Use `creating-ai-clis` when the CLI is meant to be consumed primarily by agents, automation, or MCP wrappers.

```
Design a CLI for managing device profiles with universal --json support and MCP parity.
```

The skill drives the design toward:
- stable request and response models
- typed actionable errors
- mutating/readback symmetry
- simulator-backed testability

## Review an existing CLI contract

Use `reviewing-ai-clis` when a CLI already exists and you need to know whether it is reliable for AI/system use.

```
Review this CLI and identify gaps in JSON coverage, error contracts, and MCP compatibility.
```

The skill reviews:
- success-path and failure-path JSON completeness
- stable error categories and codes
- auditability of state changes
- realism of simulator-backed testing

## Plan simulator architecture for a device CLI

Use `designing-cli-simulators` when a serial, USB, TCP, HTTP, or RPC integration needs a reusable simulator design.

```
Design the simulator boundary for a serial device CLI so tests can run without hardware.
```

The skill focuses on:
- adapter seam design
- persistent state model
- fault injection controls
- read-after-write verification paths

## Plan simulator architecture for a database-backed CLI

Use `designing-cli-simulators` when the external system is a persistent store rather than a physical device.

```
Design a simulator strategy for a database-backed CLI where routine tests should use JSON-store or SQLite-backed state instead of a shared live database.
```

The skill helps decide:
- JSON store vs. SQLite-backed simulator
- schema fidelity expectations
- conflict and invalid-state simulation
- test completeness without live infrastructure

## Create repeatable boilerplate for a CLI family

Use `creating-ai-clis` with the template-generation guidance when multiple CLIs or commands share the same shape.

```
Create a reusable sc-compose template strategy for a Go and Rust command pair with shared JSON error envelopes.
```

The skill will steer toward:
- `sc-compose`-rendered `.j2` templates
- normalized YAML frontmatter
- generated command/readback pairs
- shared contract and simulator seams
