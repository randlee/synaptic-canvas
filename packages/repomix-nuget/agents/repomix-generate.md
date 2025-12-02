---
name: repomix-generate
version: 0.4.0
description: Execute Repomix to generate compressed XML API surface for a NuGet package.
---

# repomix-generate

## Inputs
- `package_path`: string (default ".")
- `output_path`: string (default "./repomix-output.xml")
- `compress`: boolean (default true)
- `include_patterns`: string[] (default ["**/*.cs"]) 
- `ignore_patterns`: string[] (default ["**/obj/**", "**/bin/**", "**/*.Tests.cs"]) 

## Execution
1. Validate `package_path` exists and contains `.csproj` or `*.cs` files.
2. Build Repomix command:
   - `npx -y repomix --style xml --output <output_path>`
   - Add `--compress` if `compress=true`
   - Add `--include` for each include pattern
   - Add `--ignore` for each ignore pattern
   - Add `--remove-empty-lines`
3. Execute command; fail if non-zero.
4. Validate `<output_path>` created and <= 500KB.
5. Return fenced JSON.

## Output (machine)

````markdown
```json
{
  "success": true,
  "data": {
    "output_path": "./repomix-output.xml",
    "token_count": 0,
    "file_count": 0,
    "compressed": true
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
    "code": "REPO.INCOMPATIBLE",
    "message": "No .cs files found under package_path",
    "recoverable": false,
    "suggested_action": "Specify a directory containing C# sources"
  }
}
```
````

## Constraints
- Do not include tests (`**/*.Tests.cs`, `**/*.Test.cs`).
- Size cap ~500KB; fail if exceeded.
