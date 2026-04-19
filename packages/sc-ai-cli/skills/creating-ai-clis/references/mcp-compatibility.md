# MCP Compatibility

The CLI should be architected so a future MCP wrapper can reuse the same request and response models with no JSON reshaping. This package does not currently ship MCP templates; it defines the contract seam those templates or wrappers should use later.

## What "MCP-ready" Means Here

For this skill, "MCP-ready" means:
- the CLI command surface maps cleanly to tool-like operations
- request and response payloads are JSON-serializable without transport-specific rewriting
- the same fixtures can be used to test CLI and MCP paths when both surfaces exist

It does not require:
- the MCP server to shell out to the CLI binary
- stdout text to be parsed by the MCP layer

The important constraint is contract identity, not process identity.

## Required Boundary

Separate these concerns:
- request parsing
- operation execution
- response serialization
- human formatting

The MCP wrapper and the CLI should share the same operation layer and the same request/response models.

Recommended architecture:

```text
CLI parser -> request model -> operation layer -> response model -> JSON serializer
MCP tool   -> request model -> operation layer -> response model -> JSON serializer
```

## No-Reshaping Rule

The wrapper may:
- call the same underlying operation directly
- serialize with the same JSON library and model types
- add transport metadata outside the business payload if required by MCP infrastructure

The wrapper should not:
- rename fields
- collapse or expand nested structures
- convert typed payloads into prose summaries
- return a different success/error schema than the CLI uses in `--json` mode

## Test Strategy

When both surfaces exist, use shared fixtures for both paths:
- input fixture -> CLI command -> JSON result
- same input fixture -> MCP method/tool -> JSON result

Assert:
- same success/error shape
- same fields and field names
- same enum/string values
- same omitted/null behavior when relevant

Minor transport differences like trailing newlines on stdout are acceptable. Business payload differences are not.

If the project does not yet have an MCP wrapper:
- keep request and response models outside the CLI entrypoint
- keep human formatting isolated from business payload construction
- keep CLI tests fixture-oriented so MCP parity can be added without redesigning the contract

## Good Signs

- the request and response types live outside the CLI entrypoint
- the MCP layer is thin
- human formatting is isolated
- tests compare JSON payloads rather than prose output

## Warning Signs

- the CLI is built around printing text first and adding JSON later
- the MCP wrapper has its own DTOs
- JSON mode is assembled from formatted strings
- the only way to reuse behavior is to parse stdout
