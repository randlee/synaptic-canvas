# Implementation Plan: Typestate Pattern

## Overview

Encode state machine transitions into the type system so that invalid states are **unrepresentable** and illegal transitions are **compilation errors**. This eliminates runtime state checks and the bugs that come from forgetting them.

## Design Goals

1. Invalid state transitions fail at compile time, not runtime
2. Zero runtime cost — phantom types are erased after compilation
3. Each state exposes only the methods valid in that state
4. Transitions consume the old state and return the new state (move semantics)

---

## Core Pattern: Rust

```rust
use std::marker::PhantomData;

// --- State marker types (zero-sized) ---
pub struct Disconnected;
pub struct Connected;
pub struct Authenticated;

// --- The stateful resource ---
pub struct Connection<S> {
    addr: String,
    _state: PhantomData<S>,
}

// --- Transitions are consuming methods that return a new state ---

impl Connection<Disconnected> {
    pub fn new(addr: impl Into<String>) -> Self {
        Connection {
            addr: addr.into(),
            _state: PhantomData,
        }
    }

    /// Consumes Disconnected, returns Connected.
    /// Cannot be called on Connected or Authenticated.
    pub fn connect(self) -> Result<Connection<Connected>, ConnectionError> {
        // ... actual connection logic ...
        Ok(Connection {
            addr: self.addr,
            _state: PhantomData,
        })
    }
}

impl Connection<Connected> {
    pub fn authenticate(self, token: &str) -> Result<Connection<Authenticated>, AuthError> {
        // ... auth logic ...
        Ok(Connection {
            addr: self.addr,
            _state: PhantomData,
        })
    }

    pub fn disconnect(self) -> Connection<Disconnected> {
        Connection {
            addr: self.addr,
            _state: PhantomData,
        }
    }
}

impl Connection<Authenticated> {
    pub fn query(&self, sql: &str) -> QueryResult {
        // Only available when authenticated
        todo!()
    }

    pub fn disconnect(self) -> Connection<Disconnected> {
        Connection {
            addr: self.addr,
            _state: PhantomData,
        }
    }
}
```

**What the compiler prevents:**
```rust
let conn = Connection::new("localhost:5432");
// conn.query("SELECT 1");        // ❌ Won't compile — no query() on Disconnected
// conn.authenticate("token");    // ❌ Won't compile — no authenticate() on Disconnected

let conn = conn.connect()?;
// conn.query("SELECT 1");        // ❌ Won't compile — no query() on Connected

let conn = conn.authenticate("token")?;
conn.query("SELECT 1");           // ✅ Compiles — query() exists on Authenticated
```

---

## When to Use Typestates

### Strong Candidates (high value)

| Signal in plan doc | Example |
|---|---|
| "Must X before Y" | "Must authenticate before querying" |
| "Only valid when Z" | "Only valid when connection is open" |
| "After initialization" | "After initialization, the pipeline can accept frames" |
| Linear protocol steps | HTTP request lifecycle, TLS handshake |
| Resource acquisition/release | File handles, locks, database transactions |
| Build/deploy pipelines | Configure → Validate → Build → Deploy |

### Weak Candidates (avoid)

| Situation | Why |
|---|---|
| Many states with many transitions | Combinatorial explosion of `impl` blocks |
| States that need to be stored heterogeneously | Can't put `Connection<A>` and `Connection<B>` in the same `Vec` |
| Transitions determined at runtime | If you can't know the next state at compile time, typestates don't help |
| Hot loops where state changes frequently | Move semantics add boilerplate; benchmark first |

---

## Advanced: Fallible Transitions

Real-world transitions can fail. Return `Result` and give back the original state on failure:

```rust
impl Connection<Connected> {
    /// On success: transitions to Authenticated
    /// On failure: returns the error AND the still-Connected connection
    pub fn authenticate(self, token: &str) -> Result<Connection<Authenticated>, (AuthError, Self)> {
        if token.is_empty() {
            return Err((AuthError::EmptyToken, self)); // caller keeps Connected state
        }
        Ok(Connection {
            addr: self.addr,
            _state: PhantomData,
        })
    }
}
```

