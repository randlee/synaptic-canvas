# Synaptic Canvas Release Notes Template

**Document Version:** 2.0.0
**Last Updated:** 2025-12-02
**Status:** Comprehensive guide for all package release types

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Template Selection Guide](#template-selection-guide)
4. [Universal Template](#universal-template)
5. [Package-Tier Specific Templates](#package-tier-specific-templates)
6. [Release Type Templates](#release-type-templates)
7. [Markdown Formatting Guidelines](#markdown-formatting-guidelines)
8. [Examples](#examples)
9. [Release Notes Checklist](#release-notes-checklist)

---

## Overview

This document provides standardized templates for creating release notes across all Synaptic Canvas packages. Release notes bridge the gap between technical details (in CHANGELOG.md) and user-friendly communication.

### Key Principles

- **Clarity First**: Write for both technical and non-technical users
- **Scannability**: Use headers, lists, and code blocks for quick reference
- **Actionability**: Provide clear upgrade paths and migration guides
- **Transparency**: Highlight breaking changes prominently
- **Completeness**: Include all necessary information for informed decisions

### Package Tiers

The Synaptic Canvas ecosystem categorizes packages by complexity:

| Tier | Complexity | Dependencies | Characteristics | Examples |
|------|-----------|--------------|-----------------|----------|
| **Tier 0** | Minimal | None or built-in | Self-contained, simple usage | Simple utilities |
| **Tier 1** | Low | Optional variables/tokens | Uses token substitution | `git-worktree` ({{REPO_NAME}}) |
| **Tier 2** | Medium | External dependencies | Requires setup (git, Node, Python) | `delay-tasks`, `sc-repomix-nuget` |

### Installation Scopes

- **Global**: Available system-wide after installation
- **Local**: Repo-specific installation only
- **Local-only**: Can only be installed locally (enforced)

---

## Quick Start

**Choose your path:**

1. **First release?** → [Universal Template](#universal-template)
2. **Know your package tier?** → [Package-Tier Specific Templates](#package-tier-specific-templates)
3. **Know your release type?** → [Release Type Templates](#release-type-templates)
4. **Need formatting help?** → [Markdown Formatting Guidelines](#markdown-formatting-guidelines)

---

## Template Selection Guide

```
START
  |
  +-- Is this a major version bump (0.x.y → 1.0.0)?
  |     YES → Use "Major Release" template + "Migration Guide" section
  |     NO  → Continue
  |
  +-- Is this a minor version bump (0.x.y → 0.x+1.0)?
  |     YES → Use "Minor Release" template
  |     NO  → Use "Patch Release" template (for 0.x.y → 0.x.y+1)
  |
  +-- Package depends on external tools?
  |     YES → Add "Dependencies & Setup" section
  |     NO  → Use base template
  |
  +-- Package uses token substitution (e.g., {{REPO_NAME}})?
  |     YES → Add "Variable Substitution" section
  |     NO  → Skip that section
```

---

## Universal Template

Use this as your foundation for all releases. Fill in all sections; mark as "N/A" if not applicable.

```markdown
# Release Notes: {{PACKAGE_NAME}} v{{VERSION}}

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}
**Installation Scope:** {{global|local|local-only}}

## Executive Summary

<!-- 1-2 paragraphs answering: What is new? Why should users care? -->
<!-- For patch releases: Keep to 1 paragraph about the bug fixes -->
<!-- For minor releases: Highlight 2-3 major improvements -->
<!-- For major releases: Explain the evolution and new capabilities -->

{{Write 1-2 sentences about the release's purpose and main benefit}}

{{Optional: Add 1-2 sentences about who this release is for}}

## What's New

### Features

<!-- List new capabilities added in this release -->

- **Feature Name**: Brief description of what it does and why it matters
  - Use case: When/how users would employ this feature
  - Example: `/command-name --flag value` (for user-facing features)

### Improvements

<!-- Enhancements to existing functionality -->

- **Area**: Description of improvement
  - Previous behavior: What it did before
  - New behavior: What it does now
  - Impact: Why this matters (faster, easier, more reliable, etc.)

### Changes

<!-- Non-breaking modifications to behavior, API, or output -->

- **Changed Behavior**: Description
  - What changed and why
  - No action required unless noted in "Migration Guide"

## Bug Fixes

<!-- What was broken and is now fixed? -->

- Fixed: {{issue description}} ([#123](link-to-issue))
  - Symptom: What users experienced
  - Resolution: How it's fixed
  - Workaround for older versions: (if applicable)

- Fixed: {{another issue}}

<!-- If no bug fixes, write: "No known bug fixes in this release." -->

## Breaking Changes

<!-- ⚠️ CRITICAL: Highlight all breaking changes clearly -->

> ⚠️ **BREAKING CHANGE**: {{description}}
>
> This release introduces changes that may affect existing workflows.
> See "Migration Guide" below for upgrade instructions.

<!-- If no breaking changes, write: "No breaking changes in this release." -->

## Migration Guide

<!-- Only include if there are breaking changes or significant version upgrades -->

### Upgrading from v{{OLD_VERSION}} to v{{NEW_VERSION}}

**Action Required:** Yes | No

#### Step 1: {{First action}}

```bash
# Command or code example
{{command or code}}
```

**Expected output:**
```
{{what user should see}}
```

#### Step 2: {{Next action}}

{{Continue for each step}}

**Validation:**
- [ ] Action 1 completed successfully
- [ ] Action 2 verified
- [ ] Test in staging environment

### Known Compatibility Issues

- **Old Package X with New Package Y**: Description of issue and workaround

<!-- Or: "No known compatibility issues." -->

## Known Issues & Limitations

<!-- What are the current limitations? What doesn't work yet? -->

| Issue | Impact | Workaround | Status |
|-------|--------|-----------|--------|
| {{Issue Name}} | {{Who/what is affected}} | {{How to work around}} | {{planned fix version}} |

<!-- Example: -->
| Minimum polling interval is 60 seconds | High-frequency polling not supported | Use external schedulers for sub-minute intervals | v0.5.0 |

### Temporary Limitations

- **Limitation**: Brief description
  - Planned resolution: {{When/how it will be fixed}}
  - Workaround: {{How to work around it}}

## Dependencies & Setup

<!-- What do users need to install this package? -->

### System Requirements

| Dependency | Version | Required | Purpose |
|-----------|---------|----------|---------|
| {{tool}} | {{version}} | {{Yes/Optional}} | {{What it's used for}} |

### Installation Instructions

**Option A: Global Installation**

```bash
{{installation command}}
```

**Option B: Local Installation (Repository-Specific)**

```bash
{{installation command}}
```

### Verification

After installation, verify setup:

```bash
{{verification command}}
```

Expected output:
```
{{expected result}}
```

### Setup Video/Walkthrough

[Link to video or interactive tutorial] (Optional: embedded or linked)

## Upgrade Instructions

### From v{{PREVIOUS_VERSION}}

**Automatic:**
```bash
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}} --upgrade
```

**Manual:**
```bash
# Step 1: Uninstall old version
python3 tools/sc-install.py uninstall {{PACKAGE_NAME}} --dest {{DEST}}

# Step 2: Install new version
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}} --version {{VERSION}}

# Step 3: Verify
{{verification command}}
```

### Rollback (if needed)

```bash
# Revert to previous version
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}} --version {{PREVIOUS_VERSION}}
```

## Testing Recommendations

### For End Users

- [ ] Install/upgrade in a test environment first
- [ ] Run: `{{basic command}}` to verify installation
- [ ] Try: `{{feature command}}` to test new functionality
- [ ] Compare output with: {{baseline or previous version}}
- [ ] Test edge cases: {{specific scenarios that might break}}

### For Package Maintainers

```bash
# Run test suite
npm test                    # (if Node.js project)
python3 -m pytest          # (if Python project)
./tests/integration.sh     # (if bash project)

# Test across environments
# - Platforms: macOS, Linux, Windows (if applicable)
# - Shell versions: bash 3.x, 4.x, 5.x (if applicable)
# - Versions: Node 16+, Python 3.8+ (if applicable)
```

## Contributors

This release was made possible by:

- {{Contributor Name}} — {{contribution type}} (e.g., "Feature development")
- {{Contributor Name}} — {{contribution type}}

Special thanks to:
- {{Reviewer/tester names}}
- {{Community members who reported issues}}

### How to Contribute

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting features
- Contributing code
- Writing documentation

## Security Advisories

<!-- Include if applicable; otherwise write "None for this release." -->

### CVE Information

- **CVE-XXXX-XXXXX**: {{Description}} — {{link to advisory}}
  - Severity: {{Critical|High|Medium|Low}}
  - Fixed in: {{This version}}
  - Affected versions: {{List versions}}

### Security Recommendations

If you're on {{affected version}}, upgrade immediately:
```bash
{{upgrade command}}
```

### Responsible Disclosure

To report security issues, please:
1. **Do NOT** open a public issue
2. Email: {{security contact email}}
3. Include: {{what to include in report}}
4. Allow {{timeframe}} for response

## Roadmap

### Planned for Next Release (v{{NEXT_VERSION}})

- {{Feature idea}}
- {{Improvement}}
- {{Bug fix category}}

### Longer-Term Vision

- {{Long-term goal 1}}
- {{Long-term goal 2}}

[See full roadmap]({{link to roadmap}})

## Support & Resources

### Getting Help

- **Documentation**: [{{Package}} README](./README.md)
- **Issues**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- **Discussions**: [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
- **Repository**: [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

### Troubleshooting

For common issues, see [Troubleshooting Guide](./TROUBLESHOOTING.md)

### Feedback

We'd love to hear from you:
- Feature requests: [GitHub Issues - Feature Request](https://github.com/randlee/synaptic-canvas/issues/new?labels=enhancement)
- Bug reports: [GitHub Issues - Bug Report](https://github.com/randlee/synaptic-canvas/issues/new?labels=bug)
- General feedback: {{contact method}}

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| {{VERSION}} | {{DATE}} | {{status}} | This release |
| {{PREV_VERSION}} | {{DATE}} | stable | Previous release |

[See full changelog](./CHANGELOG.md)

---

**Generated:** {{CURRENT_DATE}}
**Package Registry:** [docs/registries/nuget/registry.json](../../docs/registries/nuget/registry.json)
```

---

## Package-Tier Specific Templates

### Tier 0: No Dependencies

Use when package has minimal/no external dependencies. Simplify installation and dependencies sections.

```markdown
# Release Notes: {{PACKAGE_NAME}} v{{VERSION}}

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}

## Executive Summary

{{Brief summary}}

## What's New

### Features
- {{Feature 1}}

### Bug Fixes
- {{Fix 1}}

## Installation

```bash
{{Simple single installation command}}
```

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

### Tier 1: Token Substitution

Use when package uses variables like `{{REPO_NAME}}`. Include variable documentation.

```markdown
# Release Notes: {{PACKAGE_NAME}} v{{VERSION}}

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}
**Installation Scope:** {{local-only|local|global}}

## Executive Summary

{{Summary}}

## What's New

### Features
- {{Feature}} with token support

## Variable Substitution

This package uses the following automatic variable substitution:

| Variable | Value | Set By | Example |
|----------|-------|--------|---------|
| `{{REPO_NAME}}` | Your repository name | Git auto-detection | `my-repo-worktrees` |

**How it works:**
- Variables are auto-populated during installation
- For manual override: Edit `.claude/config.json` and update the variables object
- Token format: `{{VARIABLE_NAME}}` (double curly braces)

**Example path resolution:**
```
Project directory: /Users/me/projects/my-awesome-repo
{{REPO_NAME}} expands to: my-awesome-repo
Worktree location: ../my-awesome-repo-worktrees/
```

## Installation

```bash
{{Installation command}}
```

## Troubleshooting

### Variable Expansion Failed

**Symptom:** `{{REPO_NAME}}` appears literally in output (not expanded)

**Causes & Solutions:**
- Not in a git repository: Ensure you're in a valid git repo
- Git not in PATH: Verify git is installed: `which git`
- Repository not initialized: Run: `git init`

**Workaround:** Manually update variables in `.claude/config.json`

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

### Tier 2: External Dependencies

Use for packages requiring external tools (git, Node.js, Python). Emphasize setup.

```markdown
# Release Notes: {{PACKAGE_NAME}} v{{VERSION}}

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}
**Installation Scope:** {{local-only|local|global}}

## Executive Summary

{{Summary}}

## System Requirements

Your system must have the following tools installed:

| Tool | Version | Check Command | Install Link |
|------|---------|---------------|--------------|
| {{tool}} | {{min version}} | `{{check cmd}}` | [Install Guide]({{url}}) |

**Quick Check:**
```bash
node --version     # Should be >= 18
python3 --version  # Should be >= 3.8
git --version      # Should be >= 2.20
```

## What's New

### Features
- {{Feature}}

## Installation

**Before you start:**
1. Install all dependencies (see System Requirements above)
2. Verify each tool is in your PATH

**Step-by-step:**

```bash
# 1. Verify dependencies
node --version

# 2. Install package
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}}

# 3. Verify installation
{{verification command}}
```

## Troubleshooting

### Dependency Not Found

**Problem:** `python3: command not found`

**Solution:**
```bash
# Check if Python is installed
which python3

# If not found, install Python 3.8+:
# macOS: brew install python3
# Linux: sudo apt install python3
# Windows: https://www.python.org/downloads/
```

### Version Too Old

**Problem:** `git version is 2.10.0 but we need >= 2.20`

**Solution:**
```bash
# Check current version
git --version

# Update git:
# macOS: brew upgrade git
# Linux: sudo apt upgrade git
# Windows: https://git-scm.com/download/win
```

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

---

## Release Type Templates

### Minor Release: v0.x.y → v0.(x+1).0

Use for features and improvements (backward compatible).

```markdown
# Release Notes: {{PACKAGE_NAME}} v0.{{X+1}}.0

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}

## Executive Summary

{{PACKAGE_NAME}} v0.{{X+1}}.0 introduces {{number}} major features and {{number}} improvements.
This release is fully backward compatible with v0.{{X}}.0.

**Key highlights:**
- 🎯 {{Feature 1 — one-liner impact}}
- 🚀 {{Feature 2 — one-liner impact}}
- ⚡ {{Improvement 1 — one-liner impact}}

## What's New

### Features

- **{{Feature Name}}**: {{Description}}
  - Use case: {{When to use}}
  - Example: {{Usage example}}

- **{{Feature Name}}**: {{Description}}

### Improvements

- **{{Improvement}}**: {{Description of improvement and impact}}

### Bug Fixes

- Fixed: {{Issue}} ([#123](link))

## Upgrade Instructions

No special steps required. Your existing configuration will continue to work.

```bash
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}} --upgrade
```

All new features are opt-in — existing functionality is unchanged.

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

### Patch Release: v0.x.y → v0.x.(y+1)

Use for bug fixes only (backward compatible, minimal changes).

```markdown
# Release Notes: {{PACKAGE_NAME}} v0.{{X}}.{{Y+1}}

**Release Date:** {{DATE}}
**Status:** {{alpha|beta|stable}}

## Summary

Patch release fixing {{number}} bugs. Fully backward compatible with v0.{{X}}.{{Y}}.

**Fixes:**
- 🐛 {{Bug 1}}
- 🐛 {{Bug 2}}

## Bug Fixes

- **{{Issue Title}}** ([#{{number}}](link)): {{Description}}
  - Symptom: {{What was broken}}
  - Fixed in: This release

- **{{Issue Title}}** ([#{{number}}](link)): {{Description}}

## Upgrade Instructions

This patch release has no breaking changes. Upgrade when convenient:

```bash
python3 tools/sc-install.py install {{PACKAGE_NAME}} --dest {{DEST}} --upgrade
```

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

### Major Release: v0.x.y → v1.0.0

Use for significant changes and API stabilization.

```markdown
# Release Notes: {{PACKAGE_NAME}} v1.0.0

**Release Date:** {{DATE}}
**Status:** stable
**Milestone:** Initial stable release

## Executive Summary

🎉 {{PACKAGE_NAME}} v1.0.0 marks our first stable release with a solidified API,
production-ready features, and full backward compatibility guarantees.

This release represents {{timeframe}} of development and incorporates feedback from
{{number}} beta testers and {{number}} community members.

**What's included:**
- {{Major feature/capability 1}}
- {{Major feature/capability 2}}
- {{Stability improvement}}
- Production-grade documentation

## What's New (Since v0.x.0)

### Major Features

- **{{Feature}}**: {{Description}} [New in v1.0]
- **{{Feature}}**: {{Description}} [New in v1.0]

### Production Improvements

- Enhanced error handling and recovery
- Expanded test coverage ({{percentage}}%)
- Performance optimizations ({{metric}})
- Comprehensive documentation

### Breaking Changes (from v0.x series)

> ⚠️ BREAKING CHANGES — Action required before upgrading

#### Change 1: {{Description}}

**Old API:**
```bash
{{old usage}}
```

**New API:**
```bash
{{new usage}}
```

**Migration:**
See "Migration Guide" section below.

## Migration Guide

### Upgrading from v0.x.0 to v1.0.0

This is a major version bump with breaking changes. Plan for {{estimated time}} to upgrade.

#### Step 1: {{Action}}

{{Details}}

#### Step 2: {{Action}}

{{Details}}

[See full migration guide](#migration-guide)

## API Changes

The v1.0.0 API is now stable. Expect minimal changes going forward.

| Change | Impact | Migration |
|--------|--------|-----------|
| {{Change}} | {{Impact}} | {{How to migrate}} |

## Stability Guarantee

From v1.0.0 onward:
- ✅ Semantic versioning strictly enforced
- ✅ Backward compatibility through major versions
- ✅ Deprecation warnings for future changes (minimum 2 releases notice)
- ✅ Security releases for bugs in current and previous major version
- ✅ LTS consideration for high-adoption versions

[See Versioning Policy](../../CONTRIBUTING.md#versioning-policy)

## Known Issues

| Issue | Status | Workaround |
|-------|--------|-----------|
| {{Known issue}} | Planned for {{version}} | {{Workaround}} |

## Support

- Documentation: [Full Docs](./README.md)
- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Discussions: [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)

---

**Congratulations on upgrading!** Welcome to v1.0.0 🎊
```

---

## Markdown Formatting Guidelines

### Emoji Usage

Use emojis sparingly to improve scannability:

```markdown
🎯 New features (goals achieved)
🚀 Performance improvements (launch/acceleration)
⚡ Speed/efficiency enhancements
🐛 Bug fixes
⚠️  Breaking changes, warnings
✅ Completed, working, approved
❌ Broken, deprecated, removed
🔒 Security improvements
📊 Metrics, data, statistics
🎉 Celebrations, milestones
📝 Documentation updates
🔧 Configuration, setup
🚩 Important notices
💡 Tips, insights, suggestions
```

**Guidelines:**
- Use 1 emoji per bullet point maximum
- Avoid emoji-heavy paragraphs (max 1 per section)
- Never use emoji in code blocks
- Always follow emoji with space and text

### Code Block Styling

```markdown
# Good: Labeled code blocks
$ bash example (command line)
```bash
command --with --flags
```

$ python example
```python
# Python code here
output = function()
```

$ json example
```json
{"key": "value"}
```

# Bad: Unlabeled or misleading blocks
```
some code here without context
```
```

**Guidelines:**
- Always specify language: ` ```bash `, ` ```python `, ` ```json `
- Use `$` prefix for shell commands to show they're runnable
- Show expected output after:
  ```bash
  command
  ```
  Output:
  ```
  result here
  ```
- Keep code blocks under 15 lines (use "..." for truncation)

### Table Formatting

```markdown
# Good: Clear, scannable tables
| Feature | Before | After | Impact |
|---------|--------|-------|--------|
| Speed   | 5s     | 1s    | 80% faster |
| Memory  | 100MB  | 50MB  | 50% reduction |

# Use alignment for readability
| Left-aligned | Center-aligned | Right-aligned |
|:-----|:------:|----------:|
| Text | Middle | 12345     |
```

**Guidelines:**
- Use headers for all columns
- Align data meaningfully (text left, numbers right)
- Keep cells concise (one concept per cell)
- Use max 6 columns (split into multiple tables if needed)

### Link Formatting

```markdown
# Good links
[Link text describes destination](https://example.com)
[See CONTRIBUTING.md](../../CONTRIBUTING.md)
[GitHub Issue #123](https://github.com/randlee/synaptic-canvas/issues/123)

# References in lists
1. Install package
2. Read [getting started guide](./docs/getting-started.md)
3. Report issues [here](https://github.com/randlee/synaptic-canvas/issues)

# Relative links for internal docs
[Changelog](./CHANGELOG.md)
[Troubleshooting](./TROUBLESHOOTING.md)
[Parent folder](../)
```

**Guidelines:**
- Link text should describe where it goes
- Use relative paths for internal links (easier to maintain)
- Use full HTTPS URLs for external links
- Avoid "click here" — be specific

### List Formatting

```markdown
# Good: Hierarchical, scannable lists

- **Topic**: Brief explanation
  - Sub-point with more detail
  - Another sub-point
    - Deep nesting (max 3 levels)

- **Another Topic**: Explanation

# Good: Numbered for procedures
1. Do this first
   - Alternative approach A
   - Alternative approach B
2. Do this second
3. Verify it worked

# Good: Task lists for tracking
- [x] Completed task
- [ ] Pending task
- [ ] Blocked task (see issue #123)

# Bad: Too much nesting or unclear hierarchy
- Item 1
  - Item 1a
    - Item 1a1
      - Item 1a1i (too deep!)
```

**Guidelines:**
- Use unordered (-) for concepts, features, lists of items
- Use ordered (1, 2, 3) for steps and procedures
- Use [ ] for task tracking
- Max nesting depth: 3 levels
- Use **bold** for emphasis on key terms
- Use `code` for commands, file names, variables

---

## Examples

### Good Release Notes Example

```markdown
# Release Notes: delay-tasks v0.5.0

**Release Date:** 2025-12-15
**Status:** beta
**Installation Scope:** Global or Local

## Executive Summary

delay-tasks v0.5.0 introduces dynamic interval adjustment for polling tasks,
allowing workflows to adapt polling frequency based on success patterns. This
release maintains full backward compatibility with v0.4.0.

## What's New

### Features

- **Dynamic Interval Adjustment**: Polling intervals now automatically adjust based on success rate
  - When tasks succeed frequently: Intervals increase (reduces overhead)
  - When tasks fail frequently: Intervals decrease (faster detection)
  - Use case: CI checks that sometimes pass instantly, sometimes take minutes
  - Example: `/delay --poll --adaptive --every 30 --for 5m --action "test"`

- **Enhanced Logging**: New debug mode shows polling progress in real-time
  - Use case: Troubleshooting stuck polling tasks
  - Example: `/delay --poll --debug --every 60 --for 10m --action "deploy"`

### Improvements

- **Performance**: Reduced CPU usage by 40% through smarter polling ([#234](https://github.com/randlee/synaptic-canvas/issues/234))
  - Previous: Constant polling every interval
  - New: Adaptive backoff reduces frequency when no change detected
  - Impact: Lower system load during long polling windows

- **Error Messages**: More descriptive error messages with suggested fixes ([#245](https://github.com/randlee/synaptic-canvas/issues/245))
  - Previous: "Poll timeout"
  - New: "Poll timeout after 5m with 30s intervals. Try: --for 10m or --every 60"

### Bug Fixes

- Fixed: Polling sometimes exits early if signal received ([#239](https://github.com/randlee/synaptic-canvas/issues/239))
  - Symptom: Long polling tasks interrupted by shell signals
  - Resolution: Signal handling improved to gracefully complete current cycle

## Upgrade Instructions

Fully backward compatible. Upgrade when convenient:

```bash
python3 tools/sc-install.py install delay-tasks --dest /Users/<you>/Documents/.claude --upgrade
```

All existing delay commands continue to work without modification.

## Testing Recommendations

For end users:
- [ ] Test existing `/delay` commands still work
- [ ] Try new `--adaptive` flag: `/delay --poll --adaptive --every 30 --for 2m --action "true"`
- [ ] Check debug output: `/delay --poll --debug --every 60 --for 1m --action "echo success"`
- [ ] Compare CPU usage: Run old vs new version during 10-minute polling

## Known Issues

| Issue | Workaround | Planned Fix |
|-------|-----------|------------|
| Adaptive adjustment takes ~30s to activate | Run with slightly longer initial interval | v0.6.0 |
| Debug output only available to terminal | Redirect stderr to see debug output | v0.5.1 |

## Roadmap

**v0.6.0 (Planned February 2026)**
- Persistent task history and statistics
- Webhook notifications on task completion
- Conditional actions (if/then logic)

**v1.0.0 (Planned Q1 2026)**
- Stable API with full backward compatibility guarantee
- Production-grade documentation and examples
- Cron-like scheduling with distributed support

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Discussion: [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)

---

**Version History:**
- 0.5.0 (2025-12-15) — Adaptive polling, enhanced logging
- 0.4.0 (2025-12-02) — Initial beta release
```

### Poor Release Notes Example (What to Avoid)

```markdown
# v0.5.0 Released

New version out!

## Changes

- Stuff fixed
- More features
- Performance improved

## Bugs Fixed

- Issue 234
- Issue 245
- Issue 239

## How to Install

pip install it

## Notes

Thanks to everyone

---
```

**Why this is poor:**

| Problem | Impact | Solution |
|---------|--------|----------|
| No date or status | Users don't know when or what stability level | "2025-12-15 — beta" |
| Vague feature descriptions | Users don't understand benefits | "Dynamic interval adjustment: Polling adapts to success rate" |
| No examples | Users can't try new features | Include commands: `/delay --poll --adaptive` |
| No migration guide | Breaking changes cause confusion | Show old vs new usage |
| No troubleshooting | Users stuck on problems | Include common issues and solutions |
| Minimal context | Technical users confused | Explain the "why" not just "what" |

### Real-World Scenarios

#### Scenario 1: User with git-worktree (Tier 1 - Token Substitution)

**Release:** v0.4.1 (Patch - bug fix)

```markdown
# Release Notes: git-worktree v0.4.1

**Release Date:** 2025-12-08
**Status:** beta
**Installation Scope:** Local-only

## Summary

Patch release fixing an issue where `{{REPO_NAME}}` token failed to expand
in certain git configurations. Fully backward compatible with v0.4.0.

## Bug Fix

- Fixed: Token expansion fails when git repository has non-ASCII characters in name ([#267](github.com/.../issues/267))
  - Symptom: "Token expansion failed: {{REPO_NAME}} — invalid UTF-8"
  - Example: Repository named "café-project" would fail
  - Resolution: UTF-8 handling improved in token expansion

## Upgrade

```bash
python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude --upgrade
```

No action required. Token expansion now handles Unicode characters correctly.

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
```

#### Scenario 2: User with sc-repomix-nuget (Tier 2 - External Dependencies)

**Release:** v0.4.0 (Initial release)

```markdown
# Release Notes: sc-repomix-nuget v0.4.0

**Release Date:** 2025-12-02
**Status:** beta
**Installation Scope:** Local-only

## Executive Summary

sc-repomix-nuget v0.4.0 generates AI-optimized context for C# NuGet packages,
enriching standard Repomix output with NuGet metadata. Perfect for AI code
analysis and LLM-assisted development on .NET projects.

## System Requirements

Before installing, ensure you have:

```bash
node --version     # Requires >= 18.0.0
# macOS: brew install node
# Linux: sudo apt install nodejs npm
# Windows: https://nodejs.org/
```

## What's New

### Features

- **NuGet Context Generation**: Convert C# repositories to compressed XML optimized for AI
  - Use case: Feed code context to ChatGPT, Claude, or other LLMs
  - Example: `/sc-repomix-nuget --generate --output nuget-context.xml`

- **Metadata Enrichment**: Automatically includes dependencies, frameworks, and public API surface
  - Example output: Includes `System.Collections`, `System.Threading` namespaces

- **Registry Integration**: Optional metadata from central package registry
  - Use case: Include additional package context from registry
  - Example: `--registry-url https://raw.githubusercontent.com/.../registry.json`

## Installation

**Step 1: Verify Node.js**

```bash
node --version
# Output: v18.0.0 or higher
```

If missing, install from [nodejs.org](https://nodejs.org/)

**Step 2: Install Package**

```bash
python3 tools/sc-install.py install sc-repomix-nuget --dest /path/to/your-repo/.claude
```

**Step 3: Verify Installation**

```bash
/sc-repomix-nuget --help
# Should show command options
```

## Quick Start

In your C# repository:

```bash
/sc-repomix-nuget --generate --package-path . --output ./nuget-context.xml
```

This creates `nuget-context.xml` (~500KB, compressed) optimized for AI consumption.

## Troubleshooting

### Node.js Not Found

**Error:** `node: command not found`

**Solution:**
```bash
# Check if installed
which node

# Install if missing
brew install node          # macOS
sudo apt install nodejs npm # Linux
# Windows: https://nodejs.org/
```

### Repomix Installation Fails

**Error:** `npx repomix: command not found`

**Solution:**
```bash
# Ensure npm works
npm --version

# Clear npm cache
npm cache clean --force

# Try again
/sc-repomix-nuget --generate
```

## Support

- Issues: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Troubleshooting: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
```

---

## Release Notes Checklist

Use this checklist before publishing release notes:

### Content Completeness

- [ ] **Release Header**: Version, date, status (alpha/beta/stable) clearly visible
- [ ] **Executive Summary**: 1-2 sentences answering "What's new?" and "Why should I care?"
- [ ] **Features Section**: All new features documented with use cases
- [ ] **Improvements Section**: All enhancements with before/after comparison
- [ ] **Bug Fixes**: All fixed issues with references to GitHub issues
- [ ] **Breaking Changes**: Clearly highlighted with warning indicator (⚠️)
- [ ] **Migration Guide**: Included if breaking changes exist
- [ ] **Known Issues**: Any limitations or workarounds documented
- [ ] **Dependencies**: System requirements clearly listed with version constraints
- [ ] **Installation Instructions**: Step-by-step with verification
- [ ] **Upgrade Instructions**: Automatic and manual paths provided
- [ ] **Support Resources**: Links to issues, docs, discussions
- [ ] **Roadmap**: Next planned releases mentioned (optional but recommended)

### Technical Accuracy

- [ ] **Version Numbers**: Match semantic versioning (X.Y.Z)
- [ ] **Commands Tested**: All example commands actually work
- [ ] **Links Valid**: All GitHub issues, docs links are active
- [ ] **Code Examples**: Syntax is correct and copy-paste ready
- [ ] **Compatibility**: Stated compatibility matches actual behavior
- [ ] **Dependencies**: Minimum versions accurate and tested
- [ ] **File Paths**: Relative and absolute paths correct

### Formatting & Style

- [ ] **Markdown Valid**: No syntax errors (headers, lists, code blocks)
- [ ] **Emoji Appropriate**: Used sparingly and consistently
- [ ] **Tables Readable**: Proper alignment and clear headers
- [ ] **Lists Hierarchical**: Max 3 levels nesting, clear structure
- [ ] **Code Blocks**: Language specified, output shown for commands
- [ ] **Links Descriptive**: Link text explains destination
- [ ] **Headings Clear**: Consistent hierarchy (H1, H2, H3)
- [ ] **Grammar/Spelling**: Professional language, no typos

### User Experience

- [ ] **Target Audience Clear**: Written for both technical and non-technical users
- [ ] **Scannability**: Can read in 5 minutes with headers/bullets/tables
- [ ] **Actionability**: Users know what to do after reading
- [ ] **Example Usage**: Real commands users can copy and run
- [ ] **Troubleshooting**: Common issues and solutions included
- [ ] **Warning Prominent**: Breaking changes hard to miss
- [ ] **Encouragement**: Positive tone, celebrates improvements

### Organization & Context

- [ ] **Date Correct**: Release date accurate
- [ ] **Scope Clear**: Global/Local/Local-only clearly stated
- [ ] **Changelog Referenced**: Link to CHANGELOG.md
- [ ] **Version History**: Table of recent versions
- [ ] **Contributors Listed**: Who worked on this release
- [ ] **Context Complete**: No orphaned references or placeholder text ({{VARIABLES}} replaced)

### Pre-Release Review

- [ ] **Reviewed by Maintainer**: Accuracy verified
- [ ] **Reviewed by User**: Non-technical person can understand
- [ ] **Tested Release Instructions**: Followed and verified
- [ ] **Tested Upgrade Instructions**: From previous version works
- [ ] **Links Double-Checked**: No 404s or redirect issues
- [ ] **Cross-Referenced**: Matches CHANGELOG.md entries
- [ ] **Performance Verified**: Code examples don't take >10s to run

### Final Approval

- [ ] **Ready for Publishing**: All checks passed
- [ ] **Approved By**: (maintainer name)
- [ ] **Published Date**: (actual publication date)
- [ ] **Announcement Made**: Posted to Discussions/Twitter/etc
- [ ] **Archive Created**: Saved for record

---

## Templates by Package

Quick reference for finding the right template for each package:

### delay-tasks (Tier 2)
- External dependencies: Python 3, Bash
- Installation scopes: Global or Local
- Use: [Tier 2 Template](#tier-2-external-dependencies) + [Universal Template](#universal-template)
- Example scenario: Polling, scheduling, CI delays

### git-worktree (Tier 1)
- Token substitution: `{{REPO_NAME}}`
- Installation scopes: Local-only (enforced)
- Use: [Tier 1 Template](#tier-1-token-substitution) + [Universal Template](#universal-template)
- Example scenario: Worktree management, branch handling

### sc-manage (Tier 2)
- External dependencies: Python 3, Git
- Installation scopes: Global (recommended)
- Use: [Tier 2 Template](#tier-2-external-dependencies) + [Universal Template](#universal-template)
- Example scenario: Package management, installation, listing

### sc-repomix-nuget (Tier 2)
- External dependencies: Node.js >= 18, Bash
- Installation scopes: Local-only
- Use: [Tier 2 Template](#tier-2-external-dependencies) + [Universal Template](#universal-template)
- Example scenario: C# context generation, NuGet metadata

---

## Common Pitfalls & Solutions

### Pitfall 1: Too Technical

**Problem:** "Refactored async polling loop with exponential backoff algorithm"

**Solution:** "Reduced CPU usage during polling by 40% through smarter interval adjustment"

### Pitfall 2: Too Vague

**Problem:** "Various improvements and fixes"

**Solution:** "Fixed timeout handling in polling tasks and added detailed error messages"

### Pitfall 3: Unclear Breaking Changes

**Problem:** "API updated" (buried in middle of document)

**Solution:** Top-level section with ⚠️ warning and migration guide

### Pitfall 4: No Examples

**Problem:** "New filtering capability for advanced users"

**Solution:** `/delay --poll --filter "success_rate > 80%" --adaptive`

### Pitfall 5: Missing Context

**Problem:** "Upgraded from v0.3.0" (but v0.3.0 wasn't released)

**Solution:** "Upgraded from v0.4.0 to v0.5.0" + link to v0.4.0 release notes

### Pitfall 6: Unclear Upgrade Path

**Problem:** "Now requires Python 3.9+ (previously 3.8)"

**Solution:**
```
System Requirement Change:
- Before: Python 3.8+
- After: Python 3.9+
- Check: python3 --version
- Action: Upgrade Python if needed before installing v0.5.0
```

---

## Release Notes in the Registry

When publishing to the registry (`docs/registries/nuget/registry.json`), ensure:

```json
{
  "name": "package-name",
  "version": "X.Y.Z",
  "status": "beta|stable|alpha",
  "changelog": "https://raw.githubusercontent.com/randlee/synaptic-canvas/main/packages/package-name/CHANGELOG.md",
  "lastUpdated": "2025-12-02"
}
```

The registry metadata points to:
1. **CHANGELOG.md** - Detailed change history (Keep a Changelog format)
2. **RELEASE-NOTES.md** (optional) - User-friendly summary in your package directory
3. **README.md** - Installation and usage guide

---

## Additional Resources

- [Keep a Changelog](https://keepachangelog.com/) — Format for CHANGELOG.md
- [Semantic Versioning](https://semver.org/) — Version numbering guide
- [GitHub Release Notes Guide](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)
- [Markdown Cheatsheet](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
- [SPDX License List](https://spdx.org/licenses/) — License identifiers

---

## Questions & Feedback

Found an issue with this template or have suggestions?

- Open an issue: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Start discussion: [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
- Email: {{contact email}} (optional)

---

**Document Information:**
- **Version:** 2.0.0
- **Last Updated:** 2025-12-02
- **Maintained By:** Synaptic Canvas Team
- **License:** MIT (same as project)
- **Compatible With:** All Synaptic Canvas packages v0.4.0+
