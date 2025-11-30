# Repomix NuGet Skill Specification

> **Purpose**: This document provides a complete specification for implementing the `repomix-nuget` skill. Use this in a Claude Code session with filesystem access to generate the skill at:
> `/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/repomix/packages/repomix-nuget`

---

## 1. Overview

### What This Skill Does

Generates an AI-optimized representation of a NuGet package's public API surface and ecosystem context using [Repomix](https://github.com/yamadashy/repomix). The output is designed for consumption by Claude Code, Codex, and other LLM-based development tools.

### Key Features

1. **Compressed API Surface**: Uses Repomix's Tree-sitter `--compress` flag to extract function/method signatures, interfaces, and type definitions while stripping implementation details (~70% token reduction)
2. **Package Ecosystem Context**: Injects NuGet-specific metadata including dependencies, dependents, and repository URLs
3. **Centralized Dependency Registry**: Supports a back-annotation model where packages self-register as dependents of their upstream dependencies
4. **Two-Tier Output**: Separate artifacts for API surface (compressed) and documentation/examples (uncompressed)

### When to Use

- As part of NuGet package publishing pipeline
- When onboarding AI tools to understand a package's capabilities
- For generating package documentation context
- When analyzing cross-package dependencies

---

## 2. Architecture (per Guidelines v0.4)

### Tier Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Claude Session                       │
│  • User requests: "Generate AI context for MyPackage"        │
│  • Discovers generating-nuget-context skill                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ delegates via skill
┌─────────────────────────────────────────────────────────────┐
│              Skill: generating-nuget-context                 │
│  • Orchestrates the generation workflow                      │
│  • Invokes agents via Agent Runner                           │
│  • Formats final output for user                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ invokes via Agent Runner
┌─────────────────────────────────────────────────────────────┐
│                         Agents                               │
│  • repomix-generate: Runs repomix with configured options    │
│  • registry-resolve: Resolves dependencies/dependents        │
│  • context-assemble: Combines metadata + repomix output      │
└─────────────────────────────────────────────────────────────┘
```

### File Organization

```
packages/repomix-nuget/
├── .claude/
│   ├── skills/
│   │   └── generating-nuget-context/
│   │       ├── SKILL.md              # Entry point
│   │       ├── output-formats.md     # Format specifications
│   │       └── registry-schema.md    # Registry documentation
│   ├── agents/
│   │   ├── registry.yaml             # Agent version registry
│   │   ├── repomix-generate.md       # Runs repomix CLI
│   │   ├── registry-resolve.md       # Resolves package graph
│   │   └── context-assemble.md       # Assembles final output
│   └── state/
│       └── .gitignore
├── schemas/
│   ├── package-manifest.schema.json  # Local package manifest
│   └── package-registry.schema.json  # Central registry schema
├── templates/
│   ├── nuget-context-header.xml      # XML header template
│   └── repomix.config.json           # Base repomix configuration
├── scripts/
│   ├── generate.sh                   # CLI entry point
│   └── validate-registry.sh          # Registry validation
├── README.md
└── package.json                      # If publishing to npm
```

---

## 3. NuGet Package Context Schema

### XML Output Format (Primary)

Repomix defaults to XML, and Anthropic recommends XML for Claude. The skill injects a `<nuget_package_context>` header before the repomix output.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<nuget_package_output>
  
  <nuget_package_context>
    <package id="YourCompany.Core" 
             version="2.1.0" 
             github="YourCompany/Core"
             frameworks="net8.0;net6.0" />
    
    <dependencies>
      <!-- External packages (no github attr) -->
      <dep id="System.Numerics.Tensors" version="[8.0.0,)" />
      <!-- Internal packages (with github attr) -->
      <dep id="YourCompany.Math" version="[1.4.0,2.0.0)" github="YourCompany/Math" />
    </dependencies>
    
    <dependents>
      <!-- Packages that depend on THIS package (back-annotated from registry) -->
      <dep id="YourCompany.Sensors" version="3.0.0" github="YourCompany/Sensors" />
      <dep id="YourCompany.Display" version="2.5.1" github="YourCompany/Display" />
    </dependents>
    
    <namespaces>
      <ns>YourCompany.Core</ns>
      <ns>YourCompany.Core.Extensions</ns>
    </namespaces>
  </nuget_package_context>
  
  <!-- Repomix output follows -->
  <file_summary>
    <!-- Repomix-generated metadata -->
  </file_summary>
  
  <directory_structure>
    <!-- Repomix-generated structure -->
  </directory_structure>
  
  <files>
    <!-- Compressed API surface -->
    <file path="src/YourCompany.Core/IService.cs">
      <!-- Signatures only, no implementations -->
    </file>
  </files>
  
</nuget_package_output>
```

