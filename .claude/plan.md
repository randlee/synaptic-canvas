# Migration Plan: Claude Code Native Marketplace Integration

## Executive Summary

Migrate Synaptic Canvas from custom Python-based installation (`python3 tools/sc-install.py`) to Claude Code's native `/plugin` marketplace system. This brings our marketplace in line with Claude Code standards and significantly improves user experience.

## Current State Analysis

### What We Have
1. **Custom Installation System** (1,283 lines in `src/sc_cli/install.py`)
   - Custom registry format: `docs/registries/nuget/registry.json`
   - Custom manifest format: `packages/*/manifest.yaml`
   - Python CLI: `tools/sc-install.py`
   - Skill integration: `src/sc_cli/skill_integration.py`
   - 3,603 lines of tests across 3 test files

2. **Package Structure** (4 packages)
   - `sc-delay-tasks` - Commands, agents, skills, scripts
   - `sc-git-worktree` - Commands, agents, skills
   - `sc-manage` - Commands, agents, skills
   - `sc-repomix-nuget` - Commands, agents, skills, scripts

3. **Documentation Burden**
   - 20+ references to `python3 tools/sc-install.py` across docs
   - README.md focused on Python installation
   - Multiple doc files need updates

### What We Need
1. **Claude Code Marketplace Format**
   - `.claude-plugin/marketplace.json` (required by Claude Code)
   - Individual `plugin.json` per package
   - Native `/plugin` command support

2. **Simplified User Experience**
   - From: `python3 tools/sc-install.py install sc-delay-tasks`
   - To: `/plugin install sc-delay-tasks@synaptic-canvas`

## Migration Strategy

### Phase 1: Add Claude Code Marketplace Support (Additive)

**Goal**: Enable `/plugin` command WITHOUT breaking existing Python system

#### 1.1 Create `.claude-plugin/marketplace.json`

```json
{
  "name": "synaptic-canvas",
  "owner": {
    "name": "randlee",
    "email": "[email protected]"
  },
  "metadata": {
    "description": "A marketplace for Claude Code skills, agents, and commands",
    "version": "0.5.1"
  },
  "plugins": [
    {
      "name": "sc-delay-tasks",
      "source": "./packages/sc-delay-tasks",
      "description": "Schedule delayed or interval-based actions with minimal heartbeats",
      "version": "0.5.1",
      "author": {
        "name": "randlee"
      },
      "license": "MIT",
      "keywords": ["delay", "polling", "scheduler", "ci", "workflow"],
      "category": "productivity"
    },
    {
      "name": "sc-git-worktree",
      "source": "./packages/sc-git-worktree",
      "description": "Manage git worktrees with optional tracking",
      "version": "0.5.1",
      "author": {
        "name": "randlee"
      },
      "license": "MIT",
      "keywords": ["git", "worktree", "parallel", "development"],
      "category": "development"
    },
    {
      "name": "sc-manage",
      "source": "./packages/sc-manage",
      "description": "Synaptic Canvas package management interface",
      "version": "0.5.1",
      "author": {
        "name": "randlee"
      },
      "license": "MIT",
      "keywords": ["packages", "management", "marketplace"],
      "category": "tools"
    },
    {
      "name": "sc-repomix-nuget",
      "source": "./packages/sc-repomix-nuget",
      "description": "Generate AI-optimized NuGet package context",
      "version": "0.5.1",
      "author": {
        "name": "randlee"
      },
      "license": "MIT",
      "keywords": ["nuget", "dotnet", "analysis", "context"],
      "category": "development"
    }
  ]
}
```

#### 1.2 Create `plugin.json` for Each Package

Each package needs `.claude-plugin/plugin.json`:

**Template** (based on `manifest.yaml` data):
```json
{
  "name": "sc-delay-tasks",
  "description": "Schedule delayed one-shot or bounded polling actions",
  "version": "0.5.1",
  "author": {
    "name": "randlee"
  },
  "license": "MIT",
  "keywords": ["delay", "polling", "scheduler"],
  "commands": ["./commands"],
  "agents": ["./agents"],
  "skills": ["./skills"]
}
```

