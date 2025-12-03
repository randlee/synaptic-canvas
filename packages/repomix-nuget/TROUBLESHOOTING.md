# repomix-nuget Troubleshooting Guide

This guide helps diagnose and resolve common issues with the repomix-nuget package for Synaptic Canvas.

## Quick Diagnostics

Run these commands to verify your setup:

```bash
# Verify Node.js (required for npx repomix)
node --version  # Should be >= 18

# Verify npm/npx
npx --version

# Check if repomix-nuget is installed
ls -la .claude/commands/repomix-nuget.md
ls -la .claude/scripts/generate.sh

# Test repomix availability
npx repomix --version

# Check for .csproj files (NuGet project indicator)
find . -name "*.csproj" -maxdepth 3

# Verify bash is available
bash --version

# Test generation script
bash .claude/scripts/generate.sh --help
```

## Common Issues

### 1. Command Not Found: `/repomix-nuget` Not Recognized

**Problem:** When you run `/repomix-nuget`, Claude doesn't recognize the command.

**Symptoms:**
```
Unknown command: /repomix-nuget
```

**Root Causes:**
- Package not installed
- Installed globally (only local supported)
- Not in a git repository

**Resolution:**

1. Verify you're in a git repository:
```bash
git rev-parse --git-dir
# Should output: .git
```

2. Install locally (repomix-nuget is local-only):
```bash
cd /path/to/your/nuget/repo
python3 /path/to/synaptic-canvas/tools/sc-install.py \
  install repomix-nuget --dest ./.claude
```

3. Verify installation:
```bash
ls .claude/commands/repomix-nuget.md
ls .claude/scripts/generate.sh
ls .claude/agents/repomix-generate.md
```

4. If missing, reinstall:
```bash
python3 tools/sc-install.py install repomix-nuget --dest ./.claude --force
```

**Prevention:**
- repomix-nuget is local-only (repo-specific)
- Always install in NuGet package repository root
- Verify git repo exists first

---

### 2. Node.js Not Found or Wrong Version

**Problem:** Repomix fails because Node.js is not available or too old.

**Symptoms:**
```
node: command not found
npx: command not found
```
or
```
Error: Node.js version 16.x not supported (requires >= 18)
```

**Root Causes:**
- Node.js not installed
- Node.js version too old (requires >= 18)
- Node.js not in PATH

**Resolution:**

1. Check Node.js version:
```bash
node --version
# Requires: v18.0.0 or higher
```

2. If not installed or too old:

**macOS:**
```bash
# Using Homebrew
brew install node@20

# Or use nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20
```

**Linux (Ubuntu/Debian):**
```bash
# Using NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Or use nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20
```