### Attribute Design Decisions

| Attribute | Format | Rationale |
|-----------|--------|-----------|
| `github` | `"company/repo"` | Short form; AI trivially expands to full URL |
| `version` | NuGet range syntax | `[1.0,2.0)` for ranges, `1.0.0` for exact |
| `frameworks` | Semicolon-separated | Matches NuGet TFM convention |
| `<dep>` | Short tag | Token-efficient vs `<dependency>` |
| `<ns>` | Short tag | Token-efficient vs `<namespace>` |

### Non-GitHub Repositories

For packages hosted elsewhere, use full `repo` attribute:

```xml
<dep id="SomePackage" version="1.0.0" repo="https://gitlab.com/org/repo" />
```

The `github` shorthand handles the majority of cases; `repo` provides flexibility.

---

## 4. Centralized Package Registry

### Design Philosophy

Instead of upstream packages tracking who depends on them, **dependent packages self-register** with their dependencies. This inverts ownership and enables:

1. **Back-annotation**: Dependents list populated by querying who registered
2. **Release notifications**: On new release, notify all registered dependents
3. **Impact analysis**: Understand breaking change scope

### Data Flow

```
┌─────────────────────┐
│  YourCompany.Core   │  ← publishes v2.1.0
└─────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│           Central Registry Repository               │
│           (e.g., YourCompany/package-registry)      │
│                                                     │
│  packages/YourCompany.Core/dependents.json:         │
│    [                                                │
│      { "id": "YourCompany.Sensors", ... },          │
│      { "id": "YourCompany.Display", ... }           │
│    ]                                                │
│                                                     │
│  (entries added by Sensors/Display repos via PR)   │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Release workflow:  │
│  Query registry →   │
│  Notify dependents  │
└─────────────────────┘
```

### Local Package Manifest Schema

Each package repo contains `.nuget-context.json`:

```json
{
  "$schema": "https://yourcompany.github.io/schemas/package-manifest.schema.json",
  "package": {
    "id": "YourCompany.Sensors",
    "github": "YourCompany/Sensors"
  },
  "depends_on": [
    "YourCompany.Core",
    "YourCompany.Math"
  ],
  "public_namespaces": [
    "YourCompany.Sensors",
    "YourCompany.Sensors.Calibration"
  ]
}
```

### Central Registry Schema

The central registry aggregates all manifests:

```json
{
  "$schema": "https://yourcompany.github.io/schemas/package-registry.schema.json",
  "packages": {
    "YourCompany.Core": {
      "github": "YourCompany/Core",
      "dependents": [
        { "id": "YourCompany.Sensors", "github": "YourCompany/Sensors" },
        { "id": "YourCompany.Display", "github": "YourCompany/Display" }
      ]
    },
    "YourCompany.Math": {
      "github": "YourCompany/Math",
      "dependents": [
        { "id": "YourCompany.Core", "github": "YourCompany/Core" },
        { "id": "YourCompany.Sensors", "github": "YourCompany/Sensors" }
      ]
    }
  }
}
```

### Registry Update Mechanism

**Option A: PR-based (recommended)**
1. Package repo CI creates PR to central registry when `.nuget-context.json` changes
2. Central registry CI validates and merges
3. Dependents index rebuilt on merge

**Option B: Aggregation job**
1. Scheduled job scans all repos for `.nuget-context.json`
2. Builds inverted dependents index
3. Commits updated registry

---

## 5. Skill Implementation

### SKILL.md

