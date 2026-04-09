# .NET Examples

Use these examples after the language-agnostic contract is fixed. They are patterns to adapt, not copy verbatim.

## Recommended Shape

For a mutating command plus audit readback, keep these pieces aligned:
- `Program.cs` wires commands, handlers, and shared JSON serialization
- DTOs define the machine contract used by both CLI and MCP
- an interface-based adapter hides the real backend
- a service layer owns the business operation
- a simulator can implement the same adapter for tests

## Example Command Pair

Mutating command:

```csharp
var setCommand = new Command("set-device-mode", "Set the mode for a device");
var idOption = new Option<string>("--device-id") { IsRequired = true };
var modeOption = new Option<string>("--mode") { IsRequired = true };
var jsonOption = new Option<bool>("--json");

setCommand.AddOption(idOption);
setCommand.AddOption(modeOption);
setCommand.AddOption(jsonOption);

setCommand.SetHandler(async (string deviceId, string mode, bool json) =>
{
    var request = new SetDeviceModeRequest(deviceId, mode);
    var result = await operations.SetDeviceModeAsync(request);
    await writer.WriteAsync(result, json);
}, idOption, modeOption, jsonOption);
```

Readback command:

```csharp
var getCommand = new Command("get-device", "Read current device state");
var getIdOption = new Option<string>("--device-id") { IsRequired = true };
var getJsonOption = new Option<bool>("--json");

getCommand.AddOption(getIdOption);
getCommand.AddOption(getJsonOption);

getCommand.SetHandler(async (string deviceId, bool json) =>
{
    var result = await operations.GetDeviceAsync(new GetDeviceRequest(deviceId));
    await writer.WriteAsync(result, json);
}, getIdOption, getJsonOption);
```

## Shared Contract Types

```csharp
public sealed record SetDeviceModeRequest(string DeviceId, string Mode);

public sealed record SetDeviceModeResponse(
    string DeviceId,
    string RequestedMode,
    string AppliedMode,
    string Status,
    string DiagnosticCode);

public sealed record GetDeviceRequest(string DeviceId);

public sealed record GetDeviceResponse(
    string DeviceId,
    string CurrentMode,
    string Status);
```

## Error Envelope Pattern

Prefer a typed envelope with a stable category and remediation hint:

```csharp
public sealed record CliError(
    string Code,
    string Category,
    string Message,
    string? Remediation,
    object? Details);
```

Examples:
- invalid input: `validation.invalid_mode`
- missing target: `device.not_found`
- backend unavailable: `backend.unavailable`

The error serializer should be shared by both CLI and MCP paths.

## Adapter Boundary Pattern

```csharp
public interface IDeviceBackend
{
    Task<SetDeviceModeResult> SetDeviceModeAsync(SetDeviceModeRequest request, CancellationToken cancellationToken);
    Task<GetDeviceResult> GetDeviceAsync(GetDeviceRequest request, CancellationToken cancellationToken);
}
```

Use the same `IDeviceBackend` from:
- live hardware or network implementation
- stateful simulator
- MCP tool handler through the shared service layer

## Serialization Setup

Keep one serializer policy:

```csharp
[JsonSerializable(typeof(SetDeviceModeResponse))]
[JsonSerializable(typeof(GetDeviceResponse))]
[JsonSerializable(typeof(CliError))]
internal partial class CliJsonContext : JsonSerializerContext
{
}
```

Route all JSON output through one writer so:
- success and failure use the same serializer policy
- `--json` behaves the same for every command
- MCP wrappers can reuse the same DTOs and context

## Testing Pattern

Minimum coverage:
- mutation succeeds and readback confirms the new state
- invalid input returns a typed corrective error
- simulator-injected backend failure returns a stable code and category
- CLI JSON result matches MCP JSON result for the same request

## Template Direction

If you generate scaffolding with `sc-compose` and MiniJinja, these are the first files worth templating:
- `Program.cs`
- command registration for mutating and read commands
- DTO and error envelope definitions
- adapter interface
- simulator skeleton

Use normalized frontmatter with `required_variables`, `defaults`, and `metadata`, and keep the rendered command pair and JSON writer on the same template branch. See `references/template-generation.md` for the shared templating pattern.
