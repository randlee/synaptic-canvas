# Rust Examples

Use these examples after the language-agnostic contract is fixed. They are patterns to adapt, not copy verbatim.

## Recommended Shape

For a mutating command plus audit readback, keep these pieces aligned:
- `clap` command definitions parse arguments and `--json`
- request and response structs define the machine contract
- a trait-based adapter hides the real backend
- an operation layer owns business rules
- a simulator implements the same trait for tests

## Example Command Pair

Mutating command:

```rust
#[derive(clap::Args)]
pub struct SetDeviceModeArgs {
    #[arg(long)]
    pub device_id: String,
    #[arg(long)]
    pub mode: String,
    #[arg(long)]
    pub json: bool,
}

pub async fn run_set_device_mode(
    args: SetDeviceModeArgs,
    ops: &dyn DeviceOperations,
    writer: &OutputWriter,
) -> anyhow::Result<()> {
    let request = SetDeviceModeRequest {
        device_id: args.device_id,
        mode: args.mode,
    };
    let response = ops.set_device_mode(request).await?;
    writer.write(&response, args.json)
}
```

Readback command:

```rust
#[derive(clap::Args)]
pub struct GetDeviceArgs {
    #[arg(long)]
    pub device_id: String,
    #[arg(long)]
    pub json: bool,
}

pub async fn run_get_device(
    args: GetDeviceArgs,
    ops: &dyn DeviceOperations,
    writer: &OutputWriter,
) -> anyhow::Result<()> {
    let response = ops
        .get_device(GetDeviceRequest { device_id: args.device_id })
        .await?;
    writer.write(&response, args.json)
}
```

## Shared Contract Types

```rust
#[derive(Serialize, Deserialize)]
pub struct SetDeviceModeRequest {
    pub device_id: String,
    pub mode: String,
}

#[derive(Serialize, Deserialize)]
pub struct SetDeviceModeResponse {
    pub device_id: String,
    pub requested_mode: String,
    pub applied_mode: String,
    pub status: String,
    pub diagnostic_code: String,
}

#[derive(Serialize, Deserialize)]
pub struct GetDeviceRequest {
    pub device_id: String,
}

#[derive(Serialize, Deserialize)]
pub struct GetDeviceResponse {
    pub device_id: String,
    pub current_mode: String,
    pub status: String,
}
```

## Error Union Pattern

Prefer a tagged union or strongly-typed error struct over flattened strings:

```rust
#[derive(Serialize, Deserialize)]
#[serde(tag = "category", rename_all = "snake_case")]
pub enum CliError {
    Validation {
        code: String,
        message: String,
        remediation: String,
    },
    NotFound {
        code: String,
        message: String,
        remediation: String,
    },
    Backend {
        code: String,
        message: String,
        remediation: String,
    },
}
```

This is the pattern to aim for when lifting strong domain errors up to the CLI surface.

## Adapter Boundary Pattern

```rust
#[async_trait::async_trait]
pub trait DeviceBackend: Send + Sync {
    async fn set_device_mode(
        &self,
        request: SetDeviceModeRequest,
    ) -> Result<SetDeviceModeResponse, DomainError>;

    async fn get_device(
        &self,
        request: GetDeviceRequest,
    ) -> Result<GetDeviceResponse, DomainError>;
}
```

Use the same trait for:
- the live implementation
- a stateful simulator
- the operation layer called by both CLI and MCP entrypoints

## Output Envelope Direction

If the CLI benefits from a common wrapper, prefer a versioned envelope:

```rust
#[derive(Serialize, Deserialize)]
pub struct Envelope<T> {
    pub version: String,
    pub ok: bool,
    pub data: Option<T>,
    pub error: Option<CliError>,
}
```

Use a single writer for success and failure so `--json` never disappears on top-level errors.

## Testing Pattern

Minimum coverage:
- mutation succeeds and readback confirms state
- invalid input returns a typed corrective error
- simulator-injected backend failure returns a stable code
- CLI JSON and MCP JSON match for the same fixture
- partial-success cases are represented explicitly rather than silently dropped

## Template Direction

If you generate scaffolding with `sc-compose` and MiniJinja, these are the first files worth templating:
- `main.rs` command wiring
- args and command enums
- request and response structs
- error enums and envelope types
- backend trait and simulator skeleton

Use normalized frontmatter with `required_variables`, `defaults`, and `metadata`, and keep the rendered command pair and shared output writer on the same template branch. See `template-generation.md` for the shared templating pattern.