```yaml
---
name: generating-nuget-context
version: 1.0.0
description: >
  Generate AI-optimized context for NuGet packages using Repomix.
  Use when preparing package documentation for Claude Code, creating
  API references, or analyzing package dependencies. Triggers on
  "nuget context", "package API", "repomix nuget", or "AI documentation".
---

# Generating NuGet Package Context

This skill generates AI-optimized representations of NuGet package APIs
using Repomix with NuGet-specific metadata enrichment.

## Capabilities

- Generate compressed API surface (signatures only, ~70% token reduction)
- Resolve package dependencies and dependents from central registry
- Inject NuGet-specific context (frameworks, namespaces, repo URLs)
- Produce two-tier output (API surface + documentation)

## Agent Delegation

| Operation | Agent | Returns |
|-----------|-------|---------|
| Generate repomix output | `repomix-generate` | JSON: output path, token count |
| Resolve package graph | `registry-resolve` | JSON: dependencies, dependents |
| Assemble final context | `context-assemble` | JSON: final output path |

To invoke an agent:
"Use the Agent Runner to invoke `<agent-name>` as defined in `.claude/agents/registry.yaml`"

## Usage

### Basic Generation

When user requests NuGet context generation:

1. Invoke `registry-resolve` to get dependencies/dependents
2. Invoke `repomix-generate` with compression enabled
3. Invoke `context-assemble` to merge metadata with repomix output
4. Return path to generated context file

### Parameters

- `package_path`: Path to package source (default: current directory)
- `output_path`: Where to write output (default: `./nuget-context.xml`)
- `include_docs`: Include documentation tier (default: false)
- `registry_url`: Central registry location (default: from config)

## Reference Files

- [Output Formats](./output-formats.md): Detailed format specifications
- [Registry Schema](./registry-schema.md): Central registry documentation
```

### Agent: repomix-generate.md

```yaml
---
name: repomix-generate
version: 1.0.0
description: Executes repomix CLI with NuGet-optimized configuration.
---

# Repomix Generate Agent

## Purpose

Execute repomix CLI to generate compressed API surface for a NuGet package.

## Inputs

- `package_path`: string - Path to package source directory
- `output_path`: string - Where to write repomix output
- `compress`: boolean - Enable Tree-sitter compression (default: true)
- `include_patterns`: string[] - Glob patterns to include (default: ["**/*.cs"])
- `ignore_patterns`: string[] - Glob patterns to ignore (default: ["**/obj/**", "**/bin/**", "**/*.Tests.cs"])

## Execution Steps

1. Validate package_path exists and contains .csproj
2. Build repomix command with options:
   - `--style xml`
   - `--compress` (if enabled)
   - `--include` patterns
   - `--ignore` patterns
   - `--output` path
   - `--remove-empty-lines`
3. Execute repomix command
4. Verify output file created
5. Extract token count from repomix summary

## Output Format

```json
{
  "success": true,
  "data": {
    "output_path": "/path/to/output.xml",
    "token_count": 12500,
    "file_count": 42,
    "compressed": true
  },
  "error": null
}
```

## Error Handling

### Handled by agent (recoverable):
- Missing repomix: Install via `npx repomix`
- Invalid glob patterns: Fall back to defaults

### Propagated to skill (fatal):
- Package path doesn't exist
- No .cs files found
- Repomix execution fails

## Constraints

- Never include test projects in compressed output
- Never include internal/private namespaces unless explicitly requested
- Maximum output size: 500KB (fail if exceeded)
```

### Agent: registry-resolve.md

