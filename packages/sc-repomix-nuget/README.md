# sc-repomix-nuget

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](CHANGELOG.md)

Scope: Local-only
Requires: node >= 18 (for `npx repomix`), bash

Generate AI-optimized context for NuGet packages using Repomix with NuGet metadata enrichment (dependencies, dependents, frameworks, namespaces). Produces a compressed API surface designed for AI code tools.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Quick Start
1) Install into your repo's `.claude`:
```bash
python3 tools/sc-install.py install sc-repomix-nuget --dest /path/to/your-repo/.claude
```
2) From your repo, run:
```
/sc-repomix-nuget --generate --package-path . --output ./nuget-context.xml
```

## Command
- `/sc-repomix-nuget --help`
- `/sc-repomix-nuget --generate [--package-path <path>] [--output <file>] [--include-docs] [--registry-url <url>]`

## Skill & Agents
- Skill: `sc-repomix-nuget` (Agent Runner → agents)
- Agents: `sc-repomix-nuget-generate`, `sc-repomix-nuget-validate`, `sc-repomix-nuget-analyze`

## Getting Started
- Minimal run in a C# repo:
  ```
  /sc-repomix-nuget --generate --package-path . --output ./nuget-context.xml
  ```
- With registry URL (recommended once you host it):
  ```
  /sc-repomix-nuget --generate \
    --package-path . \
    --output ./nuget-context.xml \
--registry-url https://raw.githubusercontent.com/<owner>/<repo>/main/docs/registries/nuget/registry.json
  ```
  Notes:
  - `raw.githubusercontent.com` serves the raw JSON bytes for tools; `github.com` serves HTML pages.
- Create `docs/registries/nuget/registry.json` in your repo when ready; until then, omit `--registry-url`.

## Defaults
- Output file: `./nuget-context.xml`
- If `.nuget-context.json` is missing, the skill attempts to infer `package_id` from a primary `.csproj`.

## Examples
- Different output path:
  ```
  /sc-repomix-nuget --generate --output ./artifacts/nuget-context.xml
  ```
- Disable compression (debug):
  ```
  .claude/scripts/generate.sh --no-compress
  ```

## Notes
- `.nuget-context.json` is optional: provides package id, public namespaces, depends_on
  - If missing, package id may be inferred from a primary `.csproj`; namespaces via simple heuristics
- Output is capped at ~500KB for the compressed tier

## CI snippet (optional)
```yaml
- name: Generate NuGet AI context
  run: |
    npx repomix --style xml --compress \
      --include "**/*.cs" \
      --ignore "**/obj/**,**/bin/**,**/*.Tests.cs" \
      --output ./artifacts/nuget-context.xml
```

## Support
- Repository: https://github.com/randlee/synaptic-canvas
- Issues: https://github.com/randlee/synaptic-canvas/issues