This prevents the common bug where a failed transition leaves you with no handle at all (the old state was consumed, the new state wasn't created).

---

## Advanced: Shared Behavior Across States

Use a blanket impl or a trait bound for methods available in all states:

```rust
/// Methods available in any state
impl<S> Connection<S> {
    pub fn address(&self) -> &str {
        &self.addr
    }
}

/// Methods available in any "active" state
pub trait Active {}
impl Active for Connected {}
impl Active for Authenticated {}

impl<S: Active> Connection<S> {
    pub fn ping(&self) -> bool {
        // available for Connected and Authenticated, not Disconnected
        true
    }
}
```

---

## Design Review Agent: Typestate Detection

### Trigger Signals

The `design-review` agent scans plan documents for state-machine indicators. These are the patterns to match:

**Explicit state language:**
- "state machine"
- "lifecycle" / "life cycle"
- "must be ... before ..."
- "only when ... is ..."
- "after ... has been ..."
- "transitions from ... to ..."

**Implicit state language:**
- Enumerated phases: "Phase 1: setup, Phase 2: run, Phase 3: teardown"
- Guard conditions: "if connected," "when authenticated," "once initialized"
- Resource protocols: "acquire ... use ... release"

### Agent Output

When a state machine is detected, the agent produces:

```markdown
## Typestate Opportunity Detected

**Resource:** Connection
**States identified:** Disconnected → Connected → Authenticated
**Transitions:**
  - Disconnected → Connected (connect)
  - Connected → Authenticated (authenticate)
  - Connected → Disconnected (disconnect)
  - Authenticated → Disconnected (disconnect)

**Recommendation:** Encode as typestate pattern.
**Shared methods across states:** address() — available in all states
**Fallible transitions:** connect(), authenticate() — should return Result

**Skeleton:**
[auto-generated impl blocks as shown in Core Pattern above]
```

### What the Agent Does NOT Do

- Does not propose typestates for simple boolean flags (`is_enabled: bool`)
- Does not propose typestates when the state set exceeds ~5 states (suggest a state machine crate instead)
- Does not propose typestates when states need to be stored in collections

---

## Code Review: Typestate Smell Detection

A lighter-weight check for existing code that should have been typestates:

| Smell | Example | Suggestion |
|---|---|---|
| Method starts with state assertion | `assert!(self.is_connected)` | Typestate eliminates the assert |
| Boolean field gating behavior | `if self.authenticated { ... } else { panic!() }` | State should be in the type |
| Enum + match in every method | `match self.state { State::A => ..., _ => return Err(...) }` | Each state becomes a type |
| "InvalidState" error variant | `Err(Error::InvalidState)` | Compiler should prevent this |

The `/typestate-audit` command (or a rule in the design-review agent) can scan for these patterns and suggest refactoring.

---

## Migration Strategy

### For new code
Use typestates from the start when the design-review agent identifies a state machine. The skeleton generation makes this near-zero overhead.

### For existing code with state enums
1. Identify the state enum and all methods that branch on it
2. Create marker types for each variant
3. Split the impl block — one per state
4. Change transitions to consuming methods
5. Update call sites to thread the new types through
6. Remove the state enum and all runtime state checks

This is a significant refactor. Only worth it for high-churn state machines where invalid-state bugs have historically occurred.

---

## Testing Typestates

Typestates are primarily tested by **failing to compile**. Use `trybuild` or `compiletest` to assert that invalid code doesn't compile:

```rust
// tests/typestate_compile_fail.rs (using trybuild)
#[test]
fn typestate_prevents_invalid_transitions() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/compile_fail/query_before_auth.rs");
    t.compile_fail("tests/compile_fail/auth_before_connect.rs");
}
```

```rust
// tests/compile_fail/query_before_auth.rs
fn main() {
    let conn = Connection::new("localhost");
    let conn = conn.connect().unwrap();
    conn.query("SELECT 1"); // ERROR: no method named `query` found for `Connection<Connected>`
}
```

This turns the type system guarantee into a regression test.