**Files to Create:**
- `packages/sc-delay-tasks/.claude-plugin/plugin.json`
- `packages/sc-git-worktree/.claude-plugin/plugin.json`
- `packages/sc-manage/.claude-plugin/plugin.json`
- `packages/sc-repomix-nuget/.claude-plugin/plugin.json`

#### 1.3 Update Documentation - Primary

**README.md** - Add Claude Code installation as **PRIMARY** method:
```markdown
## 🚀 Quick Start (10 Seconds)

### Add the Marketplace

```bash
/plugin marketplace add randlee/synaptic-canvas
```

### Install a Package

```bash
/plugin install sc-delay-tasks@synaptic-canvas
```

### Browse All Packages

```bash
/plugin
```

---

## Alternative: Python CLI (Legacy)

For advanced use cases or automation, the Python CLI is still available:

```bash
python3 tools/sc-install.py install sc-delay-tasks
```

See [Legacy Installation Guide](docs/LEGACY-INSTALL.md) for details.
```

### Phase 2: Testing & Validation

#### 2.1 Manual Testing Checklist

**Marketplace Addition:**
- [ ] `/plugin marketplace add randlee/synaptic-canvas` works
- [ ] Marketplace appears in `/plugin marketplace list`
- [ ] All 4 packages visible in `/plugin` browser

**Package Installation:**
- [ ] `/plugin install sc-delay-tasks@synaptic-canvas` succeeds
- [ ] Commands appear in `/help`
- [ ] Agents appear in agent list
- [ ] Skills are functional

**Per-Package Tests:**
- [ ] sc-delay-tasks: `/sc-delay` command works
- [ ] sc-git-worktree: `/sc-git-worktree` command works
- [ ] sc-manage: `/sc-manage` command works
- [ ] sc-repomix-nuget: `/sc-repomix-nuget` command works

**Cleanup:**
- [ ] `/plugin uninstall sc-delay-tasks` removes all artifacts
- [ ] Reinstall works after uninstall

#### 2.2 Automated Testing

**New Test File**: `tests/test_claude_marketplace.py`

```python
"""Test Claude Code marketplace integration."""
import json
from pathlib import Path

def test_marketplace_json_exists():
    """Verify .claude-plugin/marketplace.json exists."""
    marketplace = Path(".claude-plugin/marketplace.json")
    assert marketplace.exists()

def test_marketplace_json_valid():
    """Verify marketplace.json is valid JSON with required fields."""
    marketplace = Path(".claude-plugin/marketplace.json")
    data = json.loads(marketplace.read_text())

    assert "name" in data
    assert data["name"] == "synaptic-canvas"
    assert "owner" in data
    assert "plugins" in data
    assert len(data["plugins"]) == 4

def test_all_packages_have_plugin_json():
    """Verify each package has .claude-plugin/plugin.json."""
    packages = ["sc-delay-tasks", "sc-git-worktree", "sc-manage", "sc-repomix-nuget"]

    for pkg in packages:
        plugin_json = Path(f"packages/{pkg}/.claude-plugin/plugin.json")
        assert plugin_json.exists(), f"{pkg} missing plugin.json"

        data = json.loads(plugin_json.read_text())
        assert data["name"] == pkg
        assert "version" in data
        assert data["version"] == "0.5.1"

def test_plugin_json_schema_valid():
    """Verify plugin.json files have required fields."""
    packages = ["sc-delay-tasks", "sc-git-worktree", "sc-manage", "sc-repomix-nuget"]

    required_fields = ["name", "description", "version", "author"]

    for pkg in packages:
        plugin_json = Path(f"packages/{pkg}/.claude-plugin/plugin.json")
        data = json.loads(plugin_json.read_text())

        for field in required_fields:
            assert field in data, f"{pkg} missing {field}"

def test_marketplace_package_sources_exist():
    """Verify all package sources referenced in marketplace exist."""
    marketplace = Path(".claude-plugin/marketplace.json")
    data = json.loads(marketplace.read_text())

    for plugin in data["plugins"]:
        source = plugin["source"]
        source_path = Path(source.lstrip("./"))
        assert source_path.exists(), f"Source {source} does not exist"
```

**Test Execution:**
```bash
pytest tests/test_claude_marketplace.py -v
```

### Phase 3: Deprecation Strategy

