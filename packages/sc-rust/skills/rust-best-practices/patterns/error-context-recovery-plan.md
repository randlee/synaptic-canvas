# Implementation Plan: Error Context + Recovery Pattern

## Overview

Standardize error handling so every error carries structured context: what happened, why, how to fix it, and where to learn more. This is the highest-ROI pattern because bad errors cascade — across agent boundaries, into user-facing output, and into debugging spirals.

## Design Goals

1. Every error message tells a **story**, not just a symptom
2. Errors are **machine-parseable** (JSON) and **human-readable** (Display)
3. Recovery steps are **actionable** — not "check your configuration" but "run `X` or set `Y`"
4. Error codes are **stable** and **documented** for scripting consumers

---

## Phase 1: Core Library

### Rust Implementation

```rust
use thiserror::Error;
use serde::{Serialize, Deserialize};

/// Stable error codes for scripting consumers.
/// Once published, codes must not be removed or renamed.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    MissingApiKey,
    ConfigInvalid,
    ResourceNotFound,
    PermissionDenied,
    NetworkUnavailable,
    TimeoutExceeded,
    InternalError,
    // Extend as needed — additions are non-breaking
}

/// A recoverable error with structured context.
///
/// # Usage
/// ```rust
/// RecoverableError::new(ErrorCode::MissingApiKey, "Semantic search unavailable")
///     .cause("OPENAI_API_KEY environment variable is not set")
///     .recovery("Set OPENAI_API_KEY environment variable")
///     .recovery("Or run: cm config set openaiApiKey <key>")
///     .recovery("Or use --no-semantic flag for keyword-only search")
///     .docs("https://docs.example.com/semantic-search")
/// ```
#[derive(Debug, Serialize, Deserialize)]
pub struct RecoverableError {
    pub message: String,
    pub code: ErrorCode,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cause: Option<String>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub recovery: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub docs: Option<String>,
    #[serde(skip)]
    pub source: Option<Box<dyn std::error::Error + Send + Sync>>,
}

impl RecoverableError {
    pub fn new(code: ErrorCode, message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            code,
            cause: None,
            recovery: Vec::new(),
            docs: None,
            source: None,
        }
    }

    pub fn cause(mut self, cause: impl Into<String>) -> Self {
        self.cause = Some(cause.into());
        self
    }

    pub fn recovery(mut self, step: impl Into<String>) -> Self {
        self.recovery.push(step.into());
        self
    }

    pub fn docs(mut self, url: impl Into<String>) -> Self {
        self.docs = Some(url.into());
        self
    }

    pub fn source(mut self, err: impl std::error::Error + Send + Sync + 'static) -> Self {
        self.source = Some(Box::new(err));
        self
    }

    /// JSON representation for machine consumers
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "success": false,
            "error": self.message,
            "code": self.code,
            "cause": self.cause,
            "recovery": self.recovery,
            "docs": self.docs,
        })
    }
}

impl std::fmt::Display for RecoverableError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)?;
        if let Some(cause) = &self.cause {
            write!(f, "\n  Cause: {cause}")?;
        }
        if !self.recovery.is_empty() {
            write!(f, "\n  Recovery:")?;
            for step in &self.recovery {
                write!(f, "\n    → {step}")?;
            }
        }
        if let Some(docs) = &self.docs {
            write!(f, "\n  Docs: {docs}")?;
        }
        Ok(())
    }
}

impl std::error::Error for RecoverableError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        self.source.as_ref().map(|e| e.as_ref() as &(dyn std::error::Error + 'static))
    }
}
```

### Key Design Decisions

- **Builder pattern** for construction — each field is optional, added fluently
- **`thiserror` compatible** — can be used as a variant in a `#[derive(Error)]` enum
- **`serde` for JSON** — `to_json()` produces the exact format from the spec
- **`source` is `#[serde(skip)]`** — the error chain is for programmatic traversal, not serialization
- **`ErrorCode` is `#[serde(rename_all = "SCREAMING_SNAKE_CASE")]`** — stable string representation

---

## Phase 2: Design Review Enforcement

### Error Inventory Requirement

Every plan document that introduces a new command, API endpoint, or agent interaction must include an **error inventory** section:

```markdown
## Error Inventory

| Failure Mode | Code | Cause | Recovery Steps |
|---|---|---|---|
| API key not set | MISSING_API_KEY | Env var unset | Set var, run config, use --no-semantic |
| Config file malformed | CONFIG_INVALID | TOML parse error | Show parse error location, link to schema |
| Agent unreachable | NETWORK_UNAVAILABLE | Daemon not running | Start daemon, check port, check logs |
```

### Agent Behavior: `design-review`

When reviewing a plan document, the design-review agent checks:

1. **Does the plan define new error-producing operations?** Look for keywords: "fails when," "error if," "invalid," "not found," "unavailable," "timeout."
2. **Does it include an error inventory?** If not, request one before approving.
3. **Does each inventory entry have recovery steps?** Flag entries with empty recovery columns.
4. **Are error codes reusing existing codes or introducing new ones?** New codes should be documented.

---

## Phase 3: Code Review Enforcement

### `/error-audit` Command

A Claude Code command that scans source files and flags violations:

**Rules:**

