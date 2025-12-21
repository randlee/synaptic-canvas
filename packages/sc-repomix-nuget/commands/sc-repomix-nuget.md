---
name: sc-repomix-nuget
description: Generate AI-optimized NuGet package context using Repomix.
version: 0.7.0
options:
  - name: --help
    description: Show usage and options.
  - name: --generate
    description: Generate compressed API surface and assemble final XML context.
  - name: --package-path
    args:
      - name: path
        description: Path to the package (default ".").
    description: Package root path containing .csproj files.
  - name: --output
    args:
      - name: file
        description: Output file path (default "./nuget-context.xml").
    description: Final XML output path.
  - name: --include-docs
    description: Include documentation/examples tier (optional; v0.4 may stub).
  - name: --registry-url
    args:
      - name: url
        description: Registry JSON URL override.
    description: Central registry URL (default raw GitHub URL in README).
---

# /sc-repomix-nuget

Invoke the `sc-repomix-nuget` skill, which orchestrates:
1) Resolve registry info (dependencies/dependents)
2) Run Repomix with compression
3) Assemble final XML with a `<nuget_package_context>` header

Typical:
- `/sc-repomix-nuget --generate --package-path . --output ./nuget-context.xml`
