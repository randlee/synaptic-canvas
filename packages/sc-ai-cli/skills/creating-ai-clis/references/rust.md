# Rust Patterns

Use this reference when implementing the CLI in Rust.

For concrete command and DTO shapes, also read `rust-examples.md`.

## Recommended Stack

- `clap` for command and option parsing
- `serde` and `serde_json` for request and response serialization
- `tokio` when async I/O or service integration is required

## Structure

Keep these layers separate:
- CLI argument parsing
- request/response structs
- operation layer
- backend adapter or transport layer
- human-readable formatting
- MCP wrapper layer

The same Rust types used for CLI JSON mode should also back the MCP wrapper.

## JSON Guidance

Prefer:
- typed request/response structs deriving `Serialize` and `Deserialize`
- one clear serialization policy shared across CLI and MCP
- machine-readable enums and stable field names

Avoid:
- building JSON manually with string concatenation
- separate DTOs for CLI and MCP unless a transport boundary truly requires it
- treating display formatting as the primary source of truth

## Simulation Guidance

For external systems:
- define traits at the adapter boundary
- provide simulator implementations of those traits
- keep simulator behavior close to the real protocol and state model

If the integration is async:
- run the same async operation layer against both real and simulated backends

For complex simulator design, especially stateful device or database simulation, use the separate `designing-cli-simulators` skill.

## Testing Guidance

Test at least:
- operation-layer behavior directly
- CLI `--json` responses, often with `assert_cmd` or equivalent
- read-after-write verification for mutations
- identical JSON contracts across CLI and MCP paths

## Example Notes

- `atm-core` is a strong example of domain-owned result types, stable error codes, and recovery-oriented error construction.
- `sc-compose` is a strong example of a versioned diagnostics envelope and library-owned diagnostic codes.
- `schook` is a strong example of treating JSON protocol and exit codes as the public contract, but its top-level CLI is not yet uniformly JSON-first enough to use as the final target standard.

For this skill’s target bar, prefer combining:
- `atm-core` style domain error taxonomy
- `sc-compose` style versioned output envelopes
- `schook` style explicit contract language
