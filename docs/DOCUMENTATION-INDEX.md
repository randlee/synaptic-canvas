# Synaptic Canvas Documentation Index

**Last Updated:** December 16, 2025
**Status:** Active Project
**Version:** 0.6.0 (Beta)

This is the central hub for all Synaptic Canvas documentation. Use this index to navigate to the specific information you need.

---

## Quick Navigation

### For New Users
- **[Getting Started](../README.md)** - Project overview and quick start guide
- **[Installation Guide](../README.md#installation)** - How to install Synaptic Canvas
- **[Quick Examples](../README.md#quick-examples)** - Common usage patterns

### For Package Maintainers
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines and development setup
- **[Versioning Strategy](./versioning-strategy.md)** - Version management and release process
- **[Architecture Guidelines](./claude-code-skills-agents-guidelines-0.4.md)** - Best practices for agents/skills/commands

### For Registry Operators
- **[Marketplace Infrastructure Guide](./MARKETPLACE-INFRASTRUCTURE.md)** - Complete guide to creating and operating Claude Code marketplaces
- **[Registry Schema](./registries/nuget/registry.json)** - Central package registry
- **[Registry Documentation](./registries/README.md)** - Registry structure and usage

---

## Core Documentation

### Project Overview
| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](../README.md) | Project overview, key features, quick start | Everyone |
| [WARP.md](../WARP.md) | Warp terminal integration and startup | Terminal users |

### Development Documentation
| Document | Purpose | Audience |
|----------|---------|----------|
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines, dev setup, code standards | Contributors |
| [Versioning Strategy](./versioning-strategy.md) | Three-layer versioning system, SemVer policy | Maintainers |
| [Architecture Guidelines](./claude-code-skills-agents-guidelines-0.4.md) | Best practices for agents, skills, commands | Developers |

### Tools and Infrastructure
| Document | Purpose | Location |
|----------|---------|----------|
| [Marketplace Infrastructure](./MARKETPLACE-INFRASTRUCTURE.md) | Complete guide to building and operating Claude Code marketplaces | `docs/MARKETPLACE-INFRASTRUCTURE.md` |
| [Agent Runner Quick Ref](./agent-runner.md) | Quick reference for Agent Runner | `docs/agent-runner.md` |
| [Agent Runner Comprehensive](./agent-runner-comprehensive.md) | Complete guide: features, benefits, integration | `docs/agent-runner-comprehensive.md` |
| [NuGet Integration](./nuget/) | NuGet-specific documentation | `docs/nuget/` |
| [Registry Metadata](./registries/nuget/) | Package registry and discovery | `docs/registries/nuget/` |

---

## Packages Documentation

Each package in `packages/*/` maintains its own documentation:

### Available Packages

| Package | Version | Purpose | Key Files |
|---------|---------|---------|-----------|
| **sc-delay-tasks** | 0.4.0 | Delayed/polled task execution | [README](../packages/sc-delay-tasks/README.md) |
| **sc-git-worktree** | 0.4.0 | Git worktree management | [README](../packages/sc-git-worktree/README.md) |
| **sc-manage** | 0.4.0 | Synaptic Canvas package manager | [README](../packages/sc-manage/README.md) |
| **sc-repomix-nuget** | 0.4.0 | NuGet context generation | [README](../packages/sc-repomix-nuget/README.md) |
| **sc-roslyn-diff** | 0.7.0 | Semantic .NET diffs with roslyn-diff | [README](../packages/sc-roslyn-diff/README.md) |

**→ See each package's README.md for details on usage, features, and skills**

---

## Version Management

### Current Versions

- **Marketplace Platform:** 0.4.0 (Beta) — See `version.yaml`
- **All Packages:** 0.4.0 (Beta) — Synchronized for marketplace consistency

### Version Tracking

- [Versioning Strategy](./versioning-strategy.md) - Complete versioning policy
- [Version Audit Script](../scripts/audit-versions.py) - Verify version consistency
- [Version Sync Script](../scripts/sync-versions.py) - Update versions bulk
- [Version Compare Tool](.python3 scripts/compare-versions.py) - Show versions by package

### Changelog Files

- **Marketplace:** `CHANGELOG.md` (at repo root) - Platform release history
- **Packages:** `packages/*/CHANGELOG.md` - Per-package release history (coming soon)

---

## Scripts and Tools

### Version Management Scripts

Located in `scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `audit-versions.py` | Verify version consistency across all artifacts | `./scripts/audit-versions.py` |
| `sync-versions.py` | Bulk update versions in packages | `python3 scripts/sync-versions.py --package NAME --version X.Y.Z` |
| `compare-versions.py` | Compare versions by package | `python3 scripts/compare-versions.py --by-package` |

### Validation Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `validate-agents.py` | Validate agent frontmatter | `scripts/validate-agents.py` |

---

## Architecture

### Directory Structure

```
synaptic-canvas/
├── docs/                          # Documentation hub
│   ├── DOCUMENTATION-INDEX.md     # This file
│   ├── versioning-strategy.md     # Versioning policy
│   ├── registries/                # Registry metadata
│   ├── nuget/                     # NuGet integration docs
│   └── ...
├── packages/                      # Installable packages
│   ├── sc-delay-tasks/               # Package 1
│   ├── sc-git-worktree/              # Package 2
│   ├── sc-manage/                 # Package 3
│   └── sc-repomix-nuget/             # Package 4
├── scripts/                       # Utility scripts
│   ├── audit-versions.py
│   ├── sync-versions.py
│   ├── compare-versions.py
│   └── ...
├── .claude/                       # Claude Code configuration
│   ├── commands/                  # Global commands
│   ├── skills/                    # Global skills
│   ├── agents/                    # Global agents
│   └── scripts/                   # Global helper scripts
├── .archive/                      # Historical/deprecated docs
│   ├── docs/                      # Old documentation
│   └── versioned-docs/            # Historical versions
└── version.yaml                   # Marketplace platform version
```

### Three-Layer Versioning

The project uses three synchronized version layers:

1. **Marketplace Version** (`version.yaml`) - Platform/CLI infrastructure
2. **Package Versions** (`packages/*/manifest.yaml`) - Per-package releases
3. **Artifact Versions** (frontmatter in `.md` files) - Individual components

→ See [Versioning Strategy](./versioning-strategy.md) for details

---

## Common Tasks

### For Developers

**Installing a package:**
```bash
python3 tools/sc-install.py install sc-delay-tasks --local
```

**Checking version consistency:**
```bash
./scripts/audit-versions.py
```

**Updating package version:**
```bash
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.5.0
```

**Running tests:**
```bash
pytest -q
```

### For Contributors

**Setting up development environment:**
1. See [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Create a feature branch: `git worktree create feature/branch-name`
3. Make changes and test
4. Submit PR against `main`

**Adding a new package:**
1. Create `packages/new-package/`
2. Add `manifest.yaml` with version field
3. Create `commands/`, `skills/`, `agents/` as needed
4. Update this index with package info
5. Add CHANGELOG.md
6. Commit and test installation

### For Maintainers

**Releasing a new version:**
1. Update package version in `packages/*/manifest.yaml`
2. Run `python3 scripts/sync-versions.py --package name --version X.Y.Z`
3. Update `packages/*/CHANGELOG.md`
4. Run `./scripts/audit-versions.py` to verify
5. Commit with clear message
6. Create git tag: `git tag v0.5.0`

---

## Related Resources

### External Documentation

- **Claude Code** - Official Claude Code documentation (`.claude/` commands)
- **Claude Agent SDK** - Agent development reference
- **Git Worktrees** - Git documentation on worktree functionality

### Community

- **Issues** - GitHub Issues for bug reports and features
- **Discussions** - GitHub Discussions for questions and ideas
- **Contributing** - See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Documentation Maintenance

### Archival Policy

Old or deprecated documentation is moved to `.archive/`:

- **When to Archive:**
  - Documents superseded by newer versions
  - Deprecated guides or outdated patterns
  - Old versions of evolving documents

- **How to Archive:**
  1. Move to `.archive/` appropriate subdirectory
  2. Update this index with note
  3. Add cross-reference in current docs linking to archived version
  4. Commit with clear archival message

See [.archive/README.md](../.archive/README.md) for full archival details.

### Version Control

This documentation is versioned alongside the marketplace platform:
- Changes to docs trigger versioning audit in CI/CD
- Major doc revisions should correspond to version bumps
- See [Versioning Strategy](./versioning-strategy.md) for policy

---

## Quick Help

**Can't find what you're looking for?**

1. **Search this index** for keywords
2. **Check [CONTRIBUTING.md](../CONTRIBUTING.md)** for development questions
3. **Review package READMEs** in `packages/*/`
4. **Look in [.archive/](../.archive/)** for historical information
5. **Check GitHub Issues** for known problems

**Want to contribute documentation?**

1. Read [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Edit relevant documentation files
3. Ensure consistency with this index
4. Submit PR with clear description

---

## Document Status

| Section | Status | Last Updated |
|---------|--------|--------------|
| Project Overview | ✅ Current | Nov 30, 2025 |
| Development Setup | ✅ Current | Nov 30, 2025 |
| Versioning System | ✅ Current | Dec 2, 2025 |
| Package Documentation | ✅ Current | Dec 1, 2025 |
| Archive Structure | ✅ Current | Dec 2, 2025 |
| Tools & Scripts | ✅ Current | Dec 2, 2025 |
| Marketplace Infrastructure | ✅ Current | Dec 16, 2025 |

---

**See something outdated?** Please open an issue or submit a PR to keep documentation current!
