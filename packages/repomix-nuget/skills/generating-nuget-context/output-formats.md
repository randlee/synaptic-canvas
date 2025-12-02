# Output Formats

Primary output: XML (`nuget_package_output`), with a `<nuget_package_context>` header followed by Repomix XML sections.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<nuget_package_output>
  <nuget_package_context>
    <package id="YourCompany.Core" version="2.1.0" github="YourCompany/Core" frameworks="net8.0;net6.0" />
    <dependencies>
      <dep id="System.Numerics.Tensors" version="[8.0.0,)" />
      <dep id="YourCompany.Math" version="[1.4.0,2.0.0)" github="YourCompany/Math" />
    </dependencies>
    <dependents>
      <dep id="YourCompany.Sensors" github="YourCompany/Sensors" />
      <dep id="YourCompany.Display" github="YourCompany/Display" />
    </dependents>
    <namespaces>
      <ns>YourCompany.Core</ns>
      <ns>YourCompany.Core.Extensions</ns>
    </namespaces>
  </nuget_package_context>

  <!-- Repomix output follows (wrapped as-is) -->
  <file_summary>...</file_summary>
  <directory_structure>...</directory_structure>
  <files>
    <file path="src/YourCompany.Core/IService.cs"> ... </file>
  </files>
</nuget_package_output>
```

Notes
- `github="owner/repo"` shorthand preferred. For non-GitHub, use `repo="https://..."`.
- Version ranges use NuGet syntax (e.g., `[1.0,2.0)`).
- `frameworks` is semicolon-separated TFMs.
