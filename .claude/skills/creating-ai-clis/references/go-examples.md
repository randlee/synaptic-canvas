# Go Examples

Use these examples after the language-agnostic contract is fixed. They are patterns to adapt, not copy verbatim.

## Recommended Shape

For a mutating command plus audit readback, keep these pieces aligned:
- command definitions parse flags including `--json`
- request and response structs define the machine contract
- an interface-based adapter hides the real backend
- an operation layer owns business rules
- a simulator implements the same interface for tests

## Example Command Pair

Mutating command:

```go
func newSetDeviceModeCmd(ops DeviceOperations, writer OutputWriter) *cobra.Command {
	cmd := &cobra.Command{
		Use: "set-device-mode",
		RunE: func(cmd *cobra.Command, args []string) error {
			deviceID, _ := cmd.Flags().GetString("device-id")
			mode, _ := cmd.Flags().GetString("mode")
			jsonMode, _ := cmd.Flags().GetBool("json")

			request := SetDeviceModeRequest{
				DeviceID: deviceID,
				Mode:     mode,
			}
			response, err := ops.SetDeviceMode(cmd.Context(), request)
			return writer.Write(cmd.OutOrStdout(), response, err, jsonMode)
		},
	}
	cmd.Flags().String("device-id", "", "Target device id")
	cmd.Flags().String("mode", "", "Requested mode")
	cmd.Flags().Bool("json", false, "Emit machine-readable JSON")
	_ = cmd.MarkFlagRequired("device-id")
	_ = cmd.MarkFlagRequired("mode")
	return cmd
}
```

Readback command:

```go
func newGetDeviceCmd(ops DeviceOperations, writer OutputWriter) *cobra.Command {
	cmd := &cobra.Command{
		Use: "get-device",
		RunE: func(cmd *cobra.Command, args []string) error {
			deviceID, _ := cmd.Flags().GetString("device-id")
			jsonMode, _ := cmd.Flags().GetBool("json")

			response, err := ops.GetDevice(cmd.Context(), GetDeviceRequest{DeviceID: deviceID})
			return writer.Write(cmd.OutOrStdout(), response, err, jsonMode)
		},
	}
	cmd.Flags().String("device-id", "", "Target device id")
	cmd.Flags().Bool("json", false, "Emit machine-readable JSON")
	_ = cmd.MarkFlagRequired("device-id")
	return cmd
}
```

## Shared Contract Types

```go
type SetDeviceModeRequest struct {
	DeviceID string `json:"device_id"`
	Mode     string `json:"mode"`
}

type SetDeviceModeResponse struct {
	DeviceID       string `json:"device_id"`
	RequestedMode  string `json:"requested_mode"`
	AppliedMode    string `json:"applied_mode"`
	Status         string `json:"status"`
	DiagnosticCode string `json:"diagnostic_code"`
}

type GetDeviceRequest struct {
	DeviceID string `json:"device_id"`
}

type GetDeviceResponse struct {
	DeviceID    string `json:"device_id"`
	CurrentMode string `json:"current_mode"`
	Status      string `json:"status"`
}
```

## Error Envelope Pattern

Prefer a stable structured error:

```go
type CliError struct {
	Code        string         `json:"code"`
	Category    string         `json:"category"`
	Message     string         `json:"message"`
	Remediation string         `json:"remediation,omitempty"`
	Details     map[string]any `json:"details,omitempty"`
}
```

Avoid returning bare `fmt.Errorf` strings from the top-level command path in JSON mode.

## Adapter Boundary Pattern

```go
type DeviceBackend interface {
	SetDeviceMode(ctx context.Context, request SetDeviceModeRequest) (SetDeviceModeResponse, error)
	GetDevice(ctx context.Context, request GetDeviceRequest) (GetDeviceResponse, error)
}
```

Use the same interface for:
- live network or device implementation
- stateful simulator
- operation layer called by both CLI and MCP handlers

## Output Envelope Direction

If the CLI benefits from a common wrapper, centralize it:

```go
type Envelope[T any] struct {
	Version string    `json:"version"`
	OK      bool      `json:"ok"`
	Data    *T        `json:"data,omitempty"`
	Error   *CliError `json:"error,omitempty"`
}
```

This reduces drift between commands and helps keep failure paths as machine-readable as success paths.

## Testing Pattern

Minimum coverage:
- mutation succeeds and readback confirms state
- invalid input returns a typed corrective error
- simulator-injected dependency failure returns a stable category and code
- CLI JSON and MCP JSON match for the same fixture
- database-backed or device-backed tests do not require live infrastructure for routine runs

## Template Direction

If you add Jinja2 or code templates later, these are the first files worth templating:
- root command and subcommand registration
- request and response structs
- output writer and error envelope
- backend interface
- simulator skeleton