| ID | Rule | Severity |
|---|---|---|
| E001 | `anyhow::anyhow!()` or `bail!()` without structured context | Warning |
| E002 | `.map_err(\|e\| ...)` that doesn't wrap in `RecoverableError` | Warning |
| E003 | `eprintln!("Error: ...")` instead of structured error output | Error |
| E004 | `process::exit(N)` without documented exit code | Error |
| E005 | `unwrap()` or `expect()` outside of tests | Warning |
| E006 | Error message is a bare string with no cause/recovery | Info |
| E007 | `panic!()` in library code (non-test) | Error |

**Output format:**

```
[E003] src/commands/search.rs:47
  Found: eprintln!("Error: search failed")
  Suggest: Use RecoverableError::new(ErrorCode::InternalError, "Search failed")
           .cause("...")
           .recovery("...")

[E001] src/agent.rs:112
  Found: anyhow::anyhow!("Agent {} not found", id)
  Suggest: Wrap in RecoverableError with code RESOURCE_NOT_FOUND
           and recovery steps for the caller
```

### sc-hooks Integration

Register as a pre-commit hook in `sc-hooks`:

```toml
[hooks.error-audit]
event = "pre-commit"
binary = "error-audit"
args = ["--severity", "error"]  # Only block on Error severity
```

---

## Phase 4: CI Validation

### Schema Enforcement

A CI step that exercises error paths and validates JSON output:

```rust
#[cfg(test)]
mod error_schema_tests {
    use super::*;
    use serde_json::Value;

    /// Every RecoverableError must produce valid JSON with required fields
    fn validate_error_json(err: &RecoverableError) {
        let json = err.to_json();
        assert_eq!(json["success"], false);
        assert!(json["error"].is_string(), "error field must be a string");
        assert!(json["code"].is_string(), "code field must be a string");
        // recovery may be empty but must be an array
        assert!(json["recovery"].is_array(), "recovery must be an array");
    }

    #[test]
    fn test_all_error_codes_have_display() {
        // Ensure every ErrorCode variant round-trips through serde
        let codes = vec![
            ErrorCode::MissingApiKey,
            ErrorCode::ConfigInvalid,
            ErrorCode::ResourceNotFound,
            // ... all variants
        ];
        for code in codes {
            let json = serde_json::to_string(&code).unwrap();
            let round_trip: ErrorCode = serde_json::from_str(&json).unwrap();
            assert_eq!(code, round_trip);
        }
    }
}
```

### Error Path Smoke Tests

For CLI tools, a CI script that runs commands with intentionally bad inputs and validates error output:

```bash
#!/bin/bash
# Verify error JSON schema for common failure modes

# Missing API key
unset OPENAI_API_KEY
output=$(my-tool search --json "test query" 2>&1)
echo "$output" | jq -e '.success == false' || exit 1
echo "$output" | jq -e '.code != null' || exit 1
echo "$output" | jq -e '.recovery | length > 0' || exit 1
```

---

## Acceptance Checklist

An error-contract implementation is not complete unless:

- all important user-visible error paths include recovery guidance
- JSON error output uses a consistent structure
- stable error codes are documented for scripting consumers
- docs links are included where they materially help recovery
- command-line tools use meaningful, documented exit behavior

---

## Migration Strategy for Existing Code

### Step 1: Introduce the library crate (non-breaking)
Add `recoverable-error` (or equivalent) as a workspace dependency. No existing code changes.

### Step 2: Convert leaf commands first
Start with the most user-facing commands — the ones that produce the most support questions. Wrap their error returns in `RecoverableError`.

### Step 3: Convert shared utilities
Functions in `src/utils.rs` or equivalent that are called by multiple commands. Add context at each call site using `.map_err()`.

### Step 4: Enable the `/error-audit` command
Initially in advisory mode (warnings only). Fix flagged issues over 2-3 sprints. Then promote to error severity and add to CI.

### Step 5: Add error documentation
Generate a table of all `ErrorCode` variants with their meanings and common recovery steps. Publish alongside the tool's docs.

---

## Exit Code Convention

| Range | Meaning |
|---|---|
| 0 | Success |
| 1 | General error (catchall) |
| 2 | Usage / argument error |
| 10-19 | Configuration errors |
| 20-29 | Network / connectivity errors |
| 30-39 | Resource not found errors |
| 40-49 | Permission / authentication errors |
| 50-59 | Internal / unexpected errors |

Map `ErrorCode` variants to exit codes deterministically so scripts can branch on them.

---

## Cross-Language / TypeScript Addendum

### Problem

Error messages don't tell users how to fix issues:

- "Semantic search unavailable" — but why? How to enable?
- "Bullet not found" — but where to look?
- "Config invalid" — but what's wrong?

### TypeScript Interface

```typescript
interface RecoverableError {
  message: string;
  code: ErrorCode;
  cause?: string;        // What triggered this
  recovery: string[];    // Steps to fix
  docs?: string;         // Link to documentation
}
```

### JSON Error Format

```json
{
  "success": false,
  "error": "Semantic search unavailable",
  "cause": "OPENAI_API_KEY not set",
  "recovery": [
    "Set OPENAI_API_KEY environment variable",
    "Or run: cm config set openaiApiKey <key>",
    "Or use --no-semantic flag for keyword-only"
  ],
  "code": "MISSING_API_KEY",
  "docs": "https://docs.example.com/semantic-search"
}
```

### Acceptance Criteria

- [ ] All error messages include recovery steps
- [ ] JSON errors have consistent structure
- [ ] Documentation links where applicable
- [ ] Exit codes are meaningful and documented
