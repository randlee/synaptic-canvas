# Error Contracts

For AI-first CLIs, error handling is part of the interface contract, not an afterthought.

## Goals

Error outputs should:
- be machine-readable
- identify the failure category clearly
- expose enough structured detail for automation
- steer the caller toward correction when correction is possible

Avoid error handling that reduces everything to:
- opaque strings
- stack traces as the main contract
- generic exit-code-only failure

## Preferred Shape

Prefer a typed success/error contract or discriminated-union style result.

Examples:

```json
{
  "success": false,
  "error": {
    "kind": "validation",
    "code": "CONFIG.MISSING_FIELD",
    "message": "Required field 'endpoint' is missing",
    "details": {
      "field": "endpoint"
    },
    "suggested_action": "Provide --endpoint or set endpoint in the config file"
  }
}
```

```json
{
  "type": "error",
  "error": {
    "kind": "not_found",
    "code": "DEVICE.NOT_FOUND",
    "message": "Device 'dev-42' was not found",
    "details": {
      "device_id": "dev-42"
    },
    "suggested_action": "Run list-devices to discover valid device ids"
  }
}
```

Exact field names may vary by language or existing conventions. The important properties are:
- explicit success vs error discrimination
- stable error codes or categories
- structured details
- actionable guidance when a caller can recover

For stronger contracts, prefer exposing both:
- a stable machine code such as `ERR_VAL_MISSING_REQUIRED` or `ATM_TEAM_NOT_FOUND`
- a broader kind/category such as `validation` or `not_found`

## Actionable Error Guidance

Good CLI errors help the caller answer:
- what failed
- why it failed
- whether the input, state, or dependency is wrong
- what to do next

Prefer messages like:
- "Profile 'x' does not exist. Run list-profiles to see valid names."
- "Port 70000 is invalid. Valid range is 1-65535."
- "Target is offline. Retry after reconnecting the device or use --offline-simulator for tests."

Avoid messages like:
- "invalid request"
- "operation failed"
- "something went wrong"

Also avoid:
- exposing only prose on stderr when `--json` was explicitly requested
- hiding partial failure in warnings/logs while returning a nominal success payload

## Recommended Error Categories

Keep categories stable enough for automation:
- validation
- not_found
- conflict or invalid_state
- dependency or transport
- permission or safety
- timeout
- internal

## CLI and MCP Consistency

The CLI and MCP wrapper should return the same business error shape. The MCP transport may add wrapper metadata, but the underlying error contract should remain the same.

If the CLI emits:
- `code: CONFIG.MISSING_FIELD`
- `kind: validation`
- `suggested_action: "Provide --endpoint ..."`

the MCP wrapper should not replace that with:
- a different code
- prose-only text
- flattened or renamed payloads

The CLI should also avoid:
- switching to a different error shape for different sub-modes of the same command
- collapsing partial success into silent omission

## Review Questions

When reviewing an existing CLI, check:
- Are errors represented as typed results or only as strings?
- Can an automated caller branch on error kind or code?
- Does the message steer the caller toward correction?
- Are validation, state, and dependency failures distinguishable?
- Does the same error contract appear in both CLI and MCP paths?
- Is the same error schema used for top-level failures, not only nested library results?

## Warning Signs

- one catch-all error string for many failure modes
- no stable code or category
- only human prose on stderr with no structured JSON in `--json` mode
- stack traces leaking into the public machine contract
- MCP wrappers inventing a separate error schema
