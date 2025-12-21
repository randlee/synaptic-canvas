<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-repomix-nuget',
    subtitle: '--generate --output ./nuget-context.xml',
    type: 'entry',
    details: {
      description: 'Entry point for NuGet package context generation. Parses flags and orchestrates the workflow through Agent Runner.',
      input: {
        flags: {
          '--generate': 'boolean - Generate compressed API surface and context',
          '--package-path': 'string - Package root path (default ".")',
          '--output': 'string - Output file path (default "./nuget-context.xml")',
          '--include-docs': 'boolean - Include documentation tier (optional)',
          '--registry-url': 'string - Central registry URL override'
        }
      },
      output: {
        operation: 'generate | help',
        params: '{ package_path?, output?, registry_url? }'
      },
      context: ['flags', 'package_path', 'output_path', 'registry_url']
    }
  },
  {
    id: 'validate',
    label: 'Validate Agent',
    subtitle: 'sc-repomix-nuget-validate',
    type: 'agent',
    details: {
      description: 'Resolves package dependencies and dependents from central registry with optional local manifest (.nuget-context.json) augmentation. Fetches registry JSON with 10s timeout.',
      input: {
        package_id: 'string (optional if discoverable)',
        manifest_path: 'string (default ".nuget-context.json")',
        registry_url: 'string (optional)'
      },
      output: {
        success: true,
        data: {
          package: {
            id: 'YourCompany.Core',
            github: 'YourCompany/Core'
          },
          dependencies: [
            { id: 'System.Numerics.Tensors', version: '[8.0.0,)' }
          ],
          dependents: [
            { id: 'YourCompany.Sensors', github: 'YourCompany/Sensors' }
          ]
        }
      },
      context: ['package_metadata', 'dependencies', 'dependents'],
      errorCodes: [
        { code: 'PACKAGE_ID.MISSING', recoverable: false, action: 'Provide --package-id or add .nuget-context.json' },
        { code: 'REGISTRY.FETCH_FAILED', recoverable: true, action: 'Continue with empty dependents' },
        { code: 'MANIFEST.PARSE_ERROR', recoverable: false, action: 'Fix .nuget-context.json syntax' }
      ]
    }
  },
  {
    id: 'generate',
    label: 'Generate Agent',
    subtitle: 'sc-repomix-nuget-generate',
    type: 'agent',
    details: {
      description: 'Executes Repomix to generate compressed XML API surface for the NuGet package. Uses Tree-sitter compression and filters C# files while excluding tests and build artifacts.',
      input: {
        package_path: 'string (default ".")',
        output_path: 'string (default "./repomix-output.xml")',
        compress: 'boolean (default true)',
        include_patterns: 'string[] (default ["**/*.cs"])',
        ignore_patterns: 'string[] (default ["**/obj/**", "**/bin/**", "**/*.Tests.cs"])'
      },
      output: {
        success: true,
        data: {
          output_path: './repomix-output.xml',
          token_count: 0,
          file_count: 0,
          compressed: true
        }
      },
      context: ['repomix_output_path', 'token_count', 'file_count'],
      errorCodes: [
        { code: 'REPO.INCOMPATIBLE', recoverable: false, action: 'Specify directory containing C# sources' },
        { code: 'REPOMIX.EXECUTION_FAILED', recoverable: false, action: 'Check npx and Node.js installation' },
        { code: 'OUTPUT.SIZE_EXCEEDED', recoverable: false, action: 'Reduce included files or use stricter patterns' }
      ]
    }
  },
  {
    id: 'analyze',
    label: 'Analyze Agent',
    subtitle: 'sc-repomix-nuget-analyze',
    type: 'agent',
    details: {
      description: 'Assembles final NuGet context XML by combining Repomix output with NuGet metadata header. Constructs <nuget_package_context> wrapper with dependencies, frameworks, and namespace information.',
      input: {
        repomix_output_path: 'string (required)',
        package_metadata: 'object (id, github/repo, dependencies, dependents, public_namespaces)',
        frameworks: 'string[] (optional)',
        output_path: 'string (default "./nuget-context.xml")'
      },
      output: {
        success: true,
        data: {
          output_path: './nuget-context.xml',
          token_count: 0,
          sections: {
            metadata: 0,
            api_surface: 0
          }
        }
      },
      context: ['final_output_path', 'token_count', 'sections'],
      errorCodes: [
        { code: 'OUTPUT.INVALID', recoverable: false, action: 'Regenerate repomix output and retry' },
        { code: 'XML.MALFORMED', recoverable: false, action: 'Validate Repomix output XML structure' }
      ]
    }
  },
  {
    id: 'success',
    label: 'Complete',
    subtitle: 'context generated',
    type: 'success',
    details: {
      description: 'NuGet package context successfully generated. The XML file contains compressed API surface with NuGet metadata header, ready for AI consumption.',
      context: ['final_status', 'output_location', 'summary']
    }
  },
  {
    id: 'validate_error',
    label: 'Validation Failed',
    subtitle: 'package not found',
    type: 'error',
    details: {
      description: 'Package validation failed. Cannot determine package ID or manifest is malformed.',
      errorCodes: [
        { code: 'PACKAGE_ID.MISSING', recoverable: false, action: 'Create .nuget-context.json or provide --package-id' },
        { code: 'MANIFEST.PARSE_ERROR', recoverable: false, action: 'Fix JSON syntax in .nuget-context.json' }
      ]
    }
  },
  {
    id: 'generate_error',
    label: 'Generation Failed',
    subtitle: 'repomix error',
    type: 'error',
    details: {
      description: 'Repomix execution failed or produced invalid output. May be due to missing dependencies or incompatible repository structure.',
      errorCodes: [
        { code: 'REPO.INCOMPATIBLE', recoverable: false, action: 'Ensure .csproj and .cs files exist' },
        { code: 'REPOMIX.EXECUTION_FAILED', recoverable: false, action: 'Verify Node.js >= 18 and npx availability' },
        { code: 'OUTPUT.SIZE_EXCEEDED', recoverable: false, action: 'Exclude more files or split into smaller contexts' }
      ]
    }
  },
  {
    id: 'analyze_error',
    label: 'Assembly Failed',
    subtitle: 'XML malformed',
    type: 'error',
    details: {
      description: 'Failed to assemble final context XML. Repomix output may be malformed or missing.',
      errorCodes: [
        { code: 'OUTPUT.INVALID', recoverable: false, action: 'Regenerate repomix output' },
        { code: 'XML.MALFORMED', recoverable: false, action: 'Check file encoding and XML structure' }
      ]
    }
  }
])

