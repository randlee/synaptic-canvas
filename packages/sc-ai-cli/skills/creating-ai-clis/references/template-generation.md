# Template Generation with `sc-compose`

Use this reference when repeated CLI scaffolding should be generated from templates instead of copied by hand.

`sc-compose` is a good fit for AI-CLI boilerplate because it already supports typed `.j2` templates, normalized YAML frontmatter, scalar defaults, and deterministic file-mode rendering.

## When to Use Templates

Prefer `sc-compose`-rendered templates when:
- multiple commands follow the same JSON contract pattern
- the CLI needs the same request/response, error-envelope, and adapter scaffolding in more than one place
- you want a skill or code skeleton to be reproducible instead of hand-assembled

Do not template unstable architecture decisions. Fix the contract first, then template the repeated shape.

## `sc-compose` Conventions

The useful baseline from `sc-compose` is:
- template files end in `.j2`
- typed template files are valid, such as `.md.j2`, `.rs.j2`, `.cs.j2`, or `.go.j2`
- YAML frontmatter must start at byte 0 with `---`
- normalized frontmatter keys are:
  - `required_variables`
  - `defaults`
  - `metadata`
- `defaults` should contain only scalar fallback values
- `metadata` is descriptive, not semantic
- include directives should live on standalone lines in the form `@<path>`

For skill templates, prefer `SKILL.md.j2`. For code or asset templates, keep typed file extensions so the rendered output is obvious.

## Normalized Frontmatter Pattern

Even when some collections are empty, keep all three keys present:

```yaml
---
required_variables:
  - cli_name
  - command_name
  - entity_name
defaults:
  json_flag: "--json"
  namespace: "Example.Cli"
metadata: {}
---
```

This keeps template expectations explicit and aligns with `sc-compose frontmatter-init`.

## Suggested Template Variables

Good scalar variables for AI-CLI boilerplate include:
- `cli_name`
- `command_name`
- `entity_name`
- `namespace`
- `module_name`
- `package_name`
- `request_type`
- `response_type`
- `error_type`
- `adapter_type`

Avoid trying to force whole object graphs into frontmatter defaults. Keep the template variables simple and explicit.

## Example Template Shapes

Useful first template targets:
- CLI entrypoint wiring
- mutating command plus readback command
- request and response types
- common error envelope
- adapter interface or trait
- simulator skeleton
- parity tests for CLI and MCP JSON fixtures

## Example `Program.cs.j2`

```csharp
---
required_variables:
  - namespace
  - command_name
  - request_type
  - response_type
defaults:
  json_flag: "--json"
metadata: {}
---
namespace {{ namespace }};

public static class {{ command_name|replace("-", "_")|title }}Command
{
    public static Command Create({{ response_type }}Writer writer, IOperations operations)
    {
        var command = new Command("{{ command_name }}");
        var jsonOption = new Option<bool>("{{ json_flag }}");
        command.AddOption(jsonOption);
        return command;
    }
}
```

## Example `main.rs.j2`

```rust
---
required_variables:
  - module_name
  - command_name
  - request_type
defaults:
  json_flag: "--json"
metadata: {}
---
pub mod {{ module_name }};

#[derive(clap::Args)]
pub struct {{ request_type }}Args {
    #[arg(long)]
    pub json: bool,
}
```

## Example `main.go.j2`

```go
---
required_variables:
  - package_name
  - command_name
defaults:
  json_flag: "--json"
metadata: {}
---
package {{ package_name }}

func new{{ command_name|replace("-", " ")|title|replace(" ", "") }}Cmd() *cobra.Command {
	cmd := &cobra.Command{Use: "{{ command_name }}"}
	return cmd
}
```

## Guidance for AI-CLI Skills

When templating AI-facing CLIs:
- keep the JSON contract types explicit in the rendered output
- do not generate separate CLI and MCP DTO families unless a transport boundary forces it
- keep the `--json` path present in every generated command
- generate mutating and readback command pairs together
- generate simulator seams together with the live adapter seam

Templates should accelerate a sound design. They should not lock in a weak contract.
