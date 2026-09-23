# Synaptic Canvas

[![Build Status](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml/badge.svg)](https://github.com/randlee/synaptic-canvas/actions/workflows/tests.yml)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](docs/PUBLISHER-VERIFICATION.md)

**A marketplace for Claude Code skills, agents, and commands.**

Discover and install productivity packages for Claude development workflows. Register once, use across all your projects.

---

## 🚀 Quick Start (10 Seconds)

### Add the Marketplace

```bash
/plugin marketplace add randlee/synaptic-canvas
```

### Browse & Install Packages

```bash
# Browse all packages interactively
/plugin

# Or install directly
/plugin install sc-delay-tasks@synaptic-canvas
```

That's it! Commands, agents, and skills are immediately available in Claude Code.

---

## Alternative: Python CLI (Legacy)

For advanced use cases or automation, the Python CLI is still available:

```bash
# Register marketplace
python3 tools/sc-install.py registry add synaptic-canvas \
  https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json

# Install package
python3 tools/sc-install.py install sc-delay-tasks
```

> **⚠️ Deprecation Notice:** The Python CLI is deprecated and will be removed in v1.0.0. Please use `/plugin` commands.
>
> See [Legacy Installation Guide](docs/LEGACY-INSTALL.md) for details.

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
[![v0.6.0](https://img.shields.io/badge/version-0.6.0-blue)](packages/sc-manage/CHANGELOG.md)
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
[![v0.6.0](https://img.shields.io/badge/version-0.6.0-blue)](packages/sc-repomix-nuget/CHANGELOG.md)
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

### [sc-github-issue](packages/sc-github-issue/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-github-issue/CHANGELOG.md)
[![v0.6.0](https://img.shields.io/badge/version-0.6.0-blue)](packages/sc-github-issue/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-github-issue/LICENSE)

**GitHub issue lifecycle management** — List, create, update issues, and implement fixes in isolated worktrees with automated testing and PR creation.

**Use when you need to:**
- List and browse GitHub issues with filtering
- Create and update issues interactively
- Implement bug fixes in isolated worktrees
- Automate testing, commits, and PR creation
- Maintain clean main working directory during fixes

📖 **[Full README](packages/sc-github-issue/README.md)** | 💡 **[10 Use Cases](packages/sc-github-issue/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-github-issue/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-github-issue/CHANGELOG.md)**

---

### [sc-ai-cli](packages/sc-ai-cli/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-ai-cli/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-ai-cli/CHANGELOG.md)
[![Tier 1](https://img.shields.io/badge/tier-1-yellow)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](../../LICENSE)

**AI-first CLI design toolkit** — Create, review, and harden JSON-first CLIs with MCP-ready contracts, typed error handling, and simulator-backed testing.

**Use when you need to:**
- Design CLIs whose primary contract is machine consumption, not human prose
- Review existing CLIs against AI-first contract standards (JSON, errors, auditability)
- Build stateful simulators for device, service, or database integrations
- Generate scaffolding for Rust, .NET, or Go CLI projects

📖 **[Full README](packages/sc-ai-cli/README.md)** | 💡 **[7 Use Cases](packages/sc-ai-cli/USE-CASES.md)** | 📋 **[Changelog](packages/sc-ai-cli/CHANGELOG.md)**

---

### [sc-ci-automation](packages/sc-ci-automation/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-ci-automation/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-ci-automation/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-ci-automation/LICENSE)

**CI quality gate automation** — Run pull → build → test pipelines with optional auto-fix and PR creation when gates pass.

**Use when you need to:**
- Automate pre-merge quality checks across any project stack
- Run CI pipelines with version bumping and auto-fix
- Coordinate 7 specialized agents for validation, build, test, fix, and PR creation
- Enforce quality gates with configurable warning and failure policies

📖 **[Full README](packages/sc-ci-automation/README.md)** | 💡 **[7 Use Cases](packages/sc-ci-automation/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-ci-automation/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-ci-automation/CHANGELOG.md)**

---

### [sc-codex](packages/sc-codex/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-codex/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-codex/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-codex/LICENSE)

**Task Tool-compatible Codex runner** — Execute Codex agents with hooks emulation and background execution support.

**Use when you need to:**
- Run OpenAI Codex agents as task tools within Claude Code
- Emulate hooks and lifecycle events for Codex sessions
- Execute Codex tasks in the background with structured output
- Integrate Codex into multi-agent workflows with typed contracts

📖 **[Full README](packages/sc-codex/README.md)** | 📋 **[Changelog](packages/sc-codex/CHANGELOG.md)**

---

### [sc-coding-agent-hardening](packages/sc-coding-agent-hardening/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-coding-agent-hardening/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-coding-agent-hardening/CHANGELOG.md)
[![Tier 0](https://img.shields.io/badge/tier-0-green)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-coding-agent-hardening/LICENSE)

**Agent prompt hardening** — Prevent coding, QA, and orchestration agents from dismissing straightforward defects.

**Use when you need to:**
- Stop agents from marking bugs as "minor", "pre-existing", or "technical debt"
- Apply hardening patterns across agent categories (coding, QA, orchestration)
- Rewrite agent system prompts to enforce fix-first behavior
- Map hardening policies to specific repositories and agent types

📖 **[Full README](packages/sc-coding-agent-hardening/README.md)** | 📋 **[Changelog](packages/sc-coding-agent-hardening/CHANGELOG.md)**

---

### [sc-commit-push-pr](packages/sc-commit-push-pr/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-commit-push-pr/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-commit-push-pr/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](../../LICENSE)

**Automated commit, push, and PR creation** — Multi-provider PR workflow with preflight validation for GitHub and Azure DevOps.

**Use when you need to:**
- Automate the commit → push → PR workflow from Claude Code
- Detect git hosting provider (GitHub vs Azure DevOps) automatically
- Run preflight checks before pushing (clean tree, branch validity, auth)
- Create cross-provider PRs with consistent metadata

📖 **[Full README](packages/sc-commit-push-pr/README.md)** | 📋 **[Changelog](packages/sc-commit-push-pr/CHANGELOG.md)**

---

### [sc-just](packages/sc-just/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-just/CHANGELOG.md)
[![v0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](packages/sc-just/CHANGELOG.md)
[![Tier 1](https://img.shields.io/badge/tier-1-yellow)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](../../LICENSE)

**Repo-local just task runners** — Set up curated Justfiles with helper scripts and starter templates for 5 language profiles.

**Use when you need to:**
- Bootstrap a `just` task runner in any repository
- Choose from minimal, Python, Go, .NET, or Rust starter templates
- Get pre-built helpers for fmt, lint, test, and common workflows
- Adapt templates to existing toolchains via `.just/config.toml`

📖 **[Full README](packages/sc-just/README.md)** | 📋 **[Changelog](packages/sc-just/CHANGELOG.md)**

---

### [sc-kanban](packages/sc-kanban/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-kanban/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-kanban/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-kanban/LICENSE)

**Kanban state machine** — Track tasks from backlog to board to done with gate validation, scrubbing, and shared board config.

**Use when you need to:**
- Manage task workflow through backlog → board → done states
- Validate transitions with configurable quality gates
- Scrub and reconcile task state against worktrees and PRs
- Share board configuration across team members

📖 **[Full README](packages/sc-kanban/README.md)** | 💡 **[7 Use Cases](packages/sc-kanban/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-kanban/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-kanban/CHANGELOG.md)**

---

### [sc-launch-term](packages/sc-launch-term/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-launch-term/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-launch-term/CHANGELOG.md)
[![Tier 1](https://img.shields.io/badge/tier-1-yellow)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-launch-term/LICENSE)

**Terminal session launcher** — Launch Claude, Codex, and Gemini in supported terminals with platform-aware autodetect.

**Use when you need to:**
- Launch Claude Code, Codex, or Gemini sessions in the right terminal
- Auto-detect the best terminal emulator on macOS or Windows
- Manage AI coding sessions in tmux with automatic session naming
- Start model-specific sessions (`/sc/sonnet`, `/sc/haiku`, `/sc/opus`, `/sc/codex`, `/sc/gemini`)

📖 **[Full README](packages/sc-launch-term/README.md)** | 📋 **[Changelog](packages/sc-launch-term/CHANGELOG.md)**

---

### [sc-launchpad](packages/sc-launchpad/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-launchpad/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-launchpad/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-launchpad/LICENSE)

**Background sub-agent runtime** — Launch Claude, Codex, or Gemini as separate background agents with ATM teammate-mode normalization.

**Use when you need to:**
- Spawn Claude, Codex, or Gemini as independent background sub-agents
- Register agents in the ATM roster with teammate-mode normalization
- Run parallel agent workflows without blocking the main session
- Coordinate multi-model agent teams with typed task contracts

📖 **[Full README](packages/sc-launchpad/README.md)** | 📋 **[Changelog](packages/sc-launchpad/CHANGELOG.md)**

---

### [sc-roslyn-diff](packages/sc-roslyn-diff/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-roslyn-diff/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-roslyn-diff/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-roslyn-diff/LICENSE)

**Semantic diffing for .NET** — Roslyn-powered diffs with JSON outputs, HTML reports, and git/PR-aware comparisons.

**Use when you need to:**
- Diff C# or VB.NET source semantically, not just textually
- Generate JSON-first diff outputs for machine consumption
- Produce HTML diff reports for human review
- Compare against git history or PR branches with context-aware results

📖 **[Full README](packages/sc-roslyn-diff/README.md)** | 💡 **[7 Use Cases](packages/sc-roslyn-diff/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-roslyn-diff/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-roslyn-diff/CHANGELOG.md)**

---

### [sc-rust](packages/sc-rust/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-rust/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-rust/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](../../LICENSE)

**Rust development toolkit** — Idiomatic guidelines, service hardening, pattern enforcement, and specialized agents for architecture, code review, and QA.

**Use when you need to:**
- Enforce Rust best practices with 11 design pattern modules (typestate, sealed traits, newtype, etc.)
- Harden Rust services for production with tokio, observability, and resilience patterns
- Deploy specialized agents: architect, code reviewer, explorer, developer, QA
- Get cross-platform portability guidance for Ubuntu, macOS, and Windows

📖 **[Full README](packages/sc-rust/README.md)** | 💡 **[7 Use Cases](packages/sc-rust/USE-CASES.md)** | 📋 **[Changelog](packages/sc-rust/CHANGELOG.md)**

---

### [sc-startup](packages/sc-startup/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-startup/CHANGELOG.md)
[![v0.12.0](https://img.shields.io/badge/version-0.12.0-blue)](packages/sc-startup/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](packages/sc-startup/LICENSE)

**Startup runner for Synaptic Canvas** — Sync checklist, triage PRs, verify worktree hygiene, and pull CI on session start.

**Use when you need to:**
- Run a standardized startup routine when beginning a Claude Code session
- Sync the master checklist and surface pending tasks
- Triage open PRs and verify worktree state
- Pull CI changes and emit a concise status with next steps

📖 **[Full README](packages/sc-startup/README.md)** | 💡 **[7 Use Cases](packages/sc-startup/USE-CASES.md)** | 🔧 **[Troubleshooting](packages/sc-startup/TROUBLESHOOTING.md)** | 📋 **[Changelog](packages/sc-startup/CHANGELOG.md)**

---

### [sc-docling-pdf](packages/sc-docling-pdf/)
[![Beta](https://img.shields.io/badge/status-beta-yellow)](packages/sc-docling-pdf/CHANGELOG.md)
[![v0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](packages/sc-docling-pdf/CHANGELOG.md)
[![Tier 2](https://img.shields.io/badge/tier-2-orange)](README.md#-package-tiers-explained)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](../../LICENSE)

**PDF to structured output** — Convert PDFs to markdown, extract images and tables using the docling CLI with content-aware profile selection.

**Use when you need to:**
- Convert PDF documents to clean, structured markdown for LLM consumption
- Extract images, tables, and diagrams as referenced PNG files
- Process scanned documents with OCR (selectable engine and language)
- Handle complex layouts with VLM fallback when standard conversion fails

📖 **[Full README](packages/sc-docling-pdf/README.md)** | 📋 **[Changelog](packages/sc-docling-pdf/CHANGELOG.md)**

---

## 🎯 Find the Right Package

### I want to...

| Goal | Package | Link |
|------|---------|------|
| **Wait before checking if something is ready** | sc-delay-tasks | [Examples](packages/sc-delay-tasks/USE-CASES.md) |
| **Work on multiple branches simultaneously** | sc-git-worktree | [Guide](packages/sc-git-worktree/USE-CASES.md) |
| **Fix GitHub issues in isolated worktrees** | sc-github-issue | [Examples](packages/sc-github-issue/USE-CASES.md) |
| **Analyze a C# project with AI** | sc-repomix-nuget | [Examples](packages/sc-repomix-nuget/USE-CASES.md) |
| **Discover & install packages** | sc-manage | [Guide](packages/sc-manage/USE-CASES.md) |
| **Design an AI-first CLI** | sc-ai-cli | [Examples](packages/sc-ai-cli/USE-CASES.md) |
| **Automate CI quality gates** | sc-ci-automation | [Examples](packages/sc-ci-automation/USE-CASES.md) |
| **Run Codex agents from Claude** | sc-codex | [Readme](packages/sc-codex/README.md) |
| **Harden coding agent prompts** | sc-coding-agent-hardening | [Readme](packages/sc-coding-agent-hardening/README.md) |
| **Automate commit/push/PR workflow** | sc-commit-push-pr | [Readme](packages/sc-commit-push-pr/README.md) |
| **Bootstrap a just task runner** | sc-just | [Readme](packages/sc-just/README.md) |
| **Track tasks on a kanban board** | sc-kanban | [Examples](packages/sc-kanban/USE-CASES.md) |
| **Launch AI coding sessions** | sc-launch-term | [Readme](packages/sc-launch-term/README.md) |
| **Spawn background sub-agents** | sc-launchpad | [Readme](packages/sc-launchpad/README.md) |
| **Diff .NET source semantically** | sc-roslyn-diff | [Examples](packages/sc-roslyn-diff/USE-CASES.md) |
| **Develop idiomatic Rust code** | sc-rust | [Examples](packages/sc-rust/USE-CASES.md) |
| **Run startup checklist on open** | sc-startup | [Examples](packages/sc-startup/USE-CASES.md) |
| **Convert PDF to structured output** | sc-docling-pdf | [Readme](packages/sc-docling-pdf/README.md) |
| **See all available packages** | Any | [Registry](docs/registries/nuget/registry.json) |

---

## 📊 Package Overview

| Package | Type | Status | Version | Tier | Requirements |
|---------|------|--------|---------|------|--------------|
| sc-delay-tasks | Utilities | 🟡 Beta | 0.6.0 | 0 | Python 3.6+ |
| sc-git-worktree | Git Tools | 🟡 Beta | 0.6.0 | 1 | Git 2.27+ |
| sc-manage | Package Mgr | 🟡 Beta | 0.6.0 | 0 | Python 3.6+ |
| sc-repomix-nuget | Analysis | 🟡 Beta | 0.6.0 | 2 | Node 18+, .NET SDK |
| sc-github-issue | GitHub | 🟡 Beta | 0.6.0 | 2 | Git 2.27+, gh CLI 2.0+ |
| sc-ai-cli | CLI Design | 🟡 Beta | 0.12.0 | 1 | None |
| sc-ci-automation | CI/CD | 🟡 Beta | 0.12.0 | 2 | Git 2.20+, gh CLI |
| sc-codex | Agents | 🟡 Beta | 0.12.0 | 2 | Python 3, Codex CLI |
| sc-coding-agent-hardening | Quality | 🟡 Beta | 0.12.0 | 0 | None |
| sc-commit-push-pr | Workflow | 🟡 Beta | 0.12.0 | 2 | Python 3, Git, gh CLI |
| sc-just | Tools | 🟡 Beta | 0.1.0 | 1 | just ≥ 1.0 |
| sc-kanban | Task Mgmt | 🟡 Beta | 0.12.0 | 2 | Python 3, sc-git-worktree |
| sc-launch-term | Launcher | 🟡 Beta | 0.12.0 | 1 | Python 3 |
| sc-launchpad | Agents | 🟡 Beta | 0.12.0 | 2 | Python 3, Claude/Codex/Gemini |
| sc-roslyn-diff | Analysis | 🟡 Beta | 0.12.0 | 2 | .NET 10+, Python 3.10+ |
| sc-rust | Development | 🟡 Beta | 0.12.0 | 2 | Cargo ≥ 1.87 |
| sc-startup | Automation | 🟡 Beta | 0.12.0 | 2 | Git 2.20+, Python 3 |
| sc-docling-pdf | Conversion | 🟡 Beta | 0.1.0 | 2 | docling ≥ 2.90.0 |

**Status:** ✅ Stable (production-ready) | 🟡 Beta (active development) | 🔴 Deprecated (not recommended)

---

## 🔧 Installation Methods

### Method 1: Quick Install (Recommended)
```bash
python3 tools/sc-install.py install PACKAGE_NAME
```
Installs to your user Claude configuration (`~/.claude`). Use this for tools you want everywhere.

### Method 2: Repository-Specific Install
```bash
python3 tools/sc-install.py install PACKAGE_NAME --local
```
Installs to the current repo’s `.claude/` folder. Use this for repo-specific tools.

### Method 3: Custom Destination Install
```bash
python3 tools/sc-install.py install PACKAGE_NAME --dest /path/to/repo/.claude
```
Installs to a specific `.claude/` folder.

### Method 4: Manual Copy
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
- Example: `sc-delay-tasks`
- Setup time: < 1 minute

### Tier 1: Token Substitution
- Auto-replaces variables like `{{REPO_NAME}}`
- Customizes to your project automatically
- Example: `sc-git-worktree`
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
scripts/security-scan.py
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
2. Review a [sample manifest.yaml](packages/sc-delay-tasks/manifest.yaml) — See the format
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