```yaml
---
name: registry-resolve
version: 1.0.0
description: Resolves package dependencies and dependents from central registry.
---

# Registry Resolve Agent

## Purpose

Query the central package registry to resolve:
1. This package's dependencies (from local manifest)
2. Packages that depend on this package (from registry)

## Inputs

- `package_id`: string - NuGet package ID
- `manifest_path`: string - Path to local .nuget-context.json (optional)
- `registry_url`: string - URL to central registry JSON

## Execution Steps

1. Read local manifest if manifest_path provided
2. Fetch central registry from registry_url
3. Extract dependencies from local manifest
4. Query registry for dependents of this package
5. Resolve github attributes for all packages

## Output Format

```json
{
  "success": true,
  "data": {
    "package": {
      "id": "YourCompany.Core",
      "github": "YourCompany/Core"
    },
    "dependencies": [
      { "id": "System.Numerics.Tensors", "version": "[8.0.0,)" },
      { "id": "YourCompany.Math", "version": "[1.4.0,2.0.0)", "github": "YourCompany/Math" }
    ],
    "dependents": [
      { "id": "YourCompany.Sensors", "github": "YourCompany/Sensors" },
      { "id": "YourCompany.Display", "github": "YourCompany/Display" }
    ]
  },
  "error": null
}
```

## Error Handling

### Handled by agent (recoverable):
- Registry fetch fails: Return empty dependents, log warning
- Missing github attr: Omit from output

### Propagated to skill (fatal):
- Local manifest malformed
- Package not found in any source

## Constraints

- Never cache registry results (always fetch fresh)
- Timeout registry fetch after 10 seconds
```

### Agent: context-assemble.md

```yaml
---
name: context-assemble
version: 1.0.0
description: Assembles final NuGet context XML from components.
---

# Context Assemble Agent

## Purpose

Combine repomix output with NuGet package metadata to produce final context file.

## Inputs

- `repomix_output_path`: string - Path to repomix-generated XML
- `package_metadata`: object - From registry-resolve agent
- `frameworks`: string[] - Target frameworks (from .csproj)
- `namespaces`: string[] - Public namespaces
- `output_path`: string - Final output location

## Execution Steps

1. Read repomix output XML
2. Generate `<nuget_package_context>` header from metadata
3. Wrap repomix content in `<nuget_package_output>` root
4. Write combined output to output_path
5. Calculate final token count

## Output Format

```json
{
  "success": true,
  "data": {
    "output_path": "/path/to/nuget-context.xml",
    "token_count": 13200,
    "sections": {
      "metadata": 700,
      "api_surface": 12500
    }
  },
  "error": null
}
```

## Error Handling

### Handled by agent (recoverable):
- Missing optional metadata: Omit from output

### Propagated to skill (fatal):
- Repomix output missing or malformed
- Output path not writable

## Constraints

- Preserve repomix XML structure exactly
- Validate final XML is well-formed
```

---

## 6. Agent Registry

### .claude/agents/registry.yaml

```yaml
agents:
  repomix-generate:
    version: 1.0.0
    path: .claude/agents/repomix-generate.md
  registry-resolve:
    version: 1.0.0
    path: .claude/agents/registry-resolve.md
  context-assemble:
    version: 1.0.0
    path: .claude/agents/context-assemble.md

skills:
  generating-nuget-context:
    depends_on:
      repomix-generate: "1.x"
      registry-resolve: "1.x"
      context-assemble: "1.x"
```

---

## 7. JSON Schemas

### package-manifest.schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://yourcompany.github.io/schemas/package-manifest.schema.json",
  "title": "NuGet Package Manifest",
  "description": "Local manifest declaring package identity and dependencies for AI context generation",
  "type": "object",
  "required": ["package", "depends_on"],
  "properties": {
    "package": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id": {
          "type": "string",
          "description": "NuGet package ID"
        },
        "github": {
          "type": "string",
          "pattern": "^[\\w.-]+/[\\w.-]+$",
          "description": "GitHub repo in 'owner/repo' format"
        },
        "repo": {
          "type": "string",
          "format": "uri",
          "description": "Full repository URL (for non-GitHub repos)"
        }
      }
    },
    "depends_on": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Package IDs this package depends on"
    },
    "public_namespaces": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Namespaces intended for public consumption"
    }
  }
}
```

### package-registry.schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://yourcompany.github.io/schemas/package-registry.schema.json",
  "title": "Central Package Registry",
  "description": "Aggregated registry of packages and their dependents",
  "type": "object",
  "required": ["packages"],
  "properties": {
    "packages": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["dependents"],
        "properties": {
          "github": {
            "type": "string",
            "pattern": "^[\\w.-]+/[\\w.-]+$"
          },
          "repo": {
            "type": "string",
            "format": "uri"
          },
          "dependents": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id"],
              "properties": {
                "id": { "type": "string" },
                "github": { "type": "string" },
                "repo": { "type": "string", "format": "uri" }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 8. Repomix Configuration

### templates/repomix.config.json

```json
{
  "output": {
    "style": "xml",
    "filePath": "nuget-context.xml",
    "compress": true,
    "removeEmptyLines": true,
    "showLineNumbers": false
  },
  "include": [
    "**/*.cs"
  ],
  "ignore": {
    "customPatterns": [
      "**/obj/**",
      "**/bin/**",
      "**/*.Tests.cs",
      "**/*.Test.cs",
      "**/TestUtilities/**",
      "**/Internal/**",
      "**/*.Designer.cs",
      "**/AssemblyInfo.cs",
      "**/GlobalUsings.cs"
    ]
  },
  "security": {
    "enableSecurityCheck": true
  }
}
```

---

## 9. Release Notification Workflow

When a package publishes a new version, notify dependents:

### Pseudocode

```bash
#!/bin/bash
# scripts/notify-dependents.sh

