# Go Patterns

Use this reference when implementing the CLI in Go.

## Recommended Stack

- a mature command framework such as `cobra` when subcommands and help structure matter
- `encoding/json` for request and response serialization

## Structure

Keep these layers separate:
- command parsing
- request/response structs
- operation layer
- backend adapter or transport layer
- human-readable rendering
- MCP wrapper layer

The same structs should define the JSON contract for both CLI and MCP paths whenever practical.

## JSON Guidance

Prefer:
- typed structs with clear JSON tags
- one serialization policy for both CLI and MCP
- explicit success/error payloads in JSON mode

Avoid:
- map-heavy payloads when stable structs are practical
- independent JSON shapes for the CLI and MCP wrapper
- tests that only inspect human-readable stdout

## Simulation Guidance

For external systems:
- keep interfaces at the adapter boundary
- provide simulator implementations that preserve realistic state and error behavior
- simulate as low in the stack as practical, not only at the top-level command layer

Depending on the integration, this may be implemented through:
- a simulated service client
- an in-memory backend
- an `httptest` server or lower-level fake transport

## Testing Guidance

Test at least:
- operation-layer behavior
- CLI `--json` payloads
- read-after-write verification for mutating commands
- shared-fixture equivalence across CLI and MCP entrypoints
