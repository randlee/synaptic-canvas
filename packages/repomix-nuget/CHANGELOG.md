# Changelog

All notable changes to the **repomix-nuget** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Multi-project workspace analysis (.NET 6.0+ projects)
- ASP.NET Core endpoint and API route extraction
- Semantic analysis of interfaces and abstract classes
- Integration with IDE symbol navigation
- Support for C# analyzer rule packages
- Graph-based dependency visualization
- Performance benchmarking for large codebases

## [0.4.0] - 2025-12-02

### Status
Beta release - initial v0.x publication. Local-only scope (repo-level installation only).

### Added
- **repomix-generate** agent: Generate AI-optimized NuGet package context
  - Integrated Repomix invocation with XML output formatting
  - Automatic C# source code filtering and compression
  - Excludes build artifacts and test binaries (`/obj/`, `/bin/`, `*.Tests.cs`)
  - Configurable output file path (default: `./nuget-context.xml`)
  - Optional documentation inclusion (`--include-docs` flag)
- **registry-resolve** agent: Fetch and validate NuGet package registry
  - Retrieve central package registry from configurable URL
  - Automatic registry schema validation
  - HTTP/HTTPS URL support with error handling
  - Cache registry locally for efficiency
  - Support for raw GitHub URLs (`raw.githubusercontent.com`)
- **context-assemble** agent: Enrich Repomix output with NuGet metadata
  - Extract package metadata from `.csproj` and `.nuspec` files
  - Resolve dependencies, dependents, and target frameworks
  - Enumerate public namespaces from source code
  - Merge Repomix output with metadata in structured XML format
  - Produce final context at ~500KB (compressed tier)
- `/repomix-nuget` command: User-facing command for context generation
  - `--help`: Display usage information
  - `--generate`: Trigger context generation workflow
  - `--package-path <path>`: Root path for package analysis (default: `.`)
  - `--output <file>`: Output file path (default: `./nuget-context.xml`)
  - `--include-docs`: Include README and documentation sections
  - `--registry-url <url>`: Central registry URL for package metadata enrichment
- **generate.sh** script: Wrapper for Repomix invocation
  - Handles Node.js version checking and npx fallback
  - Configurable compression (use `--no-compress` for debugging)
  - Source code filtering and language selection
  - Exit code handling and error reporting
- **validate-registry.sh** script: Registry validation and schema checking
  - JSON schema validation for registry format
  - URL verification and accessibility checks
  - Optional cache invalidation

### Components
- Command: `commands/repomix-nuget.md`
- Skill: `skills/generating-nuget-context/SKILL.md`
- Skills Documentation:
  - `skills/generating-nuget-context/output-formats.md`: Output format reference
  - `skills/generating-nuget-context/registry-schema.md`: Registry structure and metadata
- Agents:
  - `agents/repomix-generate.md` (v0.4.0)
  - `agents/registry-resolve.md` (v0.4.0)
  - `agents/context-assemble.md` (v0.4.0)
- Scripts:
  - `scripts/generate.sh`: Repomix wrapper with compression control
  - `scripts/validate-registry.sh`: Registry validation utility

### Dependencies
- **node** >= 18: For `npx repomix` command invocation
- **bash**: For script execution and shell command composition

### Scope
- **Local-only**: Can only be installed in a repository's `.claude` directory
- Not available for global installation
- Requires a .NET/C# project with `.csproj` or `.nuspec` files

### Features
- **Token Substitution (Tier 1 Package)**: Uses `{{REPO_NAME}}` token (future enhancement)
  - Current version uses explicit package path and output parameters
- **NuGet Metadata Enrichment**:
  - Automatic `.csproj` parsing for package ID and frameworks
  - Optional `.nuget-context.json` for explicit package configuration
  - Namespace inference from C# source code
  - Dependency chain analysis
- **Compression & Optimization**:
  - Output capped at ~500KB for compressed tier
  - XML-based format for AI tool integration
  - Efficient code representation with metadata preservation
- **Registry Integration**:
  - Curated registry of NuGet packages at `docs/registries/nuget/registry.json`
  - Package metadata: name, version, description, frameworks, dependencies
  - URL-based registry fetching with local caching