PACKAGE_ID="$1"
NEW_VERSION="$2"
REGISTRY_URL="${REGISTRY_URL:-https://yourcompany.github.io/package-registry/registry.json}"

# Fetch dependents from registry
dependents=$(curl -s "$REGISTRY_URL" | jq -r ".packages[\"$PACKAGE_ID\"].dependents[].github")

for repo in $dependents; do
  echo "Notifying $repo of $PACKAGE_ID v$NEW_VERSION"
  
  # Option A: Create GitHub issue
  gh issue create \
    --repo "$repo" \
    --title "Dependency update: $PACKAGE_ID v$NEW_VERSION available" \
    --body "A new version of $PACKAGE_ID is available. Consider updating your dependency."
  
  # Option B: Trigger workflow dispatch
  # gh workflow run dependency-update.yml --repo "$repo" \
  #   -f package="$PACKAGE_ID" -f version="$NEW_VERSION"
done
```

---

## 10. Implementation Checklist

### Phase 1: Core Skill Structure
- [ ] Create directory structure at target path
- [ ] Write SKILL.md with YAML frontmatter
- [ ] Write supporting documentation (output-formats.md, registry-schema.md)
- [ ] Create agent registry.yaml

### Phase 2: Agents
- [ ] Implement repomix-generate.md
- [ ] Implement registry-resolve.md
- [ ] Implement context-assemble.md
- [ ] Add version validation script

### Phase 3: Schemas and Templates
- [ ] Create package-manifest.schema.json
- [ ] Create package-registry.schema.json
- [ ] Create repomix.config.json template
- [ ] Create nuget-context-header.xml template

### Phase 4: Scripts
- [ ] Create generate.sh CLI entry point
- [ ] Create validate-registry.sh
- [ ] Create notify-dependents.sh

### Phase 5: Documentation
- [ ] Write README.md with usage examples
- [ ] Add integration examples for CI/CD

---

## 11. Usage Examples

### Basic Generation

```bash
# From package root directory
claude "Generate AI context for this NuGet package"

# Explicit invocation
claude "Use the generating-nuget-context skill to create API documentation"
```

### With Custom Options

```bash
claude "Generate NuGet context for ./src/MyPackage with documentation tier included"
```

### CI/CD Integration

```yaml
# .github/workflows/nuget-publish.yml
- name: Generate AI Context
  run: |
    npx repomix --style xml --compress \
      --include "**/*.cs" \
      --ignore "**/obj/**,**/bin/**,**/*.Tests.cs" \
      --output ./artifacts/nuget-context.xml
    
- name: Notify Dependents
  run: ./scripts/notify-dependents.sh "${{ env.PACKAGE_ID }}" "${{ env.VERSION }}"
```

---

## 12. Future Enhancements

1. **NuGet.org Integration**: Query nuget.org API for external dependents
2. **Semantic Versioning Analysis**: Detect breaking changes from API diff
3. **Multi-Package Solutions**: Generate context for entire solution
4. **Interactive Mode**: Allow AI to request additional context tiers on demand
5. **Token Budget Management**: Automatic tier selection based on context limits

---

*Document version: 1.0.0*
*Created: November 2025*
*Based on: claude-code-skills-agents-guidelines-0.4.md*