const edges = ref([
  { from: 'command', to: 'validate', label: '--generate flag' },
  { from: 'validate', to: 'generate', label: 'metadata resolved' },
  { from: 'validate', to: 'validate_error', label: 'validation fails' },
  { from: 'generate', to: 'analyze', label: 'repomix complete' },
  { from: 'generate', to: 'generate_error', label: 'repomix fails' },
  { from: 'analyze', to: 'success', label: 'XML assembled' },
  { from: 'analyze', to: 'analyze_error', label: 'assembly fails' }
])
</script>

# sc-repomix-nuget

Generate AI-optimized NuGet package context using Repomix with metadata enrichment.

<PluginFlowVisualizer
  plugin-name="sc-repomix-nuget"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-repomix-nuget` plugin generates compressed, AI-optimized context for .NET/NuGet packages by combining Repomix's Tree-sitter compression with rich package metadata. It produces structured XML containing:

- **Compressed API surface** - All public C# code with optimized formatting
- **Dependency graphs** - Both dependencies and dependents from central registry
- **Framework information** - Target frameworks and compatibility details
- **Namespace hierarchy** - Public namespaces and organizational structure

This enables AI tools to deeply understand your .NET codebase for architecture analysis, documentation generation, code review, and onboarding.

## Quick Start

```bash
# Install in your NuGet package repository
/sc-manage --install sc-repomix-nuget --local

# Generate context (basic)
/sc-repomix-nuget --generate --package-path . --output ./nuget-context.xml

# Generate with registry metadata
/sc-repomix-nuget --generate \
  --package-path . \
  --output ./nuget-context.xml \
  --registry-url https://raw.githubusercontent.com/owner/repo/main/docs/registries/nuget/registry.json
