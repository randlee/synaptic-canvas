# sc-ai-cli

AI-first CLI design toolkit for Synaptic Canvas. Provides skills for creating, reviewing, and simulator-hardening CLIs whose primary contract is machine consumption rather than human prose.

## Skills

### creating-ai-clis
Design or harden JSON-first, MCP-ready CLIs with shared request and response models, typed actionable errors, auditable mutating commands, and simulator-backed testing expectations.

### reviewing-ai-clis
Critically review existing CLIs, MCP wrappers, or CLI plans against the AI-first contract: JSON completeness, error quality, MCP parity, auditability, and simulator realism.

### designing-cli-simulators
Design stateful simulators for device, service, or database integrations so the same business logic can run against live and simulated backends without contract drift.

## What This Package Covers

- universal `--json` support as the machine contract
- MCP compatibility with no business-payload reshaping
- typed or discriminated error contracts with stable codes
- readback symmetry for mutating commands
- realistic simulator expectations for external integrations
- `sc-compose` and MiniJinja guidance for repeatable CLI scaffolding

## Requirements

No required runtime tools are needed to install the skills themselves.

Optional supporting tools referenced by the skills:
- `sc-compose` for `.j2`-based scaffolding workflows
- language-specific CLI tooling such as `.NET`, Rust, or Go toolchains

## Storage

This package installs into `.claude/` only. No persistent runtime state is created by the package itself.

## Reference Files

Installed alongside the skills:

| File | Purpose |
|------|---------|
| `creating-ai-clis/references/core-contract.md` | Language-agnostic contract for AI-facing CLI design |
| `creating-ai-clis/references/error-contracts.md` | Typed, actionable error guidance |
| `creating-ai-clis/references/template-generation.md` | `sc-compose`/MiniJinja scaffolding guidance |
| `creating-ai-clis/references/example-repos.md` | Real-world patterns and non-patterns from example repos |
| `designing-cli-simulators/references/simulator-examples.md` | Concrete stateful simulator starting patterns |
| `reviewing-ai-clis/references/review-checklist.md` | Contract-focused review checklist |