### Known Limitations
- Single-project analysis only (v0.4.0 - no monorepo/multi-project support)
- No analysis of ASP.NET Core endpoint metadata or routes
- No semantic code analysis (symbols, type hierarchies, interface implementations)
- Limited to C# source files (no F#, VB.NET in v0.4.0)
- Namespace inference uses basic heuristics (not semantic analysis)
- No IDE integration or symbol navigation
- Registry schema is fixed; no custom metadata fields
- Performance may degrade on very large codebases (>100K lines)

### Installation
```bash
# Local installation (inside a git repository with .NET project)
python3 tools/sc-install.py install repomix-nuget --dest /path/to/your-repo/.claude
```

### Uninstallation
```bash
python3 tools/sc-install.py uninstall repomix-nuget --dest /path/to/your-repo/.claude
```

### Troubleshooting
- **"npx: command not found"**: Node.js >= 18 is not installed or not in PATH
  - Solution: Install Node.js from https://nodejs.org/ (LTS or current version)
- **"No .csproj found"**: Package ID inference failed
  - Solution: Create `.nuget-context.json` with explicit `package_id` field, or ensure primary `.csproj` exists
- **"Registry URL not accessible"**: Network issue or invalid URL
  - Solution: Check network connectivity, verify `--registry-url` format, or omit flag to skip registry enrichment
- **"Output file too large (>500KB)"**: Compression failed or codebase too large
  - Solution: Reduce source code scope or use `--no-compress` for debugging
- **"Invalid registry format"**: Central registry schema mismatch
  - Solution: Validate registry against schema in `skills/generating-nuget-context/registry-schema.md`

### Requirements
- **node** >= 18 (for `npx repomix` access)
- **bash** (for script execution)
- A .NET/C# project with `.csproj` or `.nuspec` file

### Usage Examples
```bash
# Basic generation in current repo
/repomix-nuget --generate --package-path . --output ./nuget-context.xml

# With registry enrichment
/repomix-nuget --generate \
  --package-path . \
  --output ./nuget-context.xml \
  --registry-url https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json

# With documentation inclusion
/repomix-nuget --generate \
  --package-path . \
  --output ./nuget-context.xml \
  --include-docs

# Debug mode (uncompressed output)
.claude/scripts/generate.sh --no-compress
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Generate NuGet AI context
  run: |
    npx repomix --style xml --compress \
      --include "**/*.cs" \
      --ignore "**/obj/**,**/bin/**,**/*.Tests.cs" \
      --output ./artifacts/nuget-context.xml

# GitLab CI example
generate_nuget_context:
  script:
    - npx repomix --style xml --compress --include "**/*.cs" --ignore "**/obj/**,**/bin/**" --output ./nuget-context.xml
```

### Future Roadmap
- v0.5.0: Multi-project workspace analysis and monorepo support
- v0.6.0: ASP.NET Core endpoint and route extraction
- v1.0.0: Stable API with full backward compatibility
- Semantic code analysis for interfaces and abstract classes
- IDE integration for symbol navigation
- Support for C# analyzer rules and packages
- Dependency graph visualization
- Performance optimization for large codebases

### Contributing
When updating this changelog:
1. Add entries under **[Unreleased]** for new features, bug fixes, or breaking changes
2. Use standard changelog categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**
3. Link issue/PR numbers when available
4. Create a new section with version and date when releasing
5. Maintain chronological order with newest versions at the top
6. Document any changes to registry schema or output format
7. Update examples if command syntax changes

---

## Registry Format
The central package registry (`docs/registries/nuget/registry.json`) documents NuGet packages with metadata for AI context enrichment. See `skills/generating-nuget-context/registry-schema.md` for full schema reference.

## Repository
- **Repository**: [synaptic-canvas](https://github.com/randlee/synaptic-canvas)
- **Issues**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- **Package Registry**: [docs/registries/nuget/registry.json](https://github.com/randlee/synaptic-canvas/blob/main/docs/registries/nuget/registry.json)
- **Repomix Project**: [repomix](https://github.com/yamadashy/repomix)
