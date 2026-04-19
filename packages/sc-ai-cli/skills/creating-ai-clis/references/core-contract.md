# Core Contract

This reference defines the language-agnostic contract for CLIs intended primarily for AI and automation.

## Design Priorities

1. Machine contract first
2. Stable JSON serialization
3. Deterministic read-after-write verification
4. MCP compatibility without payload reshaping
5. Human output as a secondary presentation concern

## Minimum Contract

Every command should have:
- a stable operation name
- a defined request model
- a defined response model
- `--json` output support
- deterministic exit behavior
- one stable envelope shape across command modes and failure paths

Strongly recommended for commands with structured input:
- JSON input via stdin, `--input`, or `--file`
- the same request schema used by the eventual MCP tool

## Output Modes

`--json` mode is normative:
- field names and structure must be stable
- output should be complete enough for automated callers
- avoid embedding important data only in prose strings
- avoid color, progress output, or interactivity in JSON mode
- do not change the top-level JSON shape just because the command runs in a different sub-mode
- do not silently drop skipped inputs, partial failures, or incomplete scans
- prefer provider-neutral field names in the canonical contract
- preserve forward-compatible extension data rather than dropping unknown machine fields by default

Human-readable mode may:
- format the same data for readability
- suppress machine-oriented detail that is already present in JSON mode

Human-readable mode must not:
- expose data that cannot be obtained through `--json`
- become the only validated behavior

## Error Contract

Prefer a structured JSON error shape in `--json` mode, for example:

```json
{
  "success": false,
  "error": {
    "code": "DEVICE.NOT_FOUND",
    "message": "Device abc was not found",
    "details": {
      "device_id": "abc"
    }
  }
}
```

Keep error categories stable enough for automation:
- validation/input errors
- not found/state mismatch errors
- transport/dependency errors
- permission/safety errors
- internal/unexpected errors

Top-level failure behavior should use the same machine contract family as success paths:
- if `--json` is set, failures should still be JSON
- partial success should be explicit, not inferred from stderr

## Command Modeling

Prefer commands that correspond to tool-like operations:
- `get`
- `list`
- `set`
- `apply`
- `create`
- `delete`
- `status`

Avoid machine contracts that depend on:
- interactive prompts
- parsing unstructured text
- positional-output conventions
- side effects that cannot be re-read or verified
- mode-specific envelope drift that forces callers to reshape per command path
- display-only sentinel values in machine payloads

## Completion Standard

Do not consider the CLI complete until:
- the machine contract is explicit
- `--json` mode is implemented on every command
- request and response models are reusable outside the CLI transport
- tests assert the machine contract directly
