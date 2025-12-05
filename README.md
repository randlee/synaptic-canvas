# Synaptic Canvas

[![Build Status](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml/badge.svg)](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](docs/PUBLISHER-VERIFICATION.md)

**A marketplace for Claude Code skills, agents, and commands.**

Discover and install productivity packages for Claude development workflows. Register once, use across all your projects.

---

## 🚀 Quick Start (30 Seconds)

### Step 1: Register the Marketplace

Run once on any computer to add Synaptic Canvas:

```bash
python3 tools/sc-install.py registry add synaptic-canvas \
  https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json
```

### Step 2: Discover Available Packages

```bash
python3 tools/sc-install.py list
```

### Step 3: Install a Package

```bash
# Quick install (recommended)
python3 tools/sc-install.py install sc-delay-tasks

# Or specify destination for repo-specific setup
python3 tools/sc-install.py install sc-git-worktree --dest /path/to/repo/.claude
```

> **💡 Tip:** Need help? Run `scripts/security-scan.sh` to diagnose installation issues.

---

## 📦 Available Packages

### [sc-delay-tasks](packages/sc-delay-tasks/)
[![Stable](https://img.shields.io/badge/status-stable-green)](packages/sc-delay-tasks/CHANGELOG.md)
[![v1.0.0](https://img.shields.io/badge/version-1.0.0-blue)](packages/sc-delay-tasks/CHANGELOG.md)
[![Tier 0](https://img.shields.io/badge/tier-0-green)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-delay-tasks/LICENSE)

**Polling and delay utilities** — Wait for conditions and check on intervals with minimal overhead.

**Use when you need to:**
- Delay execution before running checks (perfect for CI/CD pipelines)
- Poll on bounded intervals for external system readiness
- Wait for GitHub Actions, PR reviews, or deployment completion

📖 **[Full README](packages/sc-delay-tasks/README.md)** | 💡 **[7 Use Cases](packages/sc-delay-tasks/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-delay-tasks/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-delay-tasks/CHANGELOG.md)**

---

### [sc-git-worktree](packages/sc-git-worktree/)
[![Stable](https://img.shields.io/badge/status-stable-green)](packages/sc-git-worktree/CHANGELOG.md)
[![v1.0.0](https://img.shields.io/badge/version-1.0.0-blue)](packages/sc-git-worktree/CHANGELOG.md)
[![Tier 1](https://img.shields.io/badge/tier-1-yellow)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-git-worktree/LICENSE)

**Git worktree management** — Manage parallel development with automatic tracking and safety checks.

**Use when you need to:**
- Work on multiple branches simultaneously without context switching
- Isolate experiments in separate worktrees for safety
- Track worktree state across your team
- Clean up old worktrees with built-in safety checks

📖 **[Full README](packages/sc-git-worktree/README.md)** | 💡 **[7 Use Cases](packages/sc-git-worktree/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-git-worktree/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-git-worktree/CHANGELOG.md)**

---

### [sc-manage](packages/sc-manage/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-manage/CHANGELOG.md)
[![v0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](packages/sc-manage/CHANGELOG.md)
[![Tier 0](https://img.shields.io/badge/tier-0-green)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-manage/LICENSE)

**Package management** — Discover, install, and manage Synaptic Canvas packages.

**Use when you need to:**
- Discover packages available in the marketplace registry
- List installed packages and check their versions
- Install packages globally or locally in specific repos
- Check package compatibility with your environment

📖 **[Full README](packages/sc-manage/README.md)** | 💡 **[7 Use Cases](packages/sc-manage/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-manage/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-manage/CHANGELOG.md)**

---

### [sc-repomix-nuget](packages/sc-repomix-nuget/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-repomix-nuget/CHANGELOG.md)
[![v0.4.0](https://img.shields.io/badge/version-0.4.0-blue)](packages/sc-repomix-nuget/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-repomix-nuget/LICENSE)

**NuGet & C# analysis** — Generate AI-ready context from .NET projects for code review and documentation.

**Use when you need to:**
- Analyze .NET/NuGet projects with AI assistance
- Generate documentation from C# code automatically
- Check framework and dependency compatibility
- Create AI-ready context from large codebases

📖 **[Full README](packages/sc-repomix-nuget/README.md)** | 💡 **[7 Use Cases](packages/sc-repomix-nuget/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-repomix-nuget/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-repomix-nuget/CHANGELOG.md)**

---

## 🎯 Find the Right Package

### I want to...

| Goal | Package | Link |
|------|---------|------|
| **Wait before checking if something is ready** | sc-delay-tasks | [Examples](packages/sc-delay-tasks/USE-CASES.md) |
| **Work on multiple branches simultaneously** | sc-git-worktree | [Guide](packages/sc-git-worktree/USE-CASES.md) |
| **Analyze a C# project with AI** | sc-repomix-nuget | [Examples](packages/sc-repomix-nuget/USE-CASES.md) |
| **Discover & install packages** | sc-manage | [Guide](packages/sc-manage/USE-CASES.md) |
| **See all available packages** | Any | [Registry](docs/registries/nuget/registry.json) |

---

## 📊 Package Overview

| Package | Type | Status | Version | Tier | Requirements |
|---------|------|--------|---------|------|--------------|
| delay-tasks | Utilities | ✅ Stable | 1.0.0 | 0 | Python 3.6+ |
| git-worktree | Git Tools | ✅ Stable | 1.0.0 | 1 | Git 2.7.0+ |
| sc-manage | Package Mgr | 🟡 Beta | 0.4.0 | 0 | Python 3.6+ |
| sc-repomix-nuget | Analysis | 🟡 Beta | 0.4.0 | 2 | Node 18+, .NET SDK |

**Status:** ✅ Stable (production-ready) | 🟡 Beta (active development) | 🔴 Deprecated (not recommended)

---

## 🔧 Installation Methods

### Method 1: Quick Install (Recommended)
```bash
python3 tools/sc-install.py install PACKAGE_NAME
```
Installs to your global Claude configuration. Use this for tools you want everywhere.

### Method 2: Repository-Specific Install
```bash
python3 tools/sc-install.py install PACKAGE_NAME --dest /path/to/repo/.claude
```
Installs to a specific repository's `.claude/` folder. Use this for repo-specific tools.

### Method 3: Manual Copy
1. Clone or download the package folder
2. Copy contents to your project's `.claude/` directory
3. If Tier 1: Replace `{{REPO_NAME}}` tokens with your repository name
4. If Tier 2: Verify all dependencies are installed

---

## 📚 Documentation

### For Users
- **[Getting Started Guide](docs/DOCUMENTATION-INDEX.md)** — Complete introduction
- **[Use Cases by Package](packages/sc-delay-tasks/USE-CASES.md)** — Real-world examples (28 total)
- **[Troubleshooting Guide](docs/DIAGNOSTIC-TOOLS.md)** — Common issues and solutions
- **[Installation Help](docs/DEPENDENCY-VALIDATION.md)** — Dependencies and requirements
- **[Diagnostic Tools](docs/DIAGNOSTIC-TOOLS.md)** — Debug installation and version issues

### For Contributors
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to create and submit packages
- **[Versioning Strategy](docs/versioning-strategy.md)** — How versions work across layers
- **[Release Process](docs/RELEASE-PROCESS.md)** — How packages are released
- **[Package Manifest Guide](docs/version-compatibility-matrix.md)** — manifest.yaml format

### For Security-Conscious Users
- **[Security Policy](SECURITY.md)** — Our security commitment and practices
- **[Publisher Verification](docs/PUBLISHER-VERIFICATION.md)** — How we verify publishers
- **[Dependency Information](docs/DEPENDENCY-VALIDATION.md)** — All package requirements
- **[Security Scanning](docs/SECURITY-SCANNING-GUIDE.md)** — How we scan for vulnerabilities

---

## 🔒 Security & Trust

Every package in Synaptic Canvas is:

✅ **Publisher Verified** — Published by verified GitHub organization
✅ **Security Scanned** — Automated vulnerability checks on every release
✅ **Dependency Audited** — All requirements documented and tracked
✅ **Openly Licensed** — MIT licensed, full source available
✅ **Actively Maintained** — Regular updates and community support

[Learn more about our security practices →](SECURITY.md)

---

## 🧭 Package Tiers Explained

### Tier 0: Direct Copy
- No setup or substitution needed
- Ready to use immediately
- Example: `delay-tasks`
- Setup time: < 1 minute

### Tier 1: Token Substitution
- Auto-replaces variables like `{{REPO_NAME}}`
- Customizes to your project automatically
- Example: `git-worktree`
- Setup time: 1-2 minutes

### Tier 2: Runtime Dependencies
- Requires external tools (Python, Node, .NET SDK, etc.)
- Most powerful capabilities
- Example: `sc-repomix-nuget`
- Setup time: 5-10 minutes (depends on your environment)

---

## 🚨 Troubleshooting

### "python3 not found"
You need Python 3.6 or later. See [Dependency Guide](docs/DEPENDENCY-VALIDATION.md) for installation instructions.

### "Package not found in registry"
Make sure you've registered the marketplace first:
```bash
python3 tools/sc-install.py registry add synaptic-canvas \
  https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json
```

### "Installation failed with permission error"
Try installing to a specific repository instead of globally:
```bash
python3 tools/sc-install.py install PACKAGE --dest /path/to/repo/.claude
```

### "Can't find diagnostic info"
Run the diagnostic tool:
```bash
scripts/security-scan.sh
```

### More help needed?
→ See [Complete Troubleshooting Guide](docs/TROUBLESHOOTING.md)
→ See [Diagnostic Tools](docs/DIAGNOSTIC-TOOLS.md)
→ Check [Package-Specific Guides](packages/sc-delay-tasks/TROUBLESHOOTING.md)

---

## 🏗️ Creating Your Own Package

Want to contribute a new package to the marketplace? We'd love to have it!

### Getting Started
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) — Complete package authoring guide
2. Review a [sample manifest.yaml](packages/delay-tasks/manifest.yaml) — See the format
3. Check [Package Manifest Guide](docs/version-compatibility-matrix.md) — Field reference
4. Look at [existing packages](packages/) — Use as templates

### Package Checklist
- [ ] Create `manifest.yaml` with package metadata
- [ ] Write commands, skills, and agents in `.claude/`
- [ ] Create comprehensive `README.md` with examples
- [ ] Add `USE-CASES.md` with real workflows (7+ scenarios)
- [ ] Include `TROUBLESHOOTING.md` with common issues
- [ ] Create `CHANGELOG.md` documenting all versions
- [ ] Test on Windows, macOS, and Linux
- [ ] Open a pull request to contribute

---

## 💬 Support & Community

- 🐛 **Found a bug?** → [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- 💡 **Have an idea?** → [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
- 📖 **Need help?** → See [Troubleshooting](README.md#-troubleshooting) above
- 🔒 **Security concern?** → See [SECURITY.md](SECURITY.md)
- 🤝 **Want to contribute?** → See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT — See [LICENSE](LICENSE) for details

---

## 📚 Full Documentation

[Complete documentation index with all guides and references →](docs/DOCUMENTATION-INDEX.md)
