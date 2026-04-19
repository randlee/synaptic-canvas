# Example Repos

These repositories are pattern sources, not blanket gold standards. Some contain strong ideas worth extracting. Some also contain behavior that this skill should improve on by default.

## High-Value Positive Patterns

### `atm-core` (Rust)

Strong patterns:
- broad `--json` coverage across operational commands
- domain-owned result types serialized directly for machine output
- stable error-code registry with public string codes
- error values carrying recovery guidance
- operational readback and health commands that make state inspection first-class

Extract:
- typed domain errors with stable codes and recovery guidance
- human and JSON output both backed by the same domain result
- machine-readable findings with severity, code, message, and remediation

Do not copy blindly:
- top-level fatal failures still degrade to plain stderr text instead of a structured JSON error envelope
- verify that all commands and all exit paths actually honor `--json`, not just the happy path
- some mutation families are not fully mirrored in retained audit/query surfaces
- branching command results should be tagged unions, not two unrelated JSON shapes selected by CLI code paths

### `sc-compose` (Rust)

Strong patterns:
- all core subcommands expose `--json`
- JSON output uses a versioned envelope with `schema_version`, `payload`, and `diagnostics`
- diagnostics have stable codes, severities, and optional locations
- the library owns the diagnostic schema, and the CLI mostly presents it
- structured recovery hints exist in the library error model

Extract:
- versioned JSON envelopes
- stable diagnostic-code registry
- separation of payload from diagnostics
- operation logic below the CLI in a reusable library

Do not copy blindly:
- top-level failures still collapse to plain text stderr in some paths instead of reusing the structured envelope
- some JSON commands reshape or duplicate diagnostics rather than exposing one canonical library model

### `schook` (Rust)

Strong patterns:
- explicit statement that the public contract is JSON, environment variables, and exit codes
- plugin/host boundary uses a documented JSON result envelope
- result actions are modeled as a discriminated enum (`proceed`, `block`, `error`)
- CLI error taxonomy is typed and mapped to stable exit codes

Extract:
- treat JSON protocol and exit codes as the release contract
- use discriminated action/result models for plugin or automation boundaries
- define CLI error families and exit-code mapping explicitly

Do not copy blindly:
- the top-level CLI commands are not uniformly JSON-first enough to use as the final target standard
- provider-shaped fields in the public contract should be pushed behind neutral/namespaced extensions if the goal is reusable CLI/MCP serialization

## Mixed Examples

### `claude-history` (Go)

Good patterns:
- several commands support `--format json`
- output writing is centralized, which helps consistency
- tests cover many output and error scenarios

Weak patterns relative to this skill’s target:
- many error paths still use plain `fmt.Errorf(...)` and stderr messaging without stable machine-readable codes
- no consistent typed error envelope across commands
- “not found” or “no entries found” outcomes are often human-readable only
- partial reads and skipped malformed records are not surfaced as machine-readable partial-result state
- command JSON shapes vary by command, and some machine payloads include display-oriented sentinel values

Extraction guidance:
- keep the centralized output layer idea
- improve on it by making error contracts as structured as success contracts

### `roslyn-diff` (.NET)

Good patterns:
- explicit machine-oriented JSON option on key commands
- output routing is centralized in an output orchestrator
- validation catches many bad argument combinations early

Weak patterns relative to this skill’s target:
- JSON support is command-specific rather than a universal machine contract pattern
- errors are largely presentation-first (`ValidationResult.Error`, colored console text, stderr warnings)
- no stable typed error schema shared across the CLI surface
- multi-file modes can hide per-file failures outside the machine payload
- JSON shape drifts across single-file versus multi-file modes

Extraction guidance:
- keep centralized output orchestration
- do not let console presentation become the primary error contract

## Cautionary Example

### `roslyn-graph` (.NET)

This repo is useful mainly as a reminder of what an AI-first CLI should improve:
- single-command CLI with no first-class JSON output mode
- success path writes files and prose status messages
- failure path is plain stderr text and optional stack trace
- no explicit MCP-ready contract or shared request/response models

Extraction guidance:
- do not treat a human-oriented batch CLI as sufficient for AI-first tool use

## Skill Standard

The skill should aim higher than the weakest example and at least as strong as the best patterns above:
- `atm-core` for domain errors, codes, and operational auditability
- `sc-compose` for versioned envelopes and diagnostic schemas
- `schook` for explicit contract thinking around JSON and exit codes

The default generated guidance should be stricter than:
- `claude-history` on error contract structure
- `roslyn-diff` on universal machine-interface consistency
- `roslyn-graph` on JSON-first design in general
- `atm-core` on failure-path JSON and storage-model separation at the CLI surface
- `schook` on uniform JSON command coverage and provider-neutral contract shape

Specific things the generated guidance should prohibit by default:
- silent partial success where skipped inputs are only visible on stderr
- changing JSON envelope shape by mode
- honoring `--json` only on success paths
- display-only sentinel values in machine payloads
