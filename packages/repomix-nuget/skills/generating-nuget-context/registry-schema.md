# Registry Schema & Source

Recommended registry location in your repo:
- `docs/nuget/registry.json` (track in git)
- Tools should fetch the raw JSON via:
  - `https://raw.githubusercontent.com/<owner>/<repo>/main/docs/nuget/registry.json`
  (raw.githubusercontent.com serves the raw file bytes; github.com serves HTML.)

Behavior
- If fetch fails (timeout 10s), the `registry-resolve` agent proceeds with empty dependents and logs a warning.
- Local `.nuget-context.json` (optional) augments package id, public namespaces, and local dependencies.

Minimal schema (summary)
```json
{
  "packages": {
    "Package.Id": {
      "github": "owner/repo",   // optional
      "repo": "https://...",    // optional
      "dependents": [ { "id": "Other.Id", "github": "owner/other" } ]
    }
  }
}
```
