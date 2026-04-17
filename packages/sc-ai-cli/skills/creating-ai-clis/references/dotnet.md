# .NET Patterns

Use this reference when implementing the CLI in `.NET`.

For concrete command and DTO shapes, also read `dotnet-examples.md`.

## Recommended Stack

- `System.CommandLine` for command and option parsing
- `System.Text.Json` for request and response serialization
- source-generated serializers and AOT-compatible converters for published binaries

## Structure

Keep these layers separate:
- command binding and option parsing
- request/response DTOs
- operation/service layer
- human-readable formatting
- MCP wrapper layer

The request/response DTOs should be reusable by both:
- the CLI command handlers
- the MCP server/tool handlers

## JSON Guidance

Prefer:
- explicit DTOs over anonymous objects
- one `JsonSerializerOptions` policy shared by CLI and MCP layers
- source-generated `JsonSerializerContext` for stable AOT-friendly serialization

Avoid:
- different serializer settings between CLI and MCP wrappers
- reflection-heavy converter patterns that complicate AOT
- ad hoc `Dictionary<string, object>` payloads when typed DTOs are practical

## Simulation Guidance

For external systems:
- keep the simulator below command handlers
- simulate the transport or service boundary, not only the final method call
- use dependency injection so tests swap the real adapter for the simulator cleanly

Depending on the integration, this may be implemented through:
- a fake service client
- a fake repository or device adapter
- a custom `HttpMessageHandler` or equivalent low-level transport substitute

For complex simulator design, especially stateful device or database simulation, use the separate `designing-cli-simulators` skill.

## Testing Guidance

Test at least:
- command handler / operation layer behavior
- CLI `--json` output contract
- read-after-write auditability for mutating commands
- contract equivalence between CLI and MCP entrypoints

## Example Notes

- `roslyn-diff` shows the value of central output orchestration and explicit machine-output options on important commands.
- `roslyn-graph` is a useful caution: a human-oriented batch CLI with stderr/prose errors is not enough for AI-first consumption.

For this skill’s target bar, prefer:
- one reusable request/response model layer
- one reusable JSON serializer policy
- stable machine-readable errors for top-level failures, not just internal exceptions
