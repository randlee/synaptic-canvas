# Implementation Plan: Sealed Trait Pattern

## Overview

Prevent external crates from implementing your public traits. This gives you freedom to evolve trait surfaces (add methods, change signatures) without breaking downstream consumers — because there are no downstream implementors to break.

## Design Goals

1. Traits are **usable** by external consumers (they can call methods, accept `dyn Trait`)
2. Traits are **not implementable** by external consumers
3. Adding methods to a sealed trait is a **non-breaking change**
4. The sealing mechanism is **zero-cost** and **invisible** to consumers

---

## Core Pattern: Rust

```rust
// --- In your crate's public API ---

// The sealed module is public (so the trait bound is satisfiable)
// but its contents are private (so no one outside can implement Sealed)
mod sealed {
    pub trait Sealed {}
}

/// A trait that external crates can use but not implement.
///
/// This trait is sealed — it cannot be implemented outside this crate.
/// See: https://rust-lang.github.io/api-guidelines/future-proofing.html
pub trait Plugin: sealed::Sealed {
    fn name(&self) -> &str;
    fn execute(&self, input: &[u8]) -> Vec<u8>;

    // Because this trait is sealed, we can add methods in future
    // versions without breaking anyone:
    // fn version(&self) -> u32 { 1 }  // ← safe to add later
}

// --- Internal implementations ---

pub struct JsonPlugin;

impl sealed::Sealed for JsonPlugin {}

impl Plugin for JsonPlugin {
    fn name(&self) -> &str { "json" }
    fn execute(&self, input: &[u8]) -> Vec<u8> {
        // ...
        input.to_vec()
    }
}

pub struct CsvPlugin;

impl sealed::Sealed for CsvPlugin {}

impl Plugin for CsvPlugin {
    fn name(&self) -> &str { "csv" }
    fn execute(&self, input: &[u8]) -> Vec<u8> {
        // ...
        input.to_vec()
    }
}
```

**What external crates see:**
```rust
use your_crate::{Plugin, JsonPlugin};

// ✅ Can use the trait
fn process(plugin: &dyn Plugin) {
    println!("{}", plugin.name());
}

// ✅ Can use concrete types
let p = JsonPlugin;
process(&p);

// ❌ Cannot implement the trait
// struct MyPlugin;
// impl Plugin for MyPlugin { ... }
// ERROR: the trait bound `MyPlugin: sealed::Sealed` is not satisfied
```

---

## When to Seal

### Seal when:

| Situation | Reason |
|---|---|
| Trait is part of a public crate API | Preserve freedom to add methods |
| Trait has a fixed set of implementations | Plugin registries, codec sets, protocol handlers |
| Trait methods have safety invariants | Prevent incorrect implementations from violating guarantees |
| Trait is used for exhaustive matching via downcasting | You need to know all implementors |

### Don't seal when:

| Situation | Reason |
|---|---|
| Trait is meant to be extended by users | The whole point is external implementation |
| Trait is a standard abstraction (`Display`, `Iterator`) | Users expect to implement these |
| Trait is crate-internal only | `pub(crate)` is sufficient |

---

## Variation: Sealed Trait with Extension Points

Sometimes you want a sealed core with an open extension mechanism. Use two traits:

```rust
mod sealed {
    pub trait Sealed {}
}

/// Core behavior — sealed, only internal implementations.
pub trait CorePlugin: sealed::Sealed {
    fn name(&self) -> &str;
    fn execute(&self, input: &[u8]) -> Vec<u8>;
}

/// Extension behavior — open, anyone can implement.
/// Only requires a reference to a CorePlugin, not implementation of one.
pub trait PluginExt {
    fn pre_process(&self, input: &[u8]) -> Vec<u8>;
    fn post_process(&self, output: &[u8]) -> Vec<u8>;
}
```

This gives you a sealed kernel that you control, with open extension points that downstream crates can hook into.

---

## Crate Boundary Agent: Sealed Trait Detection

### When It Runs

The `crate-boundary` agent triggers during:
- Crate extraction PRs (splitting a workspace into published crates)
- Any PR that adds or modifies `pub trait` declarations
- API review milestones

### Detection Logic

For every `pub trait` in a crate's public API, the agent asks:

```
1. Is this trait intended for external implementation?
   - YES → Leave unsealed. Document the extension point.
   - NO → Recommend sealing.
   - UNCLEAR → Flag for manual review.

2. How many implementations exist today?
   - Fixed set (2-10) → Strong seal candidate.
   - Open-ended → Probably should not seal.

3. Does the trait have safety invariants?
   - YES → Seal unless there's a compelling reason not to.
   - NO → Seal if the implementation set is fixed.

4. Is the trait object-safe?
   - YES → Sealing is compatible with `dyn Trait` usage.
   - NO → Sealing still works but limits dynamic dispatch.
```

### Agent Output

```markdown
## Crate Boundary Review: `atm-core`

### `pub trait MessageRouter`
- Implementations: InboxRouter, BroadcastRouter, DirectRouter (3, fixed)
- External implementation expected: No
- **Recommendation: SEAL**
- Rationale: Fixed set of routing strategies. Sealing allows adding
  methods (e.g., `fn priority(&self) -> u8`) without a breaking change.

### `pub trait AgentHandler`
- Implementations: varies by consumer
- External implementation expected: Yes (agents register custom handlers)
- **Recommendation: DO NOT SEAL**
- Consider: Sealed core trait + open extension trait pattern if
  some methods need protection.

### `pub trait Serializable`
- Implementations: all message types
- External implementation expected: Yes (custom message types)
- **Recommendation: DO NOT SEAL**
```