```

## Command Reference

| Flag | Type | Description |
|------|------|-------------|
| `--generate` | boolean | Generate compressed API surface and assemble final XML context |
| `--package-path` | string | Package root path containing .csproj files (default: ".") |
| `--output` | string | Final XML output path (default: "./nuget-context.xml") |
| `--include-docs` | boolean | Include documentation/examples tier (optional; may stub in v0.4) |
| `--registry-url` | string | Central registry URL override (default documented in README) |
| `--help` | boolean | Show usage and options |

## Workflow States

### Entry Point

The command parser determines the operation:

- `--generate` → Full generation workflow (validate → generate → analyze)
- `--help` → Display usage information

### Agent Delegation

This plugin orchestrates three sequential agents via Agent Runner:

1. **Validate Agent** (sc-repomix-nuget-validate) — Resolves package metadata
   - Reads `.nuget-context.json` if present
   - Infers package ID from `.csproj` if needed
   - Fetches dependency/dependent info from central registry (10s timeout)
   - **Output**: Package metadata, dependencies, dependents

2. **Generate Agent** (sc-repomix-nuget-generate) — Executes Repomix
   - Runs `npx repomix` with compression enabled
   - Includes `**/*.cs` files
   - Excludes `**/obj/**`, `**/bin/**`, `**/*.Tests.cs`
   - Enforces ~500KB size cap
   - **Output**: Compressed XML API surface

3. **Analyze Agent** (sc-repomix-nuget-analyze) — Assembles final context
   - Constructs `<nuget_package_context>` header with metadata
   - Wraps Repomix XML under `<nuget_package_output>`
   - Validates well-formed XML
   - **Output**: Final context XML

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `package_path`, `output_path`, `registry_url` |
| Validate Agent | `package_metadata`, `dependencies`, `dependents` |
| Generate Agent | `repomix_output_path`, `token_count`, `file_count` |
| Analyze Agent | `final_output_path`, `sections` |

### No User Decision Gates

This plugin runs fully automated with no user interaction required. If errors occur, the workflow terminates with a descriptive error message.

## Dependencies

This plugin depends on:

- **Node.js** (>= 18) — For running `npx repomix`
- **npm/npx** — Package execution
- **Repomix** (latest) — Installed automatically via npx
- **bash** — For generation scripts
- **.NET/C# project** — Requires `.csproj` files and `.cs` source files

Optional:
- **Central registry** — For enhanced dependency/dependent metadata
- **.nuget-context.json** — For explicit package configuration

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `PACKAGE_ID.MISSING` | Error | Create .nuget-context.json or ensure .csproj contains PackageId |
| `MANIFEST.PARSE_ERROR` | Error | Fix JSON syntax in .nuget-context.json |
| `REGISTRY.FETCH_FAILED` | Warning | Continue with empty dependents (degraded mode) |
| `REPO.INCOMPATIBLE` | Error | Verify .csproj and .cs files exist in package-path |
| `REPOMIX.EXECUTION_FAILED` | Error | Verify Node.js >= 18, check `npx repomix --version` |
| `OUTPUT.SIZE_EXCEEDED` | Error | Exclude more files or split into smaller contexts |
| `OUTPUT.INVALID` | Error | Regenerate repomix output and retry |
| `XML.MALFORMED` | Error | Check file encoding and XML structure |

## Configuration

### Optional: .nuget-context.json

Create this file in your package root for explicit configuration:

```json
{
  "package_id": "MyCompany.MyPackage",
  "public_namespaces": [
    "MyCompany.MyPackage",
    "MyCompany.MyPackage.Extensions"
  ],
  "depends_on": [
    "Newtonsoft.Json",
    "Microsoft.Extensions.DependencyInjection"
  ],
  "target_frameworks": ["net8.0", "netstandard2.0"]
}
```

If `.nuget-context.json` is missing, the validate agent attempts to infer `package_id` from the primary `.csproj` file.

### Optional: Central Registry

Provide a `--registry-url` to fetch enhanced metadata about dependencies and dependents:

```bash
--registry-url https://raw.githubusercontent.com/owner/repo/main/docs/registries/nuget/registry.json
```

The registry must be a JSON file accessible via HTTP. See [registry-schema.md](https://github.com/randlee/synaptic-canvas/blob/main/packages/sc-repomix-nuget/skills/sc-repomix-nuget/registry-schema.md) for schema details.

## Use Cases

- **Architecture Analysis** — Understand project structure, namespaces, and component organization
- **Code Review** — AI-assisted analysis of changes, architectural impact, and breaking changes
- **Dependency Audit** — Identify unused packages, security updates, and consolidation opportunities
- **Framework Compatibility** — Assess upgrade paths and multi-targeting implications
- **Documentation Generation** — Automated API docs, architecture diagrams, and migration guides
- **Team Onboarding** — Rapid understanding of codebase for new developers

## Output Format

The generated XML has this structure:

```xml
<nuget_package_context>
  <package id="YourCompany.Core" github="YourCompany/Core" />
  <dependencies>
    <dependency id="System.Numerics.Tensors" version="[8.0.0,)" />
  </dependencies>
  <dependents>
    <dependent id="YourCompany.Sensors" github="YourCompany/Sensors" />
  </dependents>
  <frameworks>
    <framework>net8.0</framework>
  </frameworks>
  <public_namespaces>
    <namespace>YourCompany.Core</namespace>
  </public_namespaces>
  <nuget_package_output>
    <!-- Compressed Repomix API surface here -->
  </nuget_package_output>
</nuget_package_context>
```

## Related

- [sc-manage](/plugins/sc-manage) — Package installation and management (for installing this plugin)
- [Repomix](https://github.com/yamadashy/repomix) — Underlying compression tool
- [TROUBLESHOOTING](https://github.com/randlee/synaptic-canvas/blob/main/packages/sc-repomix-nuget/TROUBLESHOOTING.md) — Detailed troubleshooting guide
- [USE-CASES](https://github.com/randlee/synaptic-canvas/blob/main/packages/sc-repomix-nuget/USE-CASES.md) — Comprehensive use case examples

## Notes

- **Scope**: Local-only (repository-specific installation)
- **Size Cap**: ~500KB for compressed tier
- **Compression**: Enabled by default via `--compress` flag
- **Test Exclusion**: `**/*.Tests.cs` and `**/*.Test.cs` files automatically excluded
- **Registry**: Optional; context generation works fine without it (degraded mode)
- **Multi-targeting**: All source files included; document target frameworks in `.nuget-context.json`
