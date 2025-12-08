---
name: context-assemble
version: 0.5.2
description: Assemble final NuGet context XML by combining Repomix output with NuGet metadata header.
---

# context-assemble

## Inputs
- `repomix_output_path`: string (required)
- `package_metadata`: object (id, github/repo, dependencies[], dependents[], public_namespaces[])
- `frameworks`: string[] (optional)
- `output_path`: string (default `./nuget-context.xml`)

## Execution
1. Read Repomix XML from `repomix_output_path`.
2. Construct `<nuget_package_context>` header from `package_metadata` + `frameworks`.
3. Wrap Repomix XML sections under `<nuget_package_output>`.
4. Write to `output_path`.
5. Validate the final XML is well-formed.

## Output (machine)

````markdown
```json
{
  "success": true,
  "data": {
    "output_path": "./nuget-context.xml",
    "token_count": 0,
    "sections": { "metadata": 0, "api_surface": 0 }
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
    "code": "OUTPUT.INVALID",
    "message": "Repomix output missing or malformed",
    "recoverable": false,
    "suggested_action": "Regenerate repomix output and retry"
  }
}
```
````

## Constraints
- Preserve Repomix XML structure exactly.
- Ensure final XML is well-formed.