---

## Documentation Convention

Every sealed trait should carry a doc comment explaining the seal:

```rust
/// Routes messages between agents in the ATM system.
///
/// # Sealed
///
/// This trait is sealed and cannot be implemented outside of `atm-core`.
/// This allows the trait to evolve (new methods, changed signatures)
/// without breaking downstream crates.
///
/// If you need custom routing behavior, implement [`RoutingExt`] instead.
pub trait MessageRouter: sealed::Sealed {
    // ...
}
```

### Clippy / Custom Lint

A custom lint (or sc-hooks rule) to flag:

| Rule ID | Description | Severity |
|---|---|---|
| S001 | `pub trait` without sealed supertrait and no `#[unsealed]` attribute | Warning |
| S002 | Sealed trait missing doc comment explaining the seal | Info |
| S003 | `pub trait` with `sealed::Sealed` bound but `sealed` module is missing | Error |

The `#[unsealed]` attribute is a project-local annotation (not a real Rust attribute — implemented as a doc comment tag or cfg flag) that explicitly marks a trait as intentionally open, suppressing S001.

---

## Migration Strategy

### For existing public traits in a crate being extracted

1. **Audit all `pub trait` declarations** in the crate
2. **Classify each** as seal / don't seal / needs discussion
3. **Add the sealed module** — this is a single file addition, no existing code changes
4. **Add `sealed::Sealed` bound** to traits being sealed — this IS a breaking change if anyone was implementing the trait
5. **Add `impl sealed::Sealed for ...`** to all existing implementors
6. **Document** each sealed trait

**Breaking change mitigation:** If the trait was previously open and you're sealing it:
- Release a minor version that **deprecates** external implementation (add a doc warning)
- Release a major version that **seals** the trait
- Or: if the crate is pre-1.0, seal freely

### For new crates

Default to sealed. Use the crate-boundary agent's review to identify which traits should be open. It's easier to unseal later (non-breaking) than to seal later (breaking).

---

## Cross-Language Reference

### C# / .NET

The closest equivalent uses `internal` visibility:

```csharp
public interface IPlugin
{
    string Name { get; }
    byte[] Execute(byte[] input);

    // Internal method prevents external implementation
    // (external assemblies can't satisfy the interface contract)
    internal void Seal() { }
}

// Or more explicitly:
public abstract class PluginBase
{
    internal PluginBase() { } // internal constructor blocks external subclassing
    public abstract string Name { get; }
    public abstract byte[] Execute(byte[] input);
}
```

### Go

Use an unexported method in the interface:

```go
type Plugin interface {
    Name() string
    Execute(input []byte) []byte
    sealed() // unexported — only types in this package can implement
}

type jsonPlugin struct{}

func (j jsonPlugin) Name() string            { return "json" }
func (j jsonPlugin) Execute(b []byte) []byte { return b }
func (j jsonPlugin) sealed()                 {} // satisfies the interface
```

### TypeScript

Use a module-scoped symbol as a brand:

```typescript
const SEALED = Symbol("sealed");

export interface Plugin {
    readonly [SEALED]: true; // external code can't create this symbol
    name(): string;
    execute(input: Uint8Array): Uint8Array;
}
```

### Python

Use `__init_subclass__` to block external inheritance:

```python
class Plugin:
    _ALLOWED = {"JsonPlugin", "CsvPlugin"}

    def __init_subclass__(cls, **kwargs):
        if cls.__name__ not in Plugin._ALLOWED:
            raise TypeError(f"{cls.__name__} cannot implement Plugin (sealed)")
        super().__init_subclass__(**kwargs)
```

Note: All non-Rust approaches are runtime enforcement, not compile-time. They prevent implementation but don't catch violations until execution.

---

## Testing Sealed Traits

### Positive tests
Standard unit tests for each implementor — verify behavior.

### Negative tests (Rust)
Use `trybuild` to verify that external implementation fails to compile:

```rust
// tests/sealed_compile_fail.rs
#[test]
fn sealed_traits_reject_external_impl() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/compile_fail/external_plugin_impl.rs");
}
```

```rust
// tests/compile_fail/external_plugin_impl.rs
use your_crate::Plugin;

struct Rogue;

impl Plugin for Rogue {
    fn name(&self) -> &str { "rogue" }
    fn execute(&self, input: &[u8]) -> Vec<u8> { vec![] }
}

fn main() {}
// EXPECTED ERROR: the trait bound `Rogue: sealed::Sealed` is not satisfied
```

### API surface tests
Verify that sealed traits are usable as trait objects (if object-safe):

```rust
#[test]
fn sealed_trait_is_object_safe() {
    let plugins: Vec<Box<dyn Plugin>> = vec![
        Box::new(JsonPlugin),
        Box::new(CsvPlugin),
    ];
    for p in &plugins {
        assert!(!p.name().is_empty());
    }
}
```
