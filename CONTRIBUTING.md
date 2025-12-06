# Contributing to Synaptic Canvas

Thank you for your interest in contributing to the Claude Code marketplace! This guide will help you create high-quality packages that follow established patterns and provide value to the community.

## Table of Contents

- [Philosophy](#philosophy)
- [Package Architecture](#package-architecture)
- [Package Tiers](#package-tiers)
- [Manifest Schema](#manifest-schema)
- [Authoring Guidelines](#authoring-guidelines)
- [Command Layer](#command-layer)
- [Skill Layer](#skill-layer)
- [Agent Layer](#agent-layer)
- [Testing Your Package](#testing-your-package)
- [Submission Process](#submission-process)
- [Examples and Patterns](#examples-and-patterns)

## Philosophy

Synaptic Canvas packages follow these core principles:

1. **Layered Design**: Commands → Skills → Agents
   - Commands provide user-facing slash command interfaces
   - Skills define workflows and orchestration logic
   - Agents execute isolated operations with structured outputs

2. **Explicit Contracts**: All interfaces use structured data
   - Commands declare options and arguments upfront
   - Agents return JSON with consistent schemas
   - No implicit behavior or hidden state

3. **Safety First**: Prevent destructive operations
   - Require explicit approval for dangerous actions
   - Validate inputs before execution
   - Provide clear error messages and recovery paths

4. **Minimal Context Pollution**: Keep main conversation clean
   - Agents run in isolated contexts when possible
   - Return concise, structured outputs
   - Avoid tool traces and verbose logging

5. **Installation Simplicity**: Easy to install and customize
   - Tier 0 packages work immediately (direct copy)
   - Tier 1 packages auto-detect repository context
   - Tier 2 packages clearly document dependencies

## Package Architecture

### Directory Structure

```
packages/<package-name>/
├── manifest.yaml           # Required: package metadata
├── commands/              # Optional: slash commands
│   └── command-name.md
├── skills/                # Optional: workflow definitions
│   └── skill-name/
│       └── SKILL.md
├── agents/                # Optional: isolated executors
│   └── agent-name.md
└── scripts/               # Optional: helper scripts
    └── script-name.sh
```

### Artifact Types

**Commands** (`commands/*.md`):
- User-facing slash commands (e.g., `/sc-git-worktree`, `/delay`)
- Define options, arguments, and help text
- Delegate to skills or agents for execution
- Keep simple; avoid complex logic in command definitions

**Skills** (`skills/*/SKILL.md`):
- Workflow orchestration and business logic
- Reference agents for detailed operations
- Provide context and decision-making
- Live in main conversation context

**Agents** (`agents/*.md`):
- Isolated execution contexts
- Perform specific, bounded operations
- Return structured JSON outputs
- Avoid side effects beyond declared outputs

**Scripts** (`scripts/*.sh` or `.py`):
- Shell or Python utilities for heavy lifting
- Called by agents or skills
- Handle waits, file operations, git commands, etc.
- Should be executable (`chmod +x`)

## Package Tiers

### Tier 0: Direct Copy
No token substitution or runtime dependencies.

**Characteristics:**
- Copy contents directly to `.claude/`
- No variables in manifest
- No external tool requirements (or only ubiquitous ones like bash)
- Works immediately after installation

**Example**: `delay-tasks` package

**Best for**: General-purpose utilities, patterns, workflow templates

### Tier 1: Token Substitution
Requires variable substitution at install time.

**Characteristics:**
- Contains `{{VAR}}` tokens in artifacts
- Defines `variables` in manifest with auto-detection
- Customizes behavior per repository
- No runtime dependencies beyond git/bash

**Example**: `sc-git-worktree` package uses `{{REPO_NAME}}`

**Best for**: Repository-specific tools, workflows that need context

**Supported auto-detection patterns:**
- `git-repo-basename`: Repository name from git root directory

### Tier 2: Runtime Dependencies
Requires external tools or libraries.

**Characteristics:**
- May include Tier 0 or Tier 1 features
- Lists dependencies in `requires` field
- Documents installation instructions
- Validates dependencies before execution

**Example**: A package requiring `python3`, `jq`, `ripgrep`

**Best for**: Specialized tools with specific technology requirements

## Manifest Schema

Every package requires a `manifest.yaml` in its root directory.

### Required Fields

```yaml
name: package-name
version: 1.0.0
description: >
  Brief description of what the package does.
  Can be multi-line for clarity.
author: your-github-handle
license: MIT

artifacts:
  # At least one artifact section required
  commands:
    - commands/my-command.md
  skills:
    - skills/my-skill/SKILL.md
  agents:
    - agents/my-agent.md
  scripts:
    - scripts/my-script.sh
```

### Optional Fields

```yaml
tags:
  - relevant
  - searchable
  - keywords

# Tier 1: Token substitution
variables:
  REPO_NAME:
    auto: git-repo-basename
    description: Repository name used for paths
  CUSTOM_VAR:
    auto: custom-detector
    description: Custom variable explanation

# Future: Install-time options
options:
  option-name:
    type: boolean
    default: false
    description: What this option controls

# Tier 2: Runtime requirements
requires:
  - git >= 2.20
  - python3
  - jq
```

### Field Specifications

**name**: 
- Lowercase with hyphens
- Unique within marketplace
- No spaces or special characters

**version**: 
- Semantic versioning (major.minor.patch)
- Update minor version for new features
- Update patch version for bug fixes
- Update major version for breaking changes

**description**:
- 1-3 sentences explaining purpose
- Focus on user benefits
- Use `>` for multi-line YAML strings

**author**:
- GitHub handle or email
- Used for attribution and contact

**license**:
- MIT recommended for broad compatibility
- Must be compatible with MIT license of repo

**tags**:
- 3-5 relevant keywords
- Help with discoverability
- Examples: git, workflow, ci, testing, automation

**artifacts**:
- List all files to be installed
- Paths relative to package root
- Installer validates these paths exist
- Missing files cause installation failure

**variables** (Tier 1 only):
- Define all `{{VAR}}` tokens used in artifacts
- Specify auto-detection method
- Provide description for manual fallback
- Variables are case-sensitive

**options** (future):
- Boolean flags that modify installation
- Used for conditional features
- Example: `--no-tracking` to disable tracking docs

**requires** (Tier 2 only):
- List external dependencies
- Optionally specify version constraints
- Document installation instructions in README

## Version Management

### Three-Layer Versioning System

Synaptic Canvas uses a three-layer versioning system based on semantic versioning (SemVer):

1. **Marketplace Platform Version** (`version.yaml`) - Infrastructure and CLI
2. **Package Versions** (`manifest.yaml` in each package) - Per-package releases
3. **Artifact Versions** (YAML frontmatter in `.md` files) - Individual commands, skills, and agents

For details, see [Versioning Strategy](docs/versioning-strategy.md).

### Semantic Versioning

All versions follow MAJOR.MINOR.PATCH format:

- **MAJOR (X)**: Breaking changes, major refactoring, incompatible API changes
- **MINOR (Y)**: New features, new agents/commands/skills, backward-compatible improvements
- **PATCH (Z)**: Bug fixes, documentation updates, minor refinements

**Current Status:** All packages at 0.4.0 (beta/pre-release)

### Versioning Your Package

When creating or updating a package:

1. **Set manifest version**:
   ```yaml
   # packages/my-package/manifest.yaml
   name: my-package
   version: 0.4.0  # Must match artifact versions
   ```

2. **Add version frontmatter to ALL artifacts**:
   ```markdown
   ---
   name: /my-command
   description: Description
   version: 0.4.0      # Must match manifest
   ---
   ```

3. **Keep versions synchronized**:
   - All commands in a package → same version as manifest
   - All skills in a package → same version as manifest
   - All agents in a package → same version as manifest
   - Use `python3 scripts/sync-versions.py --package NAME --version X.Y.Z` to bulk update

4. **Document changes**:
   - Create/update `packages/my-package/CHANGELOG.md`
   - Document what changed in each version
   - Include upgrade instructions if breaking changes

### Version Examples

#### Initial Release (Beta)
```yaml
version: 0.4.0  # Release candidate
```

#### Minor Feature Update
```yaml
version: 0.5.0  # New features (backward compatible)
```

#### Bug Fix
```yaml
version: 0.4.1  # Patch release
```

#### Production Ready
```yaml
version: 1.0.0  # First stable release
```

### Version Verification

Before committing, verify all versions are synchronized:

```bash
# Audit all versions
./scripts/audit-versions.sh

# Compare versions by package
./scripts/compare-versions.sh --by-package

# Update versions in bulk
python3 scripts/sync-versions.py --package my-package --version 0.5.0
```

### Releasing a New Version

When ready to release a new version:

1. **Update package version** in `manifest.yaml`
2. **Run sync script** to update all artifacts:
   ```bash
   python3 scripts/sync-versions.py --package my-package --version 0.5.0
   ```
3. **Update CHANGELOG.md** with release notes
4. **Run audit** to verify consistency:
   ```bash
   ./scripts/audit-versions.sh
   ```
5. **Commit with clear message**:
   ```bash
   git commit -m "chore(my-package): release v0.5.0 - add new feature"
   ```
6. **Tag release** (optional):
   ```bash
   git tag v0.5.0
   ```

## Authoring Guidelines

### Command Layer Best Practices

Commands live in `commands/*.md` with YAML frontmatter:

```markdown
---
name: /my-command
description: Brief description of command purpose
options:
  - name: --option-name
    args:
      - name: arg1
        description: What this argument is
    description: What this option does
  - name: --help
    description: Show help information
---

# /my-command

Detailed explanation of command behavior.

## Usage Examples

Show common usage patterns.

## Behavior

Describe what happens when command is invoked.
```

**Guidelines:**
- Keep commands simple; delegate to skills/agents
- Always include `--help` option
- Provide clear examples
- Document all options and arguments
- Explain error conditions
- Keep output concise (no tool traces)

### Skill Layer Best Practices

Skills live in `skills/*/SKILL.md`:

```markdown
---
name: skill-name
description: What this skill helps accomplish
---

# Skill Name

Explain the workflow and patterns.

## Workflows

### Workflow Name
1. Step-by-step instructions
2. Reference agents when appropriate
3. Explain decision points

## Safety and Reminders
- Document safeguards
- Explain approval requirements
```

**Guidelines:**
- Focus on orchestration, not execution
- Reference agents for detailed operations
- Document safety checks and validations
- Explain when to use each workflow
- Provide context for decision-making
- Keep main conversation context clean

### Agent Layer Best Practices

Agents live in `agents/*.md`:

```markdown
---
name: agent-name
description: Specific operation this agent performs
model: sonnet
color: green
---

You are the **Agent Name** agent. Brief role description.

## Inputs (required)
- param1: description
- param2: description

## Rules
- Constraint 1
- Constraint 2

## Steps
1. Detailed step
2. Another step

## Output (structured JSON only)
Return ONLY valid JSON (no markdown fences, no prose):
{
  "action": "operation-type",
  "status": "success|failed",
  "data": {},
  "warnings": [],
  "errors": []
}
```

**Guidelines:**
- Single responsibility per agent
- Structured JSON output only
- No markdown fences in response
- Clear input contract
- Explicit steps and rules
- Document error conditions
- Return warnings for edge cases
- Keep isolated from main context

**Standard Response Schema:**

```json
{
  "action": "create|scan|cleanup|abort|...",
  "status": "success|failed|partial",
  "data": {
    // Operation-specific results
  },
  "warnings": [
    // Non-fatal issues
  ],
  "errors": [
    // Fatal issues that prevented success
  ]
}
```

### Script Layer Best Practices

Scripts live in `scripts/*.sh` or `.py`:

**Shell scripts:**
```bash
#!/usr/bin/env bash
set -euo pipefail

# Brief description
# Usage: script-name.sh --arg value

usage() {
  cat <<'USAGE'
Usage information
USAGE
}

# Parse arguments
# Validate inputs
# Execute operation
# Return clean output
```

**Guidelines:**
- Use `set -euo pipefail` for bash
- Provide usage/help
- Validate all inputs
- Handle errors gracefully
- Return structured output when possible
- Make executable: `chmod +x`
- Document in package README

## Testing Your Package

### Pre-Submission Checklist

- [ ] Package structure follows conventions
- [ ] Manifest validates (run `sc-install.sh info <package>`)
- [ ] All artifact paths exist
- [ ] Token substitution works correctly
- [ ] Commands provide `--help` option
- [ ] Agents return valid JSON
- [ ] Scripts are executable
- [ ] README documents usage
- [ ] License is specified
- [ ] Version follows semver

### Manual Testing

1. **Test Installation**:
```bash
./tools/sc-install.sh install <package> --dest /tmp/test-claude
```

2. **Verify Token Substitution**:
```bash
# Check that {{VAR}} tokens are replaced
grep -r "{{" /tmp/test-claude/<package>/
# Should return no results if all tokens replaced
```

3. **Test Commands**:
```bash
# In a Claude Code session with test installation:
/<command> --help
/<command> <normal-usage>
```

4. **Test Agents** (if applicable):
- Verify JSON output is valid
- Check error handling
- Confirm warnings are reported

5. **Test Uninstall**:
```bash
./tools/sc-install.sh uninstall <package> --dest /tmp/test-claude
```

### Validation Script

Create a test script in your package:

```bash
#!/usr/bin/env bash
# test.sh - Validate package before submission

set -euo pipefail

PACKAGE_NAME="my-package"
MANIFEST="manifest.yaml"

# Check manifest exists
[[ -f "$MANIFEST" ]] || { echo "Missing manifest.yaml"; exit 1; }

# Validate required fields
for field in name version description author license artifacts; do
  grep -q "^${field}:" "$MANIFEST" || { echo "Missing field: $field"; exit 1; }
done

# Check all artifact paths exist
# (parse YAML and verify files)

# Check for {{TOKENS}} in Tier 0 packages
if ! grep -q "^variables:" "$MANIFEST" 2>/dev/null; then
  if grep -r "{{[A-Z_]*}}" commands/ skills/ agents/ 2>/dev/null; then
    echo "Warning: Found tokens but no variables defined"
  fi
fi

echo "✓ Package validation passed"
```

## Submission Process

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR-USERNAME/synaptic-canvas.git
cd synaptic-canvas
```

### 2. Create Package

```bash
mkdir -p packages/my-package/{commands,skills,agents,scripts}
# Create artifacts and manifest
```

### 3. Test Locally

```bash
# Test installation
./tools/sc-install.sh install my-package --dest /tmp/test-claude

# Test usage in Claude Code
# Verify behavior matches documentation
```

### 4. Document

Create `packages/my-package/README.md`:

```markdown
# My Package

Brief description.

## Installation

\`\`\`bash
./tools/sc-install.sh install my-package --dest /path/to/.claude
\`\`\`

## Usage

### Command Examples
\`\`\`
/my-command --option value
\`\`\`

## Configuration

Document any setup or customization.

## Requirements

List dependencies if Tier 2.

## Troubleshooting

Common issues and solutions.
```

### 5. Update Main README

Add entry to package table:

```markdown
| [my-package](packages/my-package/) | Brief description | 0/1/2 |
```

### 6. Create Pull Request

```bash
git checkout -b add-my-package
git add packages/my-package/
git add README.md
git commit -m "Add my-package: brief description"
git push origin add-my-package
```

**PR Description Template:**

```markdown
## Package: my-package

**Tier**: 0 / 1 / 2
**Type**: Command / Skill / Agent / Mixed

### Description
Brief explanation of what the package does.

### Usage Example
\`\`\`
/command --example
\`\`\`

### Testing
- [ ] Installed and tested locally
- [ ] All artifacts validated
- [ ] Token substitution works (if Tier 1)
- [ ] Dependencies documented (if Tier 2)
- [ ] README complete

### Checklist
- [ ] Manifest complete and valid
- [ ] All artifact paths exist
- [ ] Commands provide --help
- [ ] Agents return valid JSON
- [ ] Scripts are executable
- [ ] README documentation
- [ ] Main README updated
```

### 7. Review Process

Maintainers will review for:
- Architecture consistency
- Code quality and safety
- Documentation completeness
- Testing coverage
- Manifest correctness
- License compatibility

## Examples and Patterns
### Example 1: Simple Tier 0 Package

A basic package with no substitution:

```
packages/code-review/
├── manifest.yaml
├── README.md
├── commands/
│   └── review.md
└── skills/
    └── reviewing-code/
        └── SKILL.md
```

**manifest.yaml**:
```yaml
name: code-review
version: 1.0.0
description: Systematic code review with common patterns and checklists
author: contributor-name
license: MIT
tags: [code-quality, review, best-practices]

artifacts:
  commands:
    - commands/review.md
  skills:
    - skills/reviewing-code/SKILL.md
```

### Example 2: Tier 1 with Token Substitution

Package using repository context:

```
packages/ci-status/
├── manifest.yaml
├── commands/
│   └── ci.md          # Uses {{REPO_NAME}}
└── agents/
    └── ci-check.md    # Uses {{REPO_NAME}}
```

**manifest.yaml**:
```yaml
name: ci-status
version: 1.0.0
description: Check CI/CD pipeline status for this repository
author: contributor-name
license: MIT
tags: [ci, github-actions, automation]

artifacts:
  commands:
    - commands/ci.md
  agents:
    - agents/ci-check.md

variables:
  REPO_NAME:
    auto: git-repo-basename
    description: Repository name for CI status checks
```

**commands/ci.md snippet**:
```markdown
Check CI status for {{REPO_NAME}} repository.
```

### Example 3: Tier 2 with Dependencies

Package requiring external tools:

```
packages/image-optimize/
├── manifest.yaml
├── README.md          # Documents imagemagick installation
├── commands/
│   └── optimize.md
└── scripts/
    └── optimize-images.sh
```

**manifest.yaml**:
```yaml
name: image-optimize
version: 1.0.0
description: Optimize images in repository using imagemagick
author: contributor-name
license: MIT
tags: [images, optimization, build-tools]

artifacts:
  commands:
    - commands/optimize.md
  scripts:
    - scripts/optimize-images.sh

requires:
  - imagemagick >= 7.0
  - bash
```

**README.md** should document:
- How to install imagemagick
- Platform-specific instructions
- How to verify installation

### Pattern: Agent with Structured Output

**agents/example-agent.md**:
```markdown
---
name: example-agent
description: Demonstrates standard JSON output pattern
model: sonnet
color: blue
---

You are the **Example** agent. You perform operation X and return structured results.

## Inputs (required)
- target: what to operate on
- mode: operation mode (scan|process|verify)

## Rules
- Validate inputs before processing
- Return errors for invalid inputs
- Include warnings for edge cases
- Never proceed with unsafe operations

## Steps
1. Validate inputs (target exists, mode is valid)
2. Perform operation based on mode
3. Collect results and warnings
4. Return structured JSON

## Output (structured JSON only)
{
  "action": "scan|process|verify",
  "status": "success|failed",
  "data": {
    "target": "processed target",
    "results": []
  },
  "warnings": [
    "Warning message if any"
  ],
  "errors": [
    "Error message if failed"
  ]
}
```

### Pattern: Command with Agent Delegation

**commands/example.md**:
```markdown
---
name: /example
description: Perform operation X using example skill/agent
options:
  - name: --scan
    description: Scan and report without changes
  - name: --process
    args:
      - name: target
        description: What to process
    description: Process the target
  - name: --help
    description: Show this help
---

# /example Command

Delegates to example-agent for actual execution.

## Behavior

### --scan
- Calls example-agent with mode=scan
- Returns structured report
- No modifications made

### --process <target>
- Validates target exists
- Calls example-agent with mode=process
- Reports results

### --help
- Shows this information
```

## Questions and Support

- **Issues**: Open an issue for bugs or questions
- **Discussions**: Use GitHub Discussions for design questions
- **Examples**: Review existing packages for patterns

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