#### 3.1 Keep (For Now)

These components serve purposes beyond just installation:

**Keep Forever:**
- `src/sc_cli/delay_run.py` - Used by sc-delay-tasks package scripts
- `packages/*/manifest.yaml` - Internal metadata, may be useful for tooling

**Keep Temporarily (6-12 months):**
- `src/sc_cli/install.py` - Legacy support for existing users
- `tools/sc-install.py` - CLI wrapper
- `tools/sc-install.sh` - Bash wrapper (already deprecated)
- `src/sc_cli/skill_integration.py` - Used by sc-manage skill
- `docs/registries/nuget/registry.json` - Custom registry format

#### 3.2 Document as Legacy

**Create**: `docs/LEGACY-INSTALL.md`

Move all Python installation documentation here:
- Installation via `python3 tools/sc-install.py`
- Registry management commands
- Custom registry format details
- Migration guide from legacy to `/plugin`

**Mark as Deprecated in Code:**
```python
# src/sc_cli/install.py
import warnings

warnings.warn(
    "The Python CLI installation method is deprecated. "
    "Please use Claude Code's native /plugin command instead: "
    "/plugin marketplace add randlee/synaptic-canvas",
    DeprecationWarning,
    stacklevel=2
)
```

#### 3.3 Eventual Removal Plan (v0.6.0 or v1.0.0)

**Candidates for Removal:**
- `src/sc_cli/install.py` (1,283 lines)
- `tools/sc-install.py`
- `tools/sc-install.sh`
- `docs/registries/nuget/registry.json`
- `tests/test_sc_install*.py` (2,594 lines)
- `tests/test_marketplace_skill.py` portions related to Python CLI

**Estimate**: ~4,000 lines of code can eventually be removed

### Phase 4: Documentation Updates

#### 4.1 High-Priority Updates

**Files requiring immediate updates:**

1. **README.md** (8 references)
   - Replace primary installation method with `/plugin`
   - Move Python CLI to "Alternative" section
   - Update Quick Start to use `/plugin`

2. **Package READMEs** (4 files)
   - `packages/sc-delay-tasks/README.md`
   - `packages/sc-git-worktree/README.md`
   - `packages/sc-manage/README.md`
   - `packages/sc-repomix-nuget/README.md`
   - Update installation sections to use `/plugin`

3. **DOCUMENTATION-INDEX.md**
   - Update installation examples
   - Add link to new marketplace integration docs

#### 4.2 Secondary Updates

**Update when convenient:**
- `docs/RELEASE-PROCESS.md` - Update installation testing steps
- `docs/RELEASE-NOTES-QUICK-REFERENCE.md` - Note new installation method
- `pm/plans/2025-12-04-ongoing-maintenance-backlog.md` - Update testing steps
- `.serena/memories/suggested_commands.md` - Update command references
- `WARP.md` - Update examples

#### 4.3 New Documentation

**Create:**
- `docs/CLAUDE-MARKETPLACE-INTEGRATION.md` - How we integrate with Claude Code
- `docs/LEGACY-INSTALL.md` - Python CLI documentation (for backward compatibility)
- `docs/MIGRATION-FROM-PYTHON-CLI.md` - Guide for existing users

### Phase 5: Version Bump & Release

**Version**: 0.6.0 (minor version bump for new feature)

**Release Notes:**
```markdown
## v0.6.0 - Claude Code Marketplace Integration

### 🎉 Major Feature: Native Claude Code Support

Synaptic Canvas now integrates with Claude Code's native `/plugin` system!

**New Installation Method:**
```bash
/plugin marketplace add randlee/synaptic-canvas
/plugin install sc-delay-tasks@synaptic-canvas
```

**Benefits:**
- ✅ No Python scripts required
- ✅ Native Claude Code integration
- ✅ Simpler installation (one command vs multiple)
- ✅ Better discovery via `/plugin` browser
- ✅ Automatic updates via Claude Code

### Breaking Changes

None - Python CLI still works for backward compatibility

### Deprecation Notice

The Python CLI (`python3 tools/sc-install.py`) is now deprecated and will be removed in v1.0.0. Please migrate to `/plugin` commands.

### Migration Guide

See [Migration Guide](docs/MIGRATION-FROM-PYTHON-CLI.md)
```

