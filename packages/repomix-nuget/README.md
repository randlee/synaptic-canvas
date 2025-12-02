# repomix-nuget

Scope: Local-only  
Requires: node >= 18 (for `npx repomix`), bash

Generate AI-optimized context for NuGet packages using Repomix with NuGet metadata enrichment (dependencies, dependents, frameworks, namespaces). Produces a compressed API surface designed for AI code tools.

## Quick Start
1) Install into your repo’s `.claude`:
```bash
python3 tools/sc-install.py install repomix-nuget --dest /path/to/your-repo/.claude
```
2) From your repo, run:
```
/repomix-nuget --generate --package-path . --output ./nuget-context.xml
```

## Command
- `/repomix-nuget --help`
- `/repomix-nuget --generate [--package-path <path>] [--output <file>] [--include-docs] [--registry-url <url>]`

## Skill & Agents
- Skill: `generating-nuget-context` (Agent Runner → agents)
- Agents: `repomix-generate`, `registry-resolve`, `context-assemble`

## Getting Started
- Minimal run in a C# repo:
  ```
  /repomix-nuget --generate --package-path . --output ./nuget-context.xml
  ```
- With registry URL (recommended once you host it):
  ```
  /repomix-nuget --generate \
    --package-path . \
    --output ./nuget-context.xml \
    --registry-url https://raw.githubusercontent.com/<owner>/<repo>/main/docs/nuget/registry.json
  ```
  Notes:
  - `raw.githubusercontent.com` serves the raw JSON bytes for tools; `github.com` serves HTML pages.
  - Create `docs/nuget/registry.json` in your repo when ready; until then, omit `--registry-url`.

## Defaults
- Output file: `./nuget-context.xml`
- If `.nuget-context.json` is missing, the skill attempts to infer `package_id` from a primary `.csproj`.

## Examples
- Different output path:
  ```
  /repomix-nuget --generate --output ./artifacts/nuget-context.xml
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
