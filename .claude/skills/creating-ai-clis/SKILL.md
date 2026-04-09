---
name: creating-ai-clis
version: 0.1.0
description: Create or harden CLIs intended primarily for AI or system consumption and secondarily for humans. Use when designing or implementing a JSON-first, MCP-ready CLI where every command supports machine output, errors are typed and actionable, mutating commands are auditable via corresponding read commands, and external integrations need simulator-backed testing. Do not use for human-first shell utilities, one-off scripts, or text-only CLIs.
---

# Creating AI CLIs

Use this skill when the machine contract is the primary product and the human CLI is a secondary interface. The CLI should be directly usable by agents and should wrap into MCP without reshaping request or response JSON.

## Scope

Use this skill for:
- JSON-first CLIs used by agents, automation, or test harnesses
- CLIs that should map cleanly to MCP tools
- CLIs that change or observe system state and must be auditable
- CLIs that integrate with external systems and need simulation-backed tests

Do not use this skill for:
- human-first UNIX tools that primarily emit prose, tables, or shell-oriented text
- ad hoc scripts with unstable output formats
- interactive-only CLIs that depend on prompts or TTY behavior

## Core Rules

- Every command must support `--json`.
- Machine-readable JSON is the source of truth; human-readable output is secondary.
- MCP wrappers must reuse the same request and response JSON models as the CLI.
- Wrapping the CLI with MCP does not require shelling out through stdout, but it must preserve the same serialization contract.
- Error results must be typed, machine-readable, and actionable for callers. Prefer discriminated-union or result-style modeling over opaque strings.
- Every mutating command must have a corresponding read command that can verify resulting state.
- External integrations should have a full simulator at the lowest practical boundary so tests can run without real hardware or services.

## References

- `references/core-contract.md` — language-agnostic contract for JSON-first CLI design
- `references/error-contracts.md` — typed, actionable error modeling for AI-facing CLIs
- `references/mcp-compatibility.md` — how to keep CLI and MCP behavior identical without JSON reshaping
- `references/simulation-and-auditability.md` — simulator, auditability, and mutation/read-pair guidance
- `references/dotnet.md` — `.NET` implementation patterns
- `references/rust.md` — Rust implementation patterns
- `references/go.md` — Go implementation patterns

Read `core-contract.md` first. Then read `error-contracts.md`, `mcp-compatibility.md`, and `simulation-and-auditability.md`. Load only the language reference that matches the implementation language.

## Agent Delegation

This skill operates directly on CLI design and implementation artifacts. It does not delegate to background agents or sub-agents.

## Workflow

When creating or hardening an AI-first CLI:

1. Define the command surface as machine operations first, not human prose flows.
2. Establish stable request and response JSON models before formatting human output.
3. Define typed success and error results before formatting human output. Error outputs should help the caller correct the problem, not just report failure.
4. Ensure every command supports `--json`, and use shared request/response models for any MCP wrapper.
5. For each mutating command, define the corresponding `get`/`show`/`list`/`status` command needed to verify resulting state.
6. If the CLI talks to an external system, place a simulator below the CLI and protocol layer so the same business logic runs against real and simulated backends.
7. Pick the language-specific reference only after the contract is fixed.
8. Test the same JSON fixtures against the CLI path and the MCP path, with no contract reshaping between them.
9. Before declaring the CLI complete, verify that:
   - all commands expose machine output through `--json`
   - the CLI and MCP wrapper use the same JSON schemas
   - error results are typed, stable, and corrective for callers
   - mutating commands are auditable through corresponding read commands
   - external integrations can be exercised through a simulator
   - human output is a presentation layer, not the only tested interface

## Output Expectations

When using this skill, report:
- the command and JSON contract that was chosen
- how CLI and MCP compatibility is enforced
- how success and error results are modeled
- how mutating commands are audited
- how simulation-backed testing is provided
- any remaining language-specific decisions
