---
name: registry-resolve
version: 0.5.0
description: Resolve package dependencies and dependents from central registry with optional local manifest augmentation.
---

# registry-resolve

## Inputs
- `package_id`: string (optional if discoverable)
- `manifest_path`: string (optional; default `.nuget-context.json`)
- `registry_url`: string (optional; default documented in README)

## Execution
1. If `manifest_path` exists, read:
   - package.id, package.github/repo
   - depends_on[], public_namespaces[] (optional)
2. If `package_id` not provided, try to infer from a primary `.csproj` (PackageId) or fail with a clear error.
3. Fetch registry JSON (timeout 10s). If fetch fails, continue with empty dependents.
4. Build output:
   - package: { id, github? }
   - dependencies: from local manifest if present; else empty list
   - dependents: from central registry if found; else empty list

## Output (machine)

````markdown
```json
{
  "success": true,
  "data": {
    "package": { "id": "YourCompany.Core", "github": "YourCompany/Core" },
    "dependencies": [ { "id": "System.Numerics.Tensors", "version": "[8.0.0,)" } ],
    "dependents": [ { "id": "YourCompany.Sensors", "github": "YourCompany/Sensors" } ]
  },
  "error": null
}
```
````

## Errors

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PACKAGE_ID.MISSING",
    "message": "Unable to determine package_id from manifest or .csproj",
    "recoverable": false,
    "suggested_action": "Provide --package_id or add .nuget-context.json"
  }
}
```
````

## Constraints
- No caching; fetch registry fresh each invocation.
- 10s timeout for registry fetch.
