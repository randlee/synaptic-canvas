# Changelog

All notable changes to the **sc-manage** package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Package dependency resolution and auto-installation
- Search and filter capabilities for package discovery
- Performance optimization for large package registries
- Package update notifications and version checking
- Integration with package registry webhooks for real-time updates

## [0.7.0] - 2025-12-21

### Changed
- Version synchronized with marketplace v0.7.0 release
- Part of coordinated marketplace release

### Notes
- No functional changes from v0.6.0
- Synchronized versioning for consistency across all packages

## [0.4.0] - 2025-12-02

### Status
Beta release - initial v0.x publication. Recommended for global installation.

### Added
- **sc-packages-list** agent: Discover and list all available Synaptic Canvas packages
  - Display package names, versions, and descriptions
  - Show installation status: none / local-only / global / both scopes
  - Filter by tag or search criteria
  - Respect package installation policies
- **sc-package-install** agent: Install packages into local/project or global/user scopes
  - Enforce package scope policies (e.g., sc-git-worktree is local-only)
  - Automatic token substitution for Tier 1 packages ({{REPO_NAME}}, etc.)
  - Validate prerequisites before installation
  - Provide installation summary and next steps
- **sc-package-uninstall** agent: Remove packages from specified scope
  - Safe removal with optional backup/rollback capability
  - Respect installation policy constraints
  - Clear status messages and error reporting
  - Cleanup of temporary or conflicting files
- **sc-package-docs** agent: Preview package documentation and ask questions
  - Display README and related documentation files
  - Interactive Q&A interface for package-specific questions
  - Provide getting started guides and examples
  - Link to full documentation and issue tracker
- `/sc-manage` command: User-facing command for package management
  - `--list`: Show all packages and their installation status
- `--install <package> --local|--project|--global|--user`: Install a package
- `--uninstall <package> --local|--project|--global|--user`: Uninstall a package
  - `--docs <package>`: Preview and ask questions about a package
- **Central Package Registry**: Curated registry of verified packages
  - Registry location: `docs/registries/nuget/registry.json`
  - Metadata: name, version, description, scope, tags, author
  - Automatic registry validation during installation

### Components
- Command: `commands/sc-manage.md`
- Skill: `skills/managing-sc-packages/SKILL.md`
- Agents:
  - `agents/sc-packages-list.md` (v0.4.0)
  - `agents/sc-package-install.md` (v0.4.0)
  - `agents/sc-package-uninstall.md` (v0.4.0)
  - `agents/sc-package-docs.md` (v0.4.0)

### Dependencies
- **python3**: For package management logic and registry parsing
- **git**: For repository detection and scope resolution

### Scope
- **Global (Recommended)**: Install globally for system-wide access to all packages
- **Local**: Can also be installed in individual repositories for repo-specific package management

### Features
- **Installation Policy Enforcement**:
  - Recognizes package scope constraints (`global`, `local-only`, `global-or-local`)
  - Prevents invalid installations (e.g., installing local-only packages globally)
  - Clear error messages for policy violations
- **Token Substitution Support**:
  - Automatic detection of `{{REPO_NAME}}` and other tokens during installation
  - Token validation and error handling
  - Support for both Tier 0 (direct copy) and Tier 1 (token substitution) packages
- **Registry Management**:
  - Version pinning and semantic versioning support
  - Package dependency tracking (future enhancement)
  - Automated registry updates

### Known Limitations
- No automatic dependency resolution between packages (manual in v0.4.0)
- Registry updates require manual intervention (no auto-fetch in v0.4.0)
- Package search is limited to name and description (no full-text search)
- No package rollback or version history tracking
- Local scope requires being inside a valid git repository
- Token expansion errors are not recoverable without manual intervention

### Installation
```bash
# Global installation (recommended)
python3 tools/sc-install.py install sc-manage --dest ~/.claude

# Local (repo-specific) installation
python3 tools/sc-install.py install sc-manage --dest /path/to/your-repo/.claude
```

### Uninstallation
```bash
python3 tools/sc-install.py uninstall sc-manage --dest /path/to/your-repo/.claude
```

### Troubleshooting
- **"Not in a git repository"**: When using local scope from outside a repo
  - Solution: Navigate to a git repository directory or use global scope
- **"Package scope mismatch"**: Trying to install a local-only package globally
  - Solution: Use `--local` flag instead of `--global`
- **"Registry not found"**: Central registry is unavailable or invalid
  - Solution: Check network connectivity or update registry URL
- **"Token substitution failed"**: `{{REPO_NAME}}` or other tokens cannot be resolved
  - Solution: Ensure running from within a valid git repository for local installs

### Requirements
- **python3** (3.8+): For script execution and package management
- **git**: For repository detection and REPO_NAME token resolution

### Usage Examples
```bash
# List all available packages
/sc-manage --list

# Install sc-delay-tasks globally
/sc-manage --install sc-delay-tasks --global

# Install sc-git-worktree locally in current repo
/sc-manage --install sc-git-worktree --local

# View documentation and ask questions about sc-repomix-nuget
/sc-manage --docs sc-repomix-nuget

# Uninstall a package from global scope
/sc-manage --uninstall sc-delay-tasks --global
```

### Future Roadmap
- v0.5.0: Add automatic dependency resolution and installation
- v0.6.0: Package version checking and update notifications
- v1.0.0: Stable API with full backward compatibility
- Registry webhook integration for real-time updates
- Search and filtering by package tags
- Package rollback and version history
- Performance optimization for large registries

### Contributing
When updating this changelog:
1. Add entries under **[Unreleased]** for new features, bug fixes, or breaking changes
2. Use standard changelog categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**
3. Link issue/PR numbers when available
4. Create a new section with version and date when releasing
5. Maintain chronological order with newest versions at the top
6. Document any new package scope policies or token types

---

## Repository
- **Repository**: [synaptic-canvas](https://github.com/randlee/synaptic-canvas)
- **Issues**: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- **Package Registry**: [docs/registries/nuget/registry.json](https://github.com/randlee/synaptic-canvas/blob/main/docs/registries/nuget/registry.json)