**Windows:**
- Download from [nodejs.org](https://nodejs.org/) (LTS version)
- Or use nvm-windows

3. Verify installation:
```bash
node --version
npm --version
npx --version
```

4. Test repomix:
```bash
npx repomix --version
```

**Prevention:**
- Use Node.js LTS versions (18, 20, 22)
- Keep Node.js in PATH
- Use version managers (nvm) for flexibility

---

### 3. .NET/NuGet Project Not Detected

**Problem:** Script cannot find or parse NuGet project files.

**Symptoms:**
```
Error: No .csproj files found
Warning: Cannot infer package ID
No NuGet project detected in current directory
```

**Root Causes:**
- Not in a NuGet package directory
- .csproj file in subdirectory
- Project file has non-standard name or location

**Resolution:**

1. **Check for .csproj files:**
```bash
find . -name "*.csproj"
```

2. **If .csproj exists but not detected:**
```bash
# Specify package path explicitly
/repomix-nuget --generate --package-path ./src/MyPackage --output ./nuget-context.xml
```

3. **If .csproj in root:**
```bash
ls *.csproj
# Should show project file(s)
```

4. **For solution-level context:**
```bash
# If you have multiple packages in a solution
# Run from individual package directory
cd src/MyPackage
/repomix-nuget --generate --output ../../artifacts/nuget-context.xml
```

5. **Create .nuget-context.json for explicit config:**
```json
{
  "package_id": "MyCompany.MyPackage",
  "public_namespaces": [
    "MyCompany.MyPackage",
    "MyCompany.MyPackage.Extensions"
  ],
  "depends_on": [
    "Newtonsoft.Json",
    "Microsoft.Extensions.DependencyInjection"
  ]
}
```

**Prevention:**
- Run from package root (where .csproj lives)
- Use `--package-path` for non-standard layouts
- Create .nuget-context.json for complex projects

---

### 4. Context Generation Errors

**Problem:** Repomix fails during context generation.

**Symptoms:**
```
Error: repomix execution failed
Output file not created
repomix: command failed with exit code 1
```

**Root Causes:**
- Invalid file patterns
- Circular references in includes
- Files too large
- Repomix version incompatibility

**Resolution:**

1. **Test repomix directly:**
```bash
npx repomix --help
npx repomix --version
```

2. **Run with minimal options:**
```bash
npx repomix --style xml --output ./test-output.xml --include "**/*.cs"
```

3. **Check for problematic files:**
```bash
# Find very large files
find . -name "*.cs" -size +1M

# Check for encoding issues
file **/*.cs | grep -v "UTF-8"
```

4. **Review ignore patterns:**
```bash
# Verify ignore patterns in generate.sh
cat .claude/scripts/generate.sh | grep IGNORE_PATTERNS
```

5. **Run script with verbose output:**
```bash
bash -x .claude/scripts/generate.sh --package-path . --output ./debug-output.xml
```

6. **Check repomix cache:**
```bash
# Clear repomix cache if corrupted
rm -rf ~/.repomix
npx repomix --clear-cache
```

**Prevention:**
- Use standard C# project layouts
- Exclude large generated files (obj/, bin/)
- Keep source files UTF-8 encoded
- Update repomix regularly: `npx repomix@latest`

---

### 5. Framework Compatibility Issues

**Problem:** Generated context doesn't match target framework.

**Symptoms:**
```
Warning: Target framework not detected
Context missing framework-specific APIs
Multi-targeting not handled correctly
```

**Root Causes:**
- Multi-targeted project (.NET Standard + .NET 8)
- Framework-specific code not included
- Conditional compilation not handled

**Resolution:**

1. **Check project target frameworks:**
```bash
# View .csproj file
cat *.csproj | grep TargetFramework
```

Expected output examples:
```xml
<TargetFramework>net8.0</TargetFramework>
<!-- or -->
<TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>
```

2. **For multi-targeted projects:**
```bash
# Context includes all files, but AI needs to understand target
# Add framework info to .nuget-context.json
cat > .nuget-context.json <<'EOF'
{
  "package_id": "MyPackage",
  "target_frameworks": ["net8.0", "netstandard2.0"],
  "public_namespaces": ["MyPackage"]
}
EOF
```

3. **Include framework-specific files:**
```bash
# Ensure all conditional compilation files are included
find . -name "*.cs" | grep -E "(net[0-9]|netstandard)"
```

4. **Test with specific include patterns:**
```bash
bash .claude/scripts/generate.sh \
  --include "**/*.cs" \
  --include "**/net8.0/**/*.cs" \
  --ignore "**/netstandard2.0/**/*.cs"
```

**Prevention:**
- Document target frameworks in .nuget-context.json
- Include all framework-specific source files
- Test context with AI for each target framework

---

### 6. File Encoding Issues

**Problem:** Generated context has garbled characters or fails to parse.

**Symptoms:**
```
Error: XML parsing failed
Warning: Invalid UTF-8 sequence
Context contains ��� characters
```

**Root Causes:**
- Non-UTF-8 source files
- BOM (Byte Order Mark) in files
- Binary files incorrectly included
- Windows-1252 encoding

**Resolution:**

1. **Check file encodings:**
```bash
# Check all .cs files
find . -name "*.cs" -exec file {} \; | grep -v "UTF-8"
```

2. **Convert to UTF-8:**
```bash
# macOS/Linux
find . -name "*.cs" -exec iconv -f WINDOWS-1252 -t UTF-8 {} -o {}.utf8 \; \
  -exec mv {}.utf8 {} \;

# Or use dos2unix
find . -name "*.cs" -exec dos2unix {} \;
```

3. **Remove BOM if present:**
```bash
# Find files with BOM
find . -name "*.cs" -exec grep -l $'\xEF\xBB\xBF' {} \;

# Remove BOM
find . -name "*.cs" -exec sed -i '1s/^\xEF\xBB\xBF//' {} \;
```

4. **Exclude binary files explicitly:**
```bash
# Ensure ignore patterns exclude binary
bash .claude/scripts/generate.sh \
  --ignore "**/bin/**" \
  --ignore "**/obj/**" \
  --ignore "**/*.dll" \
  --ignore "**/*.exe"
```

5. **Verify output encoding:**
```bash
file ./nuget-context.xml
# Should show: XML 1.0 document, UTF-8 Unicode text
```

**Prevention:**
- Configure editor/IDE to use UTF-8
- Set .editorconfig:
```ini
[*.cs]
charset = utf-8
```
- Use git attributes:
```gitattributes
*.cs text eol=lf encoding=utf-8
```

---

### 7. Output File Too Large

**Problem:** Generated context exceeds size limits.

**Symptoms:**
```
Output too large (512000+ bytes)
Error: Size cap exceeded (~500KB)
Context file rejected by AI tool
```

**Root Causes:**
- Too many source files included
- Large XML comments/documentation included
- Test files included
- Generated code not excluded

**Resolution:**

1. **Check output size:**
```bash
ls -lh ./nuget-context.xml
# Should be < 500KB for optimal AI usage
```

2. **Use compression (default):**
```bash
# Compression is enabled by default in generate.sh
# Verify:
cat .claude/scripts/generate.sh | grep compress
```

3. **Exclude more files:**
```bash
# Add more ignore patterns
bash .claude/scripts/generate.sh \
  --ignore "**/obj/**" \
  --ignore "**/bin/**" \
  --ignore "**/*.Tests.cs" \
  --ignore "**/*.Designer.cs" \
  --ignore "**/*.g.cs"
```

4. **Focus on public API surface:**
```bash
# Only include public-facing files
# Create a custom script or use .repomixignore
cat > .repomixignore <<'EOF'
**/obj/**
**/bin/**
**/*.Tests.cs
**/Internal/**
**/Private/**
EOF
```

5. **Split into multiple contexts:**
```bash
# Generate separate contexts for different namespaces
/repomix-nuget --generate --package-path ./src/Core --output ./core-context.xml
/repomix-nuget --generate --package-path ./src/Extensions --output ./ext-context.xml
```

**Prevention:**
- Use `--compress` flag (default)
- Exclude test files and internal code
- Focus on public API surface
- Keep packages small and focused

---

### 8. Registry Resolution Failures

**Problem:** Cannot fetch or parse NuGet package registry.

**Symptoms:**
```
Error: Registry URL not accessible
Failed to parse registry JSON
Registry entry not found for package
```

**Root Causes:**
- Registry URL incorrect or not provided
- Registry file not valid JSON
- Network connectivity issues
- Package not listed in registry

**Resolution:**

1. **Check if registry URL provided:**
```bash
# Registry is optional; context generation works without it
# Only needed for enhanced metadata
```

2. **Verify registry URL format:**
```bash
# CORRECT - raw GitHub content
--registry-url https://raw.githubusercontent.com/owner/repo/main/docs/registries/nuget/registry.json

# WRONG - GitHub HTML page
--registry-url https://github.com/owner/repo/blob/main/docs/registries/nuget/registry.json
```

3. **Test registry URL manually:**
```bash
# Should return JSON
curl -s "https://raw.githubusercontent.com/owner/repo/main/docs/registries/nuget/registry.json" | jq .
```

4. **Create local registry:**
```bash
# For private packages, create registry in your repo
mkdir -p docs/registries/nuget
cat > docs/registries/nuget/registry.json <<'EOF'
{
  "packages": {
    "MyCompany.MyPackage": {
      "repository": "https://github.com/mycompany/mypackage",
      "description": "My package description",
      "public_namespaces": ["MyCompany.MyPackage"]
    }
  }
}
EOF
```

5. **Validate registry schema:**
```bash
# Use validation script if available
bash .claude/scripts/validate-registry.sh docs/registries/nuget/registry.json
```

6. **Generate without registry (degraded mode):**
```bash
# Works fine without registry, just less metadata
/repomix-nuget --generate --package-path . --output ./nuget-context.xml
# (omit --registry-url)
```

**Prevention:**
- Use raw GitHub URLs for registries
- Validate JSON before committing
- Test registry accessibility
- Registry is optional - generate works without it

---

## Installation & Setup Issues

### Bash Not Available

**Problem:**
```bash
bash: command not found
.claude/scripts/generate.sh: not executable
```

**Resolution:**

1. **Verify bash installation:**
```bash
which bash
# Should show: /bin/bash or /usr/bin/bash
```

2. **On Windows, use Git Bash:**
```bash
# Git Bash comes with Git for Windows
# Or use WSL
```

3. **Make script executable:**
```bash
chmod +x .claude/scripts/generate.sh
```

4. **Or run with explicit bash:**
```bash
bash .claude/scripts/generate.sh --help
```

---

### Script Permission Denied

**Problem:**
```bash
Permission denied: .claude/scripts/generate.sh
```

**Resolution:**

1. **Fix permissions:**
```bash
chmod +x .claude/scripts/generate.sh
```

2. **Verify:**
```bash
ls -la .claude/scripts/generate.sh
# Should show: -rwxr-xr-x (executable)
```

3. **If still denied, run with bash:**
```bash
bash .claude/scripts/generate.sh --help
```

---

### Installation in Non-NuGet Repository

**Problem:** Installing in repository that doesn't contain NuGet packages.

**Resolution:**

1. **Verify repository type:**
```bash
# Check for .csproj files
find . -name "*.csproj" -maxdepth 3

# If none found, this isn't a NuGet package repo
```

2. **Install only in NuGet package repositories:**
```bash
# Navigate to correct repo
cd /path/to/your/nuget/package

# Verify .csproj exists
ls *.csproj

# Then install
python3 tools/sc-install.py install repomix-nuget --dest ./.claude
```

---

## Configuration Issues

### Missing .nuget-context.json

**Problem:** Script cannot infer package metadata.

**Symptoms:**
```
Warning: .nuget-context.json not found
Attempting to infer package ID from .csproj
```

**Resolution:**

1. **Create .nuget-context.json (recommended):**
```json
{
  "package_id": "MyCompany.MyPackage",
  "public_namespaces": [
    "MyCompany.MyPackage",
    "MyCompany.MyPackage.Extensions"
  ],
  "depends_on": [
    "Newtonsoft.Json",
    "Microsoft.Extensions.DependencyInjection"
  ],
  "target_frameworks": ["net8.0", "netstandard2.0"]
}
```

2. **Place in repository root:**
```bash
ls -la .nuget-context.json
# Should exist alongside .csproj file
```

3. **Or let script infer (may be incomplete):**
```bash
# Script will try to parse .csproj
# But may miss multi-package repos or complex setups
```

**Prevention:**
- Always create .nuget-context.json for production packages
- Include all relevant metadata
- Update when package structure changes

---

### Incorrect Output Path

**Problem:** Output file created in unexpected location.

**Resolution:**

1. **Understand default output:**
```bash
# Default: ./repomix-output.xml (in current directory)
```

2. **Specify explicit output:**
```bash
/repomix-nuget --generate --output ./artifacts/nuget-context.xml
```

3. **Ensure output directory exists:**
```bash
mkdir -p ./artifacts
/repomix-nuget --generate --output ./artifacts/nuget-context.xml
```

4. **Use absolute paths if needed:**
```bash
/repomix-nuget --generate --output /tmp/nuget-context.xml
```

---

## Integration Issues

### Using with CI/CD Pipelines

**Problem:** Context generation in CI fails or produces inconsistent results.

**Resolution:**

1. **Ensure Node.js available in CI:**
```yaml
# GitHub Actions example
- name: Setup Node.js
  uses: actions/setup-node@v3
  with:
    node-version: '20'

- name: Generate NuGet context
  run: |
    bash .claude/scripts/generate.sh \
      --package-path . \
      --output ./artifacts/nuget-context.xml
```

2. **Cache npx/repomix:**
```yaml
- name: Cache npm
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
```

3. **Use specific repomix version:**
```bash
# Instead of npx repomix (latest)
npx repomix@3.0.0 --style xml --output ./nuget-context.xml
```

4. **Handle failures gracefully:**
```yaml
- name: Generate context
  continue-on-error: true
  run: bash .claude/scripts/generate.sh
```

---

### Using with Multiple Packages

**Problem:** Monorepo with multiple NuGet packages.

**Resolution:**

1. **Generate context per package:**
```bash
# Package 1
cd src/Package1
/repomix-nuget --generate --output ../../artifacts/package1-context.xml

# Package 2
cd ../Package2
/repomix-nuget --generate --output ../../artifacts/package2-context.xml
```

2. **Or combine contexts:**
```bash
# Generate combined context for entire solution
cd solution-root
bash .claude/scripts/generate.sh \
  --package-path . \
  --include "src/**/*.cs" \
  --ignore "**/obj/**" \
  --ignore "**/bin/**" \
  --output ./artifacts/solution-context.xml
```

3. **Use solution-level .nuget-context.json:**
```json
{
  "packages": [
    {
      "package_id": "MyCompany.Package1",
      "public_namespaces": ["MyCompany.Package1"]
    },
    {
      "package_id": "MyCompany.Package2",
      "public_namespaces": ["MyCompany.Package2"]
    }
  ]
}
```

---

### Dependency Resolution

**Problem:** Package dependencies not reflected in context.

**Resolution:**

1. **Add to .nuget-context.json:**
```json
{
  "package_id": "MyPackage",
  "depends_on": [
    "Newtonsoft.Json",
    "Microsoft.Extensions.Logging",
    "MyCompany.SharedLib"
  ]
}
```

2. **Or parse from .csproj:**
```bash
# Extract package references
grep PackageReference *.csproj
```

3. **For transitive dependencies:**
```bash
# Use dotnet list
dotnet list package --include-transitive
```

---

## Performance & Timeout Issues

### Slow Context Generation

**Problem:** Generation takes very long time.

**Root Causes:**
- Large repository with many files
- Slow filesystem (network drives)
- Repomix processing large files

**Resolution:**

1. **Exclude unnecessary directories:**
```bash
bash .claude/scripts/generate.sh \
  --ignore "**/obj/**" \
  --ignore "**/bin/**" \
  --ignore "**/packages/**" \
  --ignore "**/.nuget/**"
```

2. **Use sparse patterns:**
```bash
# Only include source directories
bash .claude/scripts/generate.sh \
  --include "src/**/*.cs" \
  --output ./nuget-context.xml
```

3. **Check for very large files:**
```bash
find . -name "*.cs" -size +500k
# Exclude if generated/designer files
```

4. **Run from SSD/local drive:**
```bash
# Don't run from network-mounted directories
df -h .
```

---

### Memory Issues

**Problem:** Process crashes with out-of-memory errors.

**Resolution:**

1. **Increase Node.js memory limit:**
```bash
NODE_OPTIONS="--max-old-space-size=4096" npx repomix --style xml --output ./nuget-context.xml
```

2. **Process in chunks:**
```bash
# Generate contexts for subdirectories separately
bash .claude/scripts/generate.sh --package-path ./src/Core
bash .claude/scripts/generate.sh --package-path ./src/Extensions
```

---

## Platform-Specific Issues

### macOS stat Command

**Problem:** Script uses Linux-style stat command.

**Symptoms:**
```
stat: illegal option -- c
```

**Resolution:**

The generate.sh script handles both:
```bash
# Script already handles macOS vs Linux
SIZE=$(stat -f%z "$OUTPUT_PATH" 2>/dev/null || stat -c%s "$OUTPUT_PATH")
```

If you see errors, update script or use latest version.

---

### Windows Line Endings

**Problem:** Scripts fail due to CRLF line endings.

**Symptoms:**
```
$'\r': command not found
syntax error near unexpected token `$'\r''
```

**Resolution:**

1. **Convert to LF:**
```bash
# Using dos2unix
dos2unix .claude/scripts/generate.sh

# Or sed
sed -i 's/\r$//' .claude/scripts/generate.sh
```

2. **Configure git:**
```bash
git config core.autocrlf false
git checkout -- .claude/scripts/generate.sh
```

3. **Use WSL:**
```bash
wsl bash .claude/scripts/generate.sh
```

---

### Linux Permissions

**Problem:** Scripts not executable after clone on Linux.

**Resolution:**

```bash
# Fix permissions
chmod +x .claude/scripts/*.sh

# Or explicitly via git
git update-index --chmod=+x .claude/scripts/generate.sh
```

---

## Getting Help

### When to Escalate

Escalate to GitHub issues if you encounter:

- Repomix crashes or produces invalid output
- Context generation consistently fails
- Size limits too restrictive for your use case
- Registry schema questions
- Integration issues with AI tools consuming context

### How to Report Bugs

Include the following information:

1. **Environment details:**
```bash
node --version
npm --version
npx repomix --version
bash --version
uname -a
```

2. **Project structure:**
```bash
# Show .csproj and key files
find . -name "*.csproj" -maxdepth 3
ls -la .nuget-context.json
ls -la .claude/scripts/generate.sh
```

3. **Command that failed:**
```bash
/repomix-nuget --generate --package-path . --output ./nuget-context.xml
```

4. **Error output:**
```
# Full error message and stack trace
```

5. **Generated output (if any):**
```bash
ls -lh ./nuget-context.xml
head -20 ./nuget-context.xml
```

### Debug Information to Collect

**Basic diagnostics:**
```bash
# Environment
node --version
npm --version
npx repomix --version

# Installation
ls -la .claude/commands/repomix-nuget.md
ls -la .claude/scripts/generate.sh
ls -la .claude/agents/repomix-*.md

# Project structure
find . -name "*.csproj"
ls -la .nuget-context.json
```

**For generation issues:**
```bash
# Run with debug
bash -x .claude/scripts/generate.sh --package-path . --output ./debug.xml

# Check repomix directly
npx repomix --style xml --output ./test.xml --include "**/*.cs" --verbose

# Verify file encodings
find . -name "*.cs" -exec file {} \; | head -20
```

**For size issues:**
```bash
# Count source files
find . -name "*.cs" | wc -l

# Total size
find . -name "*.cs" -exec cat {} \; | wc -c

# Check output
ls -lh ./nuget-context.xml
file ./nuget-context.xml
```

---

## FAQ

### Q: Do I need to install Repomix separately?

**A:** No, `npx` downloads and runs Repomix automatically:
```bash
npx repomix  # Downloads if not cached
```

To install globally:
```bash
npm install -g repomix
```

---

### Q: Can I use repomix-nuget for other languages?

**A:** No, repomix-nuget is specific to .NET/NuGet packages:
- Expects .csproj files
- Includes C# file patterns
- Parses NuGet metadata

For other languages, use Repomix directly.

---

### Q: What's the difference between compressed and uncompressed output?

**A:**
- **Compressed** (default): Removes whitespace, optimizes for AI token efficiency
- **Uncompressed**: Human-readable, good for debugging

Use compressed for production (smaller, faster AI processing).

---

### Q: How often should I regenerate context?

**A:**
- After significant API changes
- Before major releases
- When adding new public types/methods
- For AI-assisted development sessions

Automate in CI for continuous updates.

---

### Q: Can I include XML documentation comments?

**A:** Yes, Repomix includes all file content:
```csharp
/// <summary>
/// This will be included in context
/// </summary>
public class MyClass { }
```

Ensure docs are concise to avoid size bloat.

---

### Q: How do I handle internal classes?

**A:** For public API context, exclude internal code:
```bash
bash .claude/scripts/generate.sh \
  --ignore "**/Internal/**" \
  --ignore "**/Private/**"
```

Or mark with `[EditorBrowsable(Never)]` and document in .nuget-context.json.

---

### Q: What if my package has multiple target frameworks?

**A:** Context includes all source files. Document in .nuget-context.json:
```json
{
  "package_id": "MyPackage",
  "target_frameworks": ["net8.0", "netstandard2.0"],
  "notes": "Use #if NET8_0 directives for framework-specific code"
}
```

---

### Q: Can I use repomix-nuget in private repositories?

**A:** Yes:
- All processing is local
- No data sent to external services
- Registry is optional (local or private GitHub repos)

---

### Q: How do I update repomix-nuget?

**A:**
```bash
# Navigate to Synaptic Canvas repo
cd /path/to/synaptic-canvas
git pull origin main

# Reinstall in your NuGet repo
cd /path/to/your/nuget/repo
python3 /path/to/synaptic-canvas/tools/sc-install.py \
  install repomix-nuget --dest ./.claude --force
```

---

### Q: What's the registry for?

**A:** Optional enhanced metadata:
- Links to package repository
- Dependency information
- Public namespace declarations
- Package descriptions

Works fine without registry for basic context generation.

---

## Additional Resources

- **Package README:** `packages/repomix-nuget/README.md`
- **Registry Schema:** `packages/repomix-nuget/skills/generating-nuget-context/registry-schema.md`
- **Changelog:** `packages/repomix-nuget/CHANGELOG.md` (if exists)
- **Skill Documentation:** `packages/repomix-nuget/skills/generating-nuget-context/SKILL.md`
- **Agent Specifications:**
  - `packages/repomix-nuget/agents/repomix-generate.md`
  - `packages/repomix-nuget/agents/registry-resolve.md`
  - `packages/repomix-nuget/agents/context-assemble.md`
- **Scripts:**
  - `packages/repomix-nuget/scripts/generate.sh`
  - `packages/repomix-nuget/scripts/validate-registry.sh`
- **Repomix Documentation:** https://github.com/yamadashy/repomix
- **Repository:** https://github.com/randlee/synaptic-canvas
- **Issues:** https://github.com/randlee/synaptic-canvas/issues
