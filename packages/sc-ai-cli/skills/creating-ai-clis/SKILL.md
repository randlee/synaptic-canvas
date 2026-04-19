---
name: creating-ai-clis
version: 0.10.0
description: Create or harden CLIs intended primarily for AI or system consumption and secondarily for humans. Use when designing or implementing a JSON-first CLI with an MCP-ready contract seam, where every command supports machine output, errors are typed and actionable, mutating commands are auditable via corresponding read commands, and external integrations need simulator-backed testing. Do not use for human-first shell utilities, one-off scripts, or text-only CLIs.
---

# Creating AI CLIs

Use this skill when the machine contract is the primary product and the human CLI is a secondary interface. The CLI should be directly usable by agents and should be structured so a future MCP wrapper can reuse the same request and response models without reshaping business JSON. This package does not currently ship MCP templates.

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

Keep these top-level rules in mind:
- the machine contract is primary: `--json`, stable envelopes, typed actionable errors, and stable codes are mandatory
- the CLI contract should expose a request/response seam that a future MCP wrapper can reuse with no business-payload reshaping
- mutating commands need readback and external integrations need simulator-backed tests

The detailed contract lives in the reference files below.

## References

- `references/core-contract.md` — language-agnostic contract for JSON-first CLI design
- `references/error-contracts.md` — typed, actionable error modeling for AI-facing CLIs
- `references/mcp-compatibility.md` — how to keep CLI and MCP behavior identical without JSON reshaping
- `references/simulation-and-auditability.md` — simulator, auditability, and mutation/read-pair guidance
- `references/template-generation.md` — `sc-compose`/MiniJinja template patterns for repeatable CLI scaffolding
- `references/example-repos.md` — extracted patterns and non-patterns from the example CLIs
- `references/dotnet.md` — `.NET` implementation patterns
- `references/dotnet-examples.md` — `.NET` command, adapter, and JSON contract examples
- `references/rust.md` — Rust implementation patterns
- `references/rust-examples.md` — Rust command, trait, and JSON contract examples
- `references/go.md` — Go implementation patterns
- `references/go-examples.md` — Go command, interface, and JSON contract examples

Read `core-contract.md` first. Then read `error-contracts.md`, `mcp-compatibility.md`, `simulation-and-auditability.md`, `template-generation.md`, and `example-repos.md`. Load only the language reference and language example file that match the implementation language. If the work requires deep simulator design, load the separate `designing-cli-simulators` skill as well.

## Agent Delegation

This skill operates directly in the main session on CLI design and implementation artifacts. It does not delegate to background agents or sub-agents.

## Workflow

When creating or hardening an AI-first CLI:

1. Define the command surface as machine operations first, not human prose flows.
2. Establish stable request and response JSON models before formatting human output.
3. Define typed success and error results before formatting human output. Error outputs should help the caller correct the problem, not just report failure.
4. Ensure every command supports `--json`, and define shared request/response models so a future MCP wrapper can reuse the same business contract.
5. For each mutating command, define the corresponding `get`/`show`/`list`/`status` command needed to verify resulting state.
6. If the CLI talks to an external system, require a stateful simulator below the CLI and protocol layer so the same business logic runs against real and simulated backends. For specialist simulator design, use `designing-cli-simulators`.
7. Pick the language-specific reference and example file only after the contract is fixed.
8. When the CLI shape repeats across projects or commands, capture the boilerplate as `sc-compose`-rendered `.j2` templates with normalized YAML frontmatter.
9. If an MCP wrapper exists or is being built in the same project, test the same JSON fixtures against the CLI path and the MCP path with no contract reshaping between them. If no MCP wrapper exists yet, keep the CLI contracts and tests ready for that parity work.
10. Before declaring the CLI complete, verify that:
   - all commands expose machine output through `--json`
   - the CLI is structured so a future MCP wrapper can reuse the same JSON schemas
   - error results are typed, stable, corrective for callers, and carry stable codes
   - mutating commands are auditable through corresponding read commands
   - external integrations can be exercised through a stateful simulator with controlled alternate behaviors
   - human output is a presentation layer, not the only tested interface

## Output Expectations

When using this skill, report:
- the command and JSON contract that was chosen
- how the CLI contract is kept MCP-ready without requiring separate MCP templates in this package
- how success and error results are modeled
- what stable error or diagnostic codes exist
- how mutating commands are audited
- how simulation-backed testing is provided
- any remaining language-specific decisions