## Implementation Checklist

### ✅ Pre-Implementation
- [x] Research Claude Code marketplace format
- [x] Analyze current system architecture
- [x] Identify code/docs to deprecate
- [x] Create comprehensive plan

### 📝 Phase 1: Add Marketplace Support
- [ ] Create `.claude-plugin/marketplace.json`
- [ ] Create `packages/sc-delay-tasks/.claude-plugin/plugin.json`
- [ ] Create `packages/sc-git-worktree/.claude-plugin/plugin.json`
- [ ] Create `packages/sc-manage/.claude-plugin/plugin.json`
- [ ] Create `packages/sc-repomix-nuget/.claude-plugin/plugin.json`
- [ ] Verify JSON syntax with validators

### 🧪 Phase 2: Testing
- [ ] Manual testing: Add marketplace
- [ ] Manual testing: Install each package
- [ ] Manual testing: Verify commands/agents/skills work
- [ ] Manual testing: Uninstall/reinstall cycle
- [ ] Create `tests/test_claude_marketplace.py`
- [ ] Run automated tests: `pytest tests/test_claude_marketplace.py`
- [ ] Run full test suite: `pytest tests/`

### 📚 Phase 3: Documentation
- [ ] Create `docs/LEGACY-INSTALL.md`
- [ ] Create `docs/CLAUDE-MARKETPLACE-INTEGRATION.md`
- [ ] Create `docs/MIGRATION-FROM-PYTHON-CLI.md`
- [ ] Update `README.md` (primary installation method)
- [ ] Update `packages/*/README.md` (4 files)
- [ ] Update `DOCUMENTATION-INDEX.md`
- [ ] Add deprecation warnings to Python CLI

### 🏷️ Phase 4: Release
- [ ] Bump version to 0.6.0 in all manifests
- [ ] Update `marketplace.json` version
- [ ] Commit all changes
- [ ] Create PR to develop
- [ ] Merge to main after approval
- [ ] Create v0.6.0 release tag
- [ ] Create GitHub release with notes
- [ ] Announce in appropriate channels

### 🔮 Phase 5: Future Cleanup (v1.0.0)
- [ ] Remove Python CLI code
- [ ] Remove custom registry system
- [ ] Remove installation tests for Python CLI
- [ ] Update all remaining docs
- [ ] Final deprecation migration

## Risk Assessment

### Low Risk ✅
- **No breaking changes** - Python CLI continues to work
- **Additive approach** - New system alongside old
- **Well-documented API** - Claude Code has clear specs
- **Simple migration** - Clear path for users

### Medium Risk ⚠️
- **Testing complexity** - Need to test both systems
- **Documentation debt** - Many files to update
- **User confusion** - Two installation methods temporarily

### Mitigation Strategies
1. Clear deprecation timeline in docs
2. Comprehensive testing checklist
3. Migration guide for users
4. Gradual removal over multiple versions

## Success Criteria

✅ Users can add marketplace with `/plugin marketplace add`
✅ All 4 packages installable via `/plugin install`
✅ Commands, agents, and skills work after installation
✅ All tests pass (including new marketplace tests)
✅ Documentation clearly shows `/plugin` as primary method
✅ Python CLI still works (backward compatibility)
✅ No regressions in existing functionality

## Timeline Estimate

- **Phase 1** (Marketplace Files): 2-3 hours
- **Phase 2** (Testing): 2-3 hours
- **Phase 3** (Documentation): 3-4 hours
- **Phase 4** (Release): 1 hour
- **Total**: 8-11 hours

## Questions for User

1. **Email for marketplace owner**: Should we use your email or a generic one?
2. **Deprecation timeline**: Remove Python CLI in v0.6.0, v1.0.0, or keep indefinitely?
3. **sc-manage package**: This package wraps the Python CLI - should we rewrite it to use `/plugin` commands instead?
4. **Testing approach**: Manual testing only, or wait for CI to add `/plugin` command testing?

## Notes

- This plan maintains backward compatibility while modernizing the system
- The additive approach minimizes risk
- Clear deprecation path provides time for users to migrate
- Estimated ~4,000 lines of code can eventually be removed
