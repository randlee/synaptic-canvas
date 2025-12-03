# Marketplace Improvement Plan

**Status:** In Progress - Foundation + Week 1-3 Complete
**Created:** 2025-12-02
**Last Updated:** 2025-12-02
**Progress:** Foundation Week ✅ | Week 1 ✅ | Week 2 ✅ | Week 3 (Item 1) ✅
**Priority Focus:** Registry Metadata → Version/Release Tracking → Documentation → Security Indicators

---

## Executive Summary

This plan addresses the four critical gaps preventing mainstream marketplace adoption:
1. **Registry Metadata** - Enrich `registry.json` with searchable package information
2. **Version/Release Tracking** - Add CHANGELOG files and establish single source of truth for versions
3. **Sparse Documentation** - Expand integration guides, troubleshooting, and use cases
4. **Security Indicators** - Add publisher verification and security metadata

**Cross-Cutting Concerns:**
- **Version Management Synchronization** - Establish and verify single source of truth across all layers
- **Document Cleanup** - Archive outdated/misleading docs, establish versioning for documentation

---

## 🎯 Progress Summary

### Foundation Week - ✅ COMPLETE
**CCS (Cross-Cutting System) Tasks:**
- [x] CCS.1: Versioning Strategy Document - `docs/versioning-strategy.md` (580+ lines)
- [x] CCS.2: Artifact Version Synchronization - All 22 artifacts at 0.4.0
- [x] CCS.3: Version Verification Scripts - `audit-versions.sh`, `sync-versions.py`, `compare-versions.sh`
- [x] CCS.4: CI/CD Version Audit - `.github/workflows/version-audit.yml` added
- [x] CCS.5: Registry Metadata - `registry.json` v2.0 with full metadata
- [x] CCS.6: Developer Documentation - Versioning section in `CONTRIBUTING.md`

**CCD (Document Cleanup):**
- [x] Created `.archive/` directory structure with documentation
- [x] Created `docs/DOCUMENTATION-INDEX.md` (central navigation hub)
- [x] Created `docs/registries/README.md` (registry guide)

**Deliverables:** 10 new files, 3 scripts, 1 workflow, 0 version mismatches

---

### Week 1: Registry Metadata Enhancement - ✅ COMPLETE
**Task 1: Registry Schema v2.0**
- [x] Created `docs/registries/nuget/registry.schema.json` (JSON Schema v7)
- [x] Created `docs/registries/nuget/validate-registry.py` (validation utility)
- [x] Created schema documentation (SCHEMA_DOCUMENTATION.md, SCHEMA_QUICK_REFERENCE.md)
- [x] All 4 packages validate successfully

**Task 2: CHANGELOG.md for All Packages**
- [x] `packages/delay-tasks/CHANGELOG.md` (108 lines)
- [x] `packages/git-worktree/CHANGELOG.md` (152 lines)
- [x] `packages/sc-manage/CHANGELOG.md` (161 lines)
- [x] `packages/repomix-nuget/CHANGELOG.md` (204 lines)

**Task 3: Version Compatibility Matrix**
- [x] `docs/version-compatibility-matrix.md` (800+ lines)
- [x] Compatibility matrices, upgrade paths, troubleshooting

**Deliverables:** 7 documentation files + 1 validation script, 3,100+ lines

---

### Week 2: Release Tracking Documentation - ✅ COMPLETE
**Task 1: Release Process Documentation**
- [x] `docs/RELEASE-PROCESS.md` (1,764 lines, 43KB)
- [x] 7-step release execution, 4 release scenarios, pre/post-release checklists

**Task 2: Release Notes Templates**
- [x] `docs/README-RELEASE-NOTES.md` (central hub)
- [x] `docs/RELEASE-NOTES-TEMPLATE.md` (1,461 lines, 38KB with tier-specific variants)
- [x] `docs/RELEASE-NOTES-QUICK-REFERENCE.md` (415 lines, print-friendly)

**Task 3: Version Release Guide**
- [x] `docs/VERSION-RELEASE-GUIDE.md` (2,707 lines, 69KB)
- [x] 12 comprehensive sections, 4 complete scenario walkthroughs

**Deliverables:** 5 documentation files, 6,872 lines, 177KB

---

### Week 3: Documentation Expansion - 🟡 IN PROGRESS
**Task 1: Use Cases for All Packages - ✅ COMPLETE**
- [x] `packages/delay-tasks/USE-CASES.md` (684 lines, 21KB - 7 use cases)
- [x] `packages/git-worktree/USE-CASES.md` (1,087 lines, 31KB - 7 use cases)
- [x] `packages/sc-manage/USE-CASES.md` (1,065 lines, 29KB - 7 use cases)
- [x] `packages/repomix-nuget/USE-CASES.md` (1,361 lines, 38KB - 7 use cases)

**Deliverables:** 4 USE-CASES.md files, 4,197 lines, 119KB

**Task 2: Troubleshooting for All Packages - ⏳ PENDING**
**Task 3: Diagnostic Tool Documentation - ⏳ PENDING**

---

### Week 4: Security Implementation - ⏳ PENDING

---

## 📊 Overall Project Metrics

| Category | Completed | Deliverables |
|----------|-----------|---------------|
| Documentation Files | 32 | .md files |
| Scripts/Tools | 4 | audit, sync, compare, validate |
| CI/CD Workflows | 1 | version-audit.yml |
| Total Lines of Code/Docs | 26,000+ | lines |
| Total Size | 450+ | KB |
| Packages Covered | 4 | delay-tasks, git-worktree, sc-manage, repomix-nuget |
| Version Mismatches | 0 | all at 0.4.0 |
| Test Coverage | 33/33 | version audit checks passing |

---

## Priority 1: Registry Metadata Enhancement ✅ COMPLETE

**Goal:** Transform `registry.json` from repository links to searchable package metadata hub
**Impact:** Enables programmatic discovery, web UI search/filtering, and package comparison
**Timeline Estimate:** 2-3 days

### Phase 1.1: Registry Schema Update
- [ ] **Document new registry schema**
  - [ ] Create `docs/registry-schema-v2.md` with extended metadata fields
  - [ ] Define fields: name, version, description, author, tags, scope, requires, install_url, download_count, security_status, compatibility
  - [ ] Include examples showing old vs new format
  - [ ] Document backward compatibility approach (v1 to v2 migration)
  - [ ] Specify optional vs required fields

- [ ] **Update registry generation logic**
  - [ ] Modify registry schema generation in `packages/repomix-nuget/scripts/validate-registry.sh`
  - [ ] Extract metadata from each package's `manifest.yaml` during registry build
  - [ ] Populate new fields programmatically:
    - [ ] `description` from manifest
    - [ ] `author` from manifest
    - [ ] `tags` from manifest
    - [ ] `requires` from manifest
    - [ ] `scope` from manifest (local-only, global, both)
    - [ ] `latest_version` from manifest version field
    - [ ] `artifacts_count` (sum of commands, skills, agents, scripts)

- [ ] **Create registry build script**
  - [ ] Location: `scripts/generate-registry.py` or extend existing registry generation
  - [ ] Input: Scans all `packages/*/manifest.yaml`
  - [ ] Output: `docs/registries/nuget/registry.json` with enriched metadata
  - [ ] Adds `generated_at` timestamp in ISO 8601 format
  - [ ] Includes `schema_version: 2.0` field
  - [ ] Validates all required fields present before writing

### Phase 1.2: Manifest Metadata Standardization
- [ ] **Audit existing manifests for consistency**
  - [ ] Check `packages/delay-tasks/manifest.yaml` for completeness
  - [ ] Check `packages/git-worktree/manifest.yaml` for completeness
  - [ ] Check `packages/sc-manage/manifest.yaml` for completeness
  - [ ] Check `packages/repomix-nuget/manifest.yaml` for completeness
  - [ ] Document any missing or inconsistent fields

- [ ] **Standardize manifest templates**
  - [ ] Create `templates/manifest.template.yaml` with all standard fields
  - [ ] Define field descriptions for package authors
  - [ ] Add validation rules (required, type, format)
  - [ ] Update CONTRIBUTING.md with manifest requirements

- [ ] **Ensure all manifests include:**
  - [ ] `description`: 1-2 sentence summary (required)
  - [ ] `author`: GitHub handle or org name (required)
  - [ ] `license`: Software license (required, default MIT)
  - [ ] `tags`: 5-10 searchable keywords (required)
  - [ ] `requires`: List of runtime dependencies with versions (required if any)
  - [ ] `install.scope`: local-only | global | both (required)
  - [ ] `homepage`: URL to package documentation or repo (optional)
  - [ ] `repository`: GitHub repo URL (optional)
  - [ ] `bugs`: Issue tracker URL (optional)

### Phase 1.3: Registry Format Implementation
- [ ] **Update registry.json structure**
  - [ ] File location: `docs/registries/nuget/registry.json`
  - [ ] Add `$schema` URL for validation
  - [ ] Add `schema_version: "2.0"` field
  - [ ] Add `generated` timestamp
  - [ ] Expand package entries with full metadata from manifests
  - [ ] Include `download_count` field (initially 0, updated by analytics)
  - [ ] Include `security_status` field (see Priority 4)

**Example new registry structure:**
```json
{
  "$schema": "https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registry-schema-v2.json",
  "schema_version": "2.0",
  "generated": "2025-12-02T15:30:00Z",
  "repo": "randlee/synaptic-canvas",
  "packages": {
    "delay-tasks": {
      "name": "delay-tasks",
      "version": "1.0.0",
      "description": "Scheduling and polling utilities for delayed task execution",
      "author": "randlee",
      "license": "MIT",
      "tags": ["scheduling", "polling", "ci", "automation", "timing"],
      "scope": "global",
      "requires": ["python3", "bash"],
      "install_url": "https://github.com/randlee/synaptic-canvas/tree/main/packages/delay-tasks",
      "repository": "https://github.com/randlee/synaptic-canvas",
      "artifacts": {
        "commands": 1,
        "skills": 1,
        "agents": 3,
        "scripts": 1
      },
      "download_count": 42,
      "security_status": "verified",
      "dependents": ["git-worktree"],
      "latest_version": "1.0.0",
      "compatibility": {
        "claude_versions": ["0.4.0+"],
        "os": ["macos", "linux"],
        "python": "3.8+",
        "node": null,
        "git": null
      }
    }
  }
}
```

- [ ] **Create registry validation schema**
  - [ ] File: `docs/registry-schema-v2.json` (JSON Schema format)
  - [ ] Validate all registry.json files against this schema
  - [ ] Include validation in CI/CD pipeline
  - [ ] Make validation available as command: `tools/validate-registry.py`

### Phase 1.4: Migration and Backward Compatibility
- [ ] **Maintain v1 registry for compatibility**
  - [ ] Keep existing `registry.json` as is OR create `registry-v1.json`
  - [ ] Create `registry-latest.json` pointing to v2.0
  - [ ] Document migration path for consumers

- [ ] **Update all registry references**
  - [ ] Update documentation referencing registry to use latest version
  - [ ] Update sc-manage package to read v2.0 format if available, fall back to v1
  - [ ] Add URL to latest registry in README.md

- [ ] **Document registry API**
  - [ ] Create `docs/registry-api.md` explaining:
    - [ ] Registry structure and fields
    - [ ] How to query the registry programmatically
    - [ ] Schema versions and deprecation timeline
    - [ ] Best practices for consuming registry data

---

---

## Cross-Cutting: Version Management System

**Goal:** Establish single source of truth for all versions (marketplace, packages, agents, commands, skills)
**Impact:** No version mismatches, automated synchronization, clear versioning strategy
**Timeline Estimate:** 2 days (to be completed BEFORE Phase 2.1)
**Criticality:** FOUNDATIONAL - must be done first

### CCS.1: Current State Assessment ✅ COMPLETE

**Version Inconsistencies Found:**
```
version.yaml (claimed single source of truth):  0.4.0
delay-tasks/manifest.yaml:                      1.0.0  ❌ MISMATCH
git-worktree/manifest.yaml:                     1.0.0  ❌ MISMATCH
repomix-nuget/manifest.yaml:                    0.4.0  ✅ Match
sc-manage/manifest.yaml:                        0.4.0  ✅ Match
All agents frontmatter:                         0.4.0  (from delay-tasks sample)
All commands frontmatter:                       NONE   ❌ Missing
All skills frontmatter:                         NONE   ❌ Missing
```

**Issues to Fix:**
- [x] `version.yaml` is NOT actually single source of truth - inconsistent with packages
- [x] Commands lack version frontmatter entirely
- [x] Skills lack version frontmatter entirely
- [x] No synchronization mechanism between layers
- [x] No verification that all versions match

### CCS.2: Establish Single Source of Truth ✅ COMPLETE

- [ ] **Clarify versioning hierarchy**
  - [ ] Decide: Does version.yaml drive all versions OR does each package manage its own?
  - [ ] Recommendation: Each package owns its version in manifest.yaml
  - [ ] version.yaml should represent "marketplace CLI version" (separate concern)
  - [ ] Document decision in `docs/versioning-strategy.md`

- [ ] **Create versioning strategy document**
  - [ ] File: `docs/versioning-strategy.md`
  - [ ] Define three version layers:
    1. **Marketplace Version** (version.yaml): Version of the marketplace platform/CLI itself
       - Used for: sc-install.py, marketplace infrastructure
       - When to bump: Major changes to installation system or marketplace features
       - Current: 0.4.0

    2. **Package Version** (manifest.yaml): Version of the individual package
       - Used for: Tracking changes to commands/skills/agents within a package
       - When to bump: Any changes to package artifacts
       - Current: varies (1.0.0 or 0.4.0 per package)

    3. **Artifact Version** (frontmatter in agents/commands/skills): Version of individual artifacts
       - Used for: Tracking changes to specific commands/skills/agents
       - When to bump: When specific artifact is modified
       - Synchronize with package version for consistency

  - [ ] Document SemVer approach for each layer:
    - [ ] Marketplace version: X.Y.Z (0.x = beta, 1.0 = stable launch)
    - [ ] Package versions: Independent SemVer per package
    - [ ] Artifact versions: Match package version or more granular

  - [ ] Policy: Artifact versions must match or be ≤ package version
    - Example: If package is 1.0.0, all artifacts must be 1.0.0 or less
    - Allows for backward-compat within version range

- [ ] **Set correct initial versions**
  - [ ] Decide on version strategy above first
  - [ ] Fix package manifest versions:
    - [ ] Confirm delay-tasks should be 1.0.0 (it is - stable)
    - [ ] Confirm git-worktree should be 1.0.0 (it is - stable)
    - [ ] Confirm repomix-nuget should stay 0.4.0 (currently beta)
    - [ ] Confirm sc-manage should stay 0.4.0 (currently beta)

  - [ ] Update all agent frontmatter to match their package version:
    - [ ] delay-tasks agents → 1.0.0
    - [ ] git-worktree agents → 1.0.0
    - [ ] sc-manage agents → 0.4.0
    - [ ] repomix-nuget agents → 0.4.0

  - [ ] Add version frontmatter to ALL commands:
    - [ ] `packages/delay-tasks/commands/delay.md` → version: 1.0.0
    - [ ] `packages/git-worktree/commands/git-worktree.md` → version: 1.0.0
    - [ ] `packages/sc-manage/commands/sc-manage.md` → version: 0.4.0
    - [ ] `packages/repomix-nuget/commands/repomix-nuget.md` → version: 0.4.0

  - [ ] Add version frontmatter to ALL skills:
    - [ ] `packages/delay-tasks/skills/delaying-tasks/SKILL.md` → version: 1.0.0
    - [ ] `packages/git-worktree/skills/managing-worktrees/SKILL.md` → version: 1.0.0
    - [ ] `packages/sc-manage/skills/managing-sc-packages/SKILL.md` → version: 0.4.0
    - [ ] `packages/repomix-nuget/skills/generating-nuget-context/SKILL.md` → version: 0.4.0

- [ ] **Decide marketplace version (version.yaml) fate**
  - [ ] Option A: Keep as separate "platform version" (recommend)
    - [ ] Stays at 0.4.0 for now
    - [ ] Only update when marketplace infrastructure changes
    - [ ] Document clearly in CONTRIBUTING.md
    - [ ] Update: `version.yaml` comment to clarify this is platform version, not package versions

  - [ ] Option B: Align with highest package version (less recommend)
    - [ ] Would become 1.0.0 now (because delay-tasks and git-worktree are 1.0.0)
    - [ ] Creates confusion about what version.yaml represents
    - [ ] Harder to track independent platform changes

  - [ ] Recommended: Go with Option A - keep separate

### CCS.3: Version Synchronization Across All Artifacts

- [ ] **Add version field to ALL frontmatter schemas**
  - [ ] Commands must have: version (required)
  - [ ] Skills must have: version (required)
  - [ ] Agents must have: version (required) - already present
  - [ ] Update `CONTRIBUTING.md` to mandate version in all frontmatter

- [ ] **Create frontmatter templates**
  - [ ] Template for agents frontmatter:
    ```yaml
    ---
    name: agent-name
    description: Brief description
    version: 1.0.0
    model: sonnet
    color: gray
    ---
    ```

  - [ ] Template for commands frontmatter:
    ```yaml
    ---
    name: /command-name
    description: Brief description
    version: 1.0.0
    options:
      - name: --option
        description: What it does
    ---
    ```

  - [ ] Template for skills frontmatter:
    ```yaml
    ---
    name: skill-name
    description: >
      Multi-line description
    version: 1.0.0
    ---
    ```

- [ ] **Update all existing commands with version**
  - [ ] Modify each command file to include version in YAML frontmatter
  - [ ] Version = package manifest version
  - [ ] Files to update: 4 commands across 4 packages

- [ ] **Update all existing skills with version**
  - [ ] Modify each skill file to include version in YAML frontmatter
  - [ ] Version = package manifest version
  - [ ] Files to update: 4 skills across 4 packages

### CCS.4: Version Verification and Synchronization Scripts

- [ ] **Create version audit script**
  - [ ] File: `scripts/audit-versions.sh`
  - [ ] Purpose: Verify all versions are synchronized
  - [ ] Checks performed:
    - [ ] All agents have version in frontmatter
    - [ ] All commands have version in frontmatter
    - [ ] All skills have version in frontmatter
    - [ ] All artifact versions match their package manifest version
    - [ ] CHANGELOG.md exists for each package (add in Phase 2.1)
    - [ ] Version in manifest.yaml follows SemVer
    - [ ] Generate report with mismatches highlighted

  - [ ] Output: Human-readable report and JSON for CI/CD
  - [ ] Exit codes: 0 for pass, 1 for failures

- [ ] **Create version enforcement in CI/CD**
  - [ ] Add GitHub Actions workflow: `.github/workflows/version-audit.yml`
  - [ ] Runs on: pull_request, push to main
  - [ ] Runs: `scripts/audit-versions.sh`
  - [ ] Blocks merge if audit fails
  - [ ] Reports findings in PR

- [ ] **Create version update helper**
  - [ ] File: `scripts/sync-versions.py`
  - [ ] Purpose: Bulk update versions when bumping package version
  - [ ] Usage: `python3 scripts/sync-versions.py --package delay-tasks --version 1.1.0`
  - [ ] Action: Updates:
    - [ ] Package manifest.yaml
    - [ ] All agents' frontmatter
    - [ ] All commands' frontmatter
    - [ ] All skills' frontmatter
    - [ ] Agent registry if exists
    - [ ] Creates git commit with message: "chore(versioning): bump delay-tasks to 1.1.0"

- [ ] **Create version comparison tool**
  - [ ] File: `scripts/compare-versions.sh`
  - [ ] Usage: `scripts/compare-versions.sh [--by-layer|--by-package]`
  - [ ] Output: Table showing all versions organized by layer or package
  - [ ] Highlights mismatches with warnings

### CCS.5: Registry Version Metadata

- [ ] **Add version tracking to registry.json**
  - [ ] Extend package entries with version information:
    ```json
    {
      "delay-tasks": {
        "name": "delay-tasks",
        "version": "1.0.0",
        "artifact_versions": {
          "delay-once": "1.0.0",
          "delay-poll": "1.0.0",
          "delay": "1.0.0",
          "delaying-tasks": "1.0.0"
        },
        "artifact_count": 4,
        "last_updated": "2025-12-02T00:00:00Z"
      }
    }
    ```

- [ ] **Generate artifact version info automatically**
  - [ ] Registry generation script extracts versions from frontmatter
  - [ ] Creates artifact_versions mapping
  - [ ] Validates all artifacts match package version
  - [ ] Reports mismatches as errors

### CCS.6: Documentation for Version Management

- [ ] **Add to CONTRIBUTING.md:**
  - [ ] "Versioning Requirements" section
  - [ ] Mandate: All agents, commands, skills must have version in frontmatter
  - [ ] Mandate: Version must match package manifest version
  - [ ] Instructions on using `sync-versions.py` to update versions
  - [ ] Instructions on running `audit-versions.sh` locally before PR

- [ ] **Create version management guide**
  - [ ] File: `docs/version-management-guide.md`
  - [ ] How to bump package version
  - [ ] How to verify versions are synchronized
  - [ ] How to use sync-versions.py
  - [ ] Troubleshooting version mismatches

---

## Cross-Cutting: Document Cleanup ✅ COMPLETE and Archival

**Goal:** Remove outdated/misleading documentation, establish clear versioning for docs, create archive
**Impact:** Cleaner codebase, no confusion from old docs, clear documentation history
**Timeline Estimate:** 1-2 days
**Criticality:** Should be done in parallel with version system, before other doc updates

### CCD.1: Create Archive Structure

- [ ] **Create .archive directory**
  - [ ] Create: `/Users/randlee/Documents/github/synaptic-canvas/.archive/`
  - [ ] Structure:
    ```
    .archive/
    ├── docs/                    # Old documentation files
    ├── deprecated-guides/       # Deprecated how-to guides
    ├── versioned-docs/          # Old versions of versioned docs
    │   ├── guidelines-v0.3/
    │   ├── guidelines-v0.4/
    │   └── README.md           # Version index
    └── README.md               # Archive purpose and index
    ```

- [ ] **Add .archive to .gitignore**
  - [ ] File: `.gitignore`
  - [ ] Add: `# Archive - preserve for historical reference`
  - [ ] Add: `.archive/`
  - [ ] Optional: Add specific archive index file if you want historical reference
    - [ ] Could commit `.archive/INDEX.md` but exclude contents
    - [ ] Allows future historians to know what was archived

- [ ] **Create archive index**
  - [ ] File: `.archive/README.md`
  - [ ] Document:
    - [ ] Purpose: "Historical records of documentation and guides"
    - [ ] How to access: These files are not part of active codebase
    - [ ] Archive date: Date archived
    - [ ] Original location: Where file came from
    - [ ] Reason archived: Why it was removed
    - [ ] Index of what's archived (with dates)

### CCD.2: Audit Current Documentation

- [ ] **Inventory all documentation files**
  - [ ] Root level: `README.md`, `CONTRIBUTING.md`, `WARP.md`, `SECURITY.md` (future)
  - [ ] Docs folder: `docs/*.md` files
  - [ ] Package READMEs: 4 files in `packages/*/README.md`
  - [ ] Skill docs: `packages/*/skills/*/SKILL.md` (4 files)
  - [ ] Command docs: `packages/*/commands/*.md` (4 files)
  - [ ] Agent docs: `packages/*/agents/*.md` (12 files)

- [ ] **Categorize by purpose and status**

  **Keep (Active):**
  - [ ] README.md - Main repository overview (current, essential)
  - [ ] CONTRIBUTING.md - Package authoring guide (essential)
  - [ ] docs/agent-runner.md - Agent runner guide (used, current)
  - [ ] Package README.md files (used, essential)
  - [ ] All command/skill/agent docs (used, current)

  **Archive (Outdated/Replaced):**
  - [ ] `WARP.md` - Developer environment guide (alternative to README for developers)
    - Reason: Duplicates/overlaps content in README
    - Decision: Archive as historical reference OR merge into README
    - Recommend: Merge relevant parts into README, archive original

  - [ ] `docs/claude-code-skills-agents-guidelines-0.4.md` - Architecture guidelines
    - Reason: Version in filename (0.4), unclear if still current
    - Decision: Move to versioned archive, create new unversioned copy if current
    - Action:
      - [ ] Move to: `.archive/versioned-docs/guidelines-v0.4/`
      - [ ] Create: `docs/ARCHITECTURE.md` (current, unversioned)
      - [ ] Reference: Link old version in new doc with "See historical v0.4 guidelines"

  - [ ] `.claude.local-backup-20251130130230/` - Local backup directory
    - Reason: Appears to be local development backup, should not be committed
    - Decision: Delete or add to .gitignore
    - Action:
      - [ ] Add to .gitignore: `.claude.local-backup*/`
      - [ ] Remove from git: `git rm -r --cached .claude.local-backup-*`
      - [ ] Delete local copy: `rm -rf .claude.local-backup-*`

- [ ] **Document each file's status**
  - [ ] Create: `docs/DOCUMENTATION-STATUS.md`
  - [ ] Table with:
    - [ ] Filename
    - [ ] Purpose
    - [ ] Status (active, deprecated, archived, legacy)
    - [ ] Last updated date
    - [ ] Maintenance owner (if applicable)
    - [ ] Notes

### CCD.3: Process Documentation for Archival

- [ ] **Archive WARP.md**
  - [ ] Move to: `.archive/docs/WARP.md`
  - [ ] Add header comment in moved file:
    ```markdown
    # WARP.md - ARCHIVED

    **Archived:** 2025-12-02
    **Reason:** Duplicate of README.md developer section
    **Original Location:** /WARP.md

    [Rest of original content]
    ```

- [ ] **Archive and replace claude-code-skills-agents-guidelines-0.4.md**
  - [ ] Move to: `.archive/versioned-docs/guidelines-v0.4/claude-code-skills-agents-guidelines-0.4.md`
  - [ ] Create new: `docs/ARCHITECTURE.md` (current version, unversioned)
  - [ ] New file includes:
    - [ ] Best practices from 0.4 version
    - [ ] Updated for current state
    - [ ] "See .archive/ for v0.4 guidelines" reference

  - [ ] Create version index: `.archive/versioned-docs/README.md`
    ```markdown
    # Versioned Documentation Archive

    Historical versions of evolving documentation:

    ## Architecture Guidelines
    - [v0.4](./guidelines-v0.4/) - Initial release (Dec 2025)
    - [v0.5](./guidelines-v0.5/) - TBD

    Note: Current active documentation is in `/docs/` root.
    ```

- [ ] **Handle agent-runner.md**
  - [ ] Check if current and maintained
  - [ ] If outdated: Archive to `.archive/docs/agent-runner.md`
  - [ ] If current: Keep in place, ensure updated in versioning work

- [ ] **Clean .claude.local-backup**
  - [ ] Confirm these are local backups (not needed in repo)
  - [ ] Remove from git tracking:
    ```bash
    git rm -r --cached .claude.local-backup-*
    git commit -m "chore: remove local backup directory from tracking"
    ```
  - [ ] Update .gitignore:
    - [ ] Add: `.claude.local-backup*/`
  - [ ] Delete local directory if you have one

### CCD.4: Update Documentation Links

- [ ] **Update README.md**
  - [ ] Remove/update references to archived docs
  - [ ] Add reference to active docs in `docs/` folder
  - [ ] Ensure all links point to current versions

- [ ] **Update CONTRIBUTING.md**
  - [ ] Update references to archived architecture guidelines
  - [ ] Link to new `docs/ARCHITECTURE.md`
  - [ ] Add section on versioning documentation (see below)

- [ ] **Create documentation index**
  - [ ] File: `docs/DOCUMENTATION-INDEX.md`
  - [ ] Purpose: Navigation hub for all active documentation
  - [ ] Categories:
    - [ ] Getting Started
    - [ ] Package Development
    - [ ] Architecture & Design
    - [ ] Marketplace Management
    - [ ] Version Management
    - [ ] Security & Trust

### CCD.5: Establish Documentation Versioning Policy

- [ ] **Create docs/VERSIONING.md for documentation**
  - [ ] How documentation versioning works
  - [ ] When to create a new version
  - [ ] When to update existing docs vs creating versioned copy
  - [ ] Archive strategy
  - [ ] Policy:
    - [ ] Active docs live in `docs/` without version numbers
    - [ ] When documentation fundamentally changes, keep old in `.archive/versioned-docs/`
    - [ ] Reference old versions in current docs with "See historical X" links
    - [ ] Archive at major version boundaries (e.g., 0.4 → 1.0)

- [ ] **Add to CONTRIBUTING.md:**
  - [ ] "Documentation Standards" section
  - [ ] Link to docs/VERSIONING.md
  - [ ] Requirements:
    - [ ] No version numbers in filenames (use `.archive/versioned-docs/` for old versions)
    - [ ] Files should be evergreen (update in place)
    - [ ] Major rewrites should preserve old version in archive
    - [ ] All docs should have "Last Updated" date in header

### CCD.6: Git Cleanup Commit

- [ ] **Create cleanup PR/commit**
  - [ ] Commit message:
    ```
    chore(docs): archive outdated documentation and create .archive structure

    - Move WARP.md to .archive/docs/
    - Move guidelines-0.4 to .archive/versioned-docs/
    - Create new docs/ARCHITECTURE.md (current version)
    - Add .archive/ to .gitignore
    - Create docs/DOCUMENTATION-INDEX.md
    - Create .archive/README.md with index
    - Remove .claude.local-backup-* from tracking
    ```

  - [ ] Files changed:
    - [ ] Moved: WARP.md → .archive/docs/WARP.md
    - [ ] Moved: docs/claude-code-skills-agents-guidelines-0.4.md → .archive/versioned-docs/guidelines-v0.4/
    - [ ] Created: docs/ARCHITECTURE.md
    - [ ] Created: docs/DOCUMENTATION-INDEX.md
    - [ ] Created: .archive/README.md
    - [ ] Created: .archive/versioned-docs/README.md
    - [ ] Modified: .gitignore
    - [ ] Modified: README.md (if needed)

---

## Priority 2: Version/Release Tracking ✅ COMPLETE

**Goal:** Establish clear version history, changelog practices, and compatibility tracking
**Impact:** Users understand what changed, breaking changes are documented, upgrades are safe
**Timeline Estimate:** 2-3 days (AFTER CCS complete)

### Phase 2.1: CHANGELOG Implementation
- [ ] **Create CHANGELOG.md template**
  - [ ] File: `templates/CHANGELOG.template.md`
  - [ ] Include sections: Unreleased, versions in descending order
  - [ ] Format for each version: version number, release date, sections (Added, Changed, Deprecated, Removed, Fixed, Security)
  - [ ] Include template with examples from existing packages

**Template structure:**
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- List of new features coming soon

### Changed
- Behavioral changes

### Deprecated
- Features to be removed in next major version

### Security
- Security updates

## [1.0.0] - 2025-12-01
### Added
- Initial stable release
- Feature X

### Changed
- Improved performance of feature Y

### Fixed
- Fixed bug in feature Z
```

- [ ] **Add CHANGELOG.md to all existing packages**
  - [ ] `packages/delay-tasks/CHANGELOG.md`
    - [ ] Document v1.0.0 as initial release
    - [ ] Backfill any historical changes if available
  - [ ] `packages/git-worktree/CHANGELOG.md`
    - [ ] Document v1.0.0 as initial release
    - [ ] Note: Tier 1 package with token substitution
  - [ ] `packages/sc-manage/CHANGELOG.md`
    - [ ] Document v0.4.0 with date
    - [ ] Note: Currently in beta (0.x)
  - [ ] `packages/repomix-nuget/CHANGELOG.md`
    - [ ] Document v0.4.0 with date
    - [ ] Note: Currently in beta (0.x)

- [ ] **Establish CHANGELOG standards**
  - [ ] Add to CONTRIBUTING.md:
    - [ ] CHANGELOG.md is mandatory for all packages
    - [ ] Update CHANGELOG.md on every commit/PR that changes package behavior
    - [ ] Keep "Unreleased" section at top
    - [ ] Use consistent formatting (Keep a Changelog format)
    - [ ] Be specific about breaking changes with migration guidance

- [ ] **Create CHANGELOG review checklist**
  - [ ] Add to PR template: "CHANGELOG.md updated?"
  - [ ] Reviewers verify CHANGELOG entries match code changes
  - [ ] Breaking changes are clearly flagged

### Phase 2.2: Version Compatibility Matrix
- [ ] **Document version support timeline**
  - [ ] Create `docs/version-support-policy.md` with:
    - [ ] SemVer explanation and package expectations
    - [ ] Support window duration (e.g., minor versions supported for 12 months)
    - [ ] When 0.x versions graduate to 1.0.0
    - [ ] Deprecation timeline (e.g., 6 months notice before removal)
    - [ ] Long-term support (LTS) designation criteria

- [ ] **Create version compatibility matrix**
  - [ ] File: `docs/version-compatibility.md`
  - [ ] Format: Table showing package versions vs Claude Code versions
  - [ ] Indicate which package versions work with which Claude versions
  - [ ] Include minimum/maximum version constraints
  - [ ] Flag deprecated versions with removal date
  - [ ] Document cross-package compatibility if applicable

**Example matrix:**
```markdown
| Package | Version | Claude Code | Status | EOL Date |
|---------|---------|-------------|--------|----------|
| delay-tasks | 1.0.0 | 0.4.0+ | Current | TBD |
| git-worktree | 1.0.0 | 0.4.0+ | Current | TBD |
| sc-manage | 0.4.0 | 0.4.0+ | Beta | 2025-03-01 |
| repomix-nuget | 0.4.0 | 0.4.0+ | Beta | 2025-03-01 |
```

- [ ] **Add version info to package manifests**
  - [ ] Add `deprecated: false` field (true if deprecated)
  - [ ] Add `end_of_life` date field if applicable
  - [ ] Add `minimum_claude_version` field
  - [ ] Add `tested_with_claude_versions` array

- [ ] **Add version compatibility checks**
  - [ ] Extend `tools/sc-install.py` to check version compatibility
  - [ ] Warn user if installing package incompatible with their Claude version
  - [ ] Suggest alternative versions if available

### Phase 2.3: Release Notes and Upgrade Guides
- [ ] **Create release notes template**
  - [ ] File: `templates/RELEASE-NOTES.template.md`
  - [ ] Include: summary, key features, bug fixes, breaking changes, migration guide, contributors
  - [ ] Location for release notes: `packages/<name>/docs/releases/<version>.md`

- [ ] **Document upgrade paths**
  - [ ] Create `UPGRADE.md` template for each package
  - [ ] For 0.x → 1.0.0 transitions:
    - [ ] List all breaking changes
    - [ ] Provide before/after code examples
    - [ ] Document new features and benefits
  - [ ] Document rollback procedures (downgrading)

- [ ] **Update package READMEs**
  - [ ] Add "Version History" section linking to CHANGELOG
  - [ ] Add "Upgrade Guide" section if major version available
  - [ ] Add badge showing current version and stability status

**Example badge:**
```markdown
![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-blue)
![Status: Stable](https://img.shields.io/badge/status-stable-green)
```

### Phase 2.4: Automated Version Tracking
- [ ] **Create version verification script**
  - [ ] File: `scripts/verify-versions.sh`
  - [ ] Check version.yaml matches all package manifest.yaml versions
  - [ ] Verify all agents have matching version in frontmatter
  - [ ] Verify CHANGELOG.md entries exist for all versions
  - [ ] Run in CI/CD on every commit

- [ ] **Add version constraints to registry build**
  - [ ] Registry generation includes version audit report
  - [ ] Flag version mismatches as errors
  - [ ] Generate version report in `docs/version-report.json`

- [ ] **Set up version bump workflow**
  - [ ] Document version bumping process in CONTRIBUTING.md
  - [ ] Create `scripts/bump-version.sh` script that:
    - [ ] Updates version.yaml
    - [ ] Updates all manifest.yaml files
    - [ ] Updates agent frontmatter versions
    - [ ] Creates git commit with version tag

---

## Priority 3: Sparse Documentation 🟡 IN PROGRESS (Item 1 Done)

**Goal:** Expand package documentation with integration guides, troubleshooting, and use cases
**Impact:** Users understand when/why to use packages, can solve problems independently
**Timeline Estimate:** 5-7 days

### Phase 3.1: Use Case Documentation
- [ ] **Define use case documentation structure**
  - [ ] Create `templates/USE-CASES.template.md`
  - [ ] Include sections: problem statement, solution, when to use, when not to use, similar packages, getting started
  - [ ] Include decision tree if package has multiple usage patterns

- [ ] **Add use case docs to each package**
  - [ ] `packages/delay-tasks/docs/USE-CASES.md`
    - [ ] Use case 1: CI/CD polling (GitHub Actions, GitLab CI, etc.)
    - [ ] Use case 2: Batch processing with retries
    - [ ] Use case 3: Wait for external system readiness
    - [ ] Use case 4: Rate limiting and backoff strategies
    - [ ] Include: when to choose delay-once vs delay-poll vs git-pr-check-delay
    - [ ] Performance considerations and limits

  - [ ] `packages/git-worktree/docs/USE-CASES.md`
    - [ ] Use case 1: Parallel feature development
    - [ ] Use case 2: Bug fix isolation
    - [ ] Use case 3: Release management
    - [ ] Use case 4: Experimental branches
    - [ ] Include: team workflow examples, integration with other tools
    - [ ] Safety considerations and gotchas

  - [ ] `packages/sc-manage/docs/USE-CASES.md`
    - [ ] Use case 1: Initial marketplace setup
    - [ ] Use case 2: Managing multiple Claude projects
    - [ ] Use case 3: Custom package development
    - [ ] Use case 4: Package distribution
    - [ ] Include: permissions management

  - [ ] `packages/repomix-nuget/docs/USE-CASES.md`
    - [ ] Use case 1: NuGet API documentation generation
    - [ ] Use case 2: C# project onboarding
    - [ ] Use case 3: Integration with documentation systems
    - [ ] Include: performance for large codebases
    - [ ] Compatibility with .NET versions

### Phase 3.2: Integration Guides
- [ ] **Create multi-package workflow documentation**
  - [ ] File: `docs/integration-guides.md`
  - [ ] Example 1: Using git-worktree + sc-manage to bootstrap new environments
  - [ ] Example 2: Using delay-tasks + git-worktree for automated branch cleanup
  - [ ] Example 3: Using repomix-nuget + sc-manage for documentation workflow
  - [ ] Each example includes: prerequisites, step-by-step instructions, expected outputs, troubleshooting

- [ ] **Create per-package integration documentation**
  - [ ] `packages/<name>/docs/INTEGRATIONS.md` for each package
    - [ ] Which other Synaptic Canvas packages work with this one
    - [ ] External tools it integrates with
    - [ ] Example workflows combining packages
    - [ ] Configuration for common scenarios

- [ ] **Add integration examples to package READMEs**
  - [ ] "See Integration Guides" section in each README
  - [ ] Links to integration docs for common workflows
  - [ ] Quick reference for combining packages

### Phase 3.3: Troubleshooting Guides
- [ ] **Create troubleshooting template**
  - [ ] File: `templates/TROUBLESHOOTING.template.md`
  - [ ] Format: error code/message → likely causes → solutions
  - [ ] Include: system requirements checklist, common misconfigurations, how to gather diagnostics

- [ ] **Add troubleshooting guides to each package**
  - [ ] `packages/delay-tasks/docs/TROUBLESHOOTING.md`
    - [ ] "Python not found" - diagnosis and solutions
    - [ ] "Polling timeout" - understanding timeout behavior
    - [ ] "Action not executing" - debugging command execution
    - [ ] "Heartbeat spam" - configuring verbosity
    - [ ] Common misconceptions about delay behavior

  - [ ] `packages/git-worktree/docs/TROUBLESHOOTING.md`
    - [ ] "Worktree creation failed" - permissions, branch conflicts
    - [ ] "Tracking document not found" - setup issues
    - [ ] "Dirty worktree rejected" - understanding safety checks
    - [ ] "Branch protection violations" - policy issues
    - [ ] Recovery procedures for stuck worktrees

  - [ ] `packages/sc-manage/docs/TROUBLESHOOTING.md`
    - [ ] "Package not found" - registry issues
    - [ ] "Installation failed" - permissions, missing dependencies
    - [ ] "Uninstall not working" - cleanup procedures
    - [ ] Local vs global scope confusion
    - [ ] Registry update issues

  - [ ] `packages/repomix-nuget/docs/TROUBLESHOOTING.md`
    - [ ] "Node not found" - installation and PATH issues
    - [ ] "Output file too large" - compression, filtering options
    - [ ] "Timeout during generation" - large codebase handling
    - [ ] "Registry resolution failed" - URL and network issues
    - [ ] XML validation errors

- [ ] **Create error reference document**
  - [ ] File: `docs/error-reference.md`
  - [ ] Centralized error code registry across all packages
  - [ ] Standardized error format including error code
  - [ ] Each error includes: meaning, common causes, solutions, links to detailed guides

- [ ] **Add diagnostic tools**
  - [ ] Script: `scripts/diagnose.sh`
    - [ ] Checks environment (Python, Node, Git versions)
    - [ ] Verifies package installations
    - [ ] Lists installed packages and versions
    - [ ] Checks for common configuration issues
    - [ ] Generates diagnostic report for troubleshooting

### Phase 3.4: Advanced Features Documentation
- [ ] **Document advanced usage for each package**
  - [ ] `packages/delay-tasks/docs/ADVANCED.md`
    - [ ] Custom polling strategies
    - [ ] Combining multiple delay modes
    - [ ] Performance tuning
    - [ ] Edge cases and limitations

  - [ ] `packages/git-worktree/docs/ADVANCED.md`
    - [ ] Custom token substitution
    - [ ] Integration with CI/CD systems
    - [ ] Multi-repository setups
    - [ ] Automation and scripting

  - [ ] `packages/repomix-nuget/docs/ADVANCED.md`
    - [ ] Custom filtering rules
    - [ ] Performance optimization for large repos
    - [ ] Registry configuration
    - [ ] Output format customization

- [ ] **Add best practices guides**
  - [ ] `packages/<name>/docs/BEST-PRACTICES.md` for each package
  - [ ] Common anti-patterns to avoid
  - [ ] Performance optimization tips
  - [ ] Security considerations
  - [ ] Team workflows and conventions

### Phase 3.5: Documentation Index
- [ ] **Create central documentation hub**
  - [ ] File: `docs/DOCUMENTATION-INDEX.md`
  - [ ] Comprehensive navigation to all package docs
  - [ ] Quick links by topic: installation, usage, troubleshooting, integration, advanced
  - [ ] Search/discovery aids for different user personas

- [ ] **Update main README.md**
  - [ ] Add "Documentation" section with links to all guides
  - [ ] Update package table with link to each package's docs
  - [ ] Add "Get Help" section with common resources

---

## Priority 4: Security Indicators

**Goal:** Build trust through publisher verification, security scanning, and transparency
**Impact:** Users know packages are safe, maintainers are legitimate, vulnerabilities are caught early
**Timeline Estimate:** 4-5 days

### Phase 4.1: Publisher Verification
- [ ] **Define publisher verification levels**
  - [ ] Create `docs/publisher-verification.md` with levels:
    - [ ] Level 0: No verification (default for new packages)
    - [ ] Level 1: Email domain verification (proof of ownership)
    - [ ] Level 2: Organization verification (GitHub org or verified entity)
    - [ ] Level 3: Security audit passed (code review + security scan)

- [ ] **Implement verification badges**
  - [ ] Update manifest schema to include `security.verification_level`
  - [ ] Add `security.verified_date` field
  - [ ] Add `security.auditor` field (who verified)
  - [ ] Badges in registry.json:
    - [ ] `verified_publisher: boolean`
    - [ ] `security_level: 0|1|2|3`
    - [ ] `last_verified: ISO8601 timestamp`

- [ ] **Verify current publishers**
  - [ ] Document publisher for each existing package
  - [ ] All packages currently: `author: synaptic-canvas`
  - [ ] Mark as Level 2 (organization verified via GitHub)
  - [ ] Add verification badge to registry

- [ ] **Create publisher verification process**
  - [ ] Document in CONTRIBUTING.md:
    - [ ] How new publishers submit for verification
    - [ ] Email verification process
    - [ ] Organization verification requirements
    - [ ] Appeal process for disputes
  - [ ] Establish verification workflow (GitHub issue template, checklist)

- [ ] **Add publisher profiles to registry**
  - [ ] Extend registry format to include `publishers` section:
```json
{
  "publishers": {
    "randlee": {
      "name": "Randall Lee",
      "github": "randlee",
      "verification_level": 1,
      "verified_date": "2025-12-01T00:00:00Z",
      "packages": ["delay-tasks", "git-worktree", "sc-manage", "repomix-nuget"],
      "profile_url": "https://github.com/randlee"
    }
  }
}
```

### Phase 4.2: Security Scanning and Status
- [ ] **Define security scanning requirements**
  - [ ] Create `docs/security-scanning-policy.md` with:
    - [ ] What scans run on each package
    - [ ] Frequency of scans (on release, monthly, etc.)
    - [ ] Passing/failing criteria
    - [ ] CVE and vulnerability handling

- [ ] **Implement automated security checks**
  - [ ] Script: `scripts/security-scan.sh`
    - [ ] Dependency vulnerability scanning (for Python/Node packages)
    - [ ] Static code analysis if applicable
    - [ ] Secrets detection (no API keys, credentials)
    - [ ] License compliance check
    - [ ] Generates security report

- [ ] **Add security metadata to manifests**
  - [ ] New manifest fields:
    - [ ] `security.scanned: boolean`
    - [ ] `security.last_scan_date: ISO8601 timestamp`
    - [ ] `security.vulnerabilities: array` (CVE list if any)
    - [ ] `security.status: safe|warning|critical`

- [ ] **Publish security scan results**
  - [ ] Add `security_status` to registry entries
  - [ ] Create `docs/security-report.md` with results
  - [ ] Include dates of scans, any findings, remediation status

- [ ] **Set up CI/CD security checks**
  - [ ] GitHub Actions workflow:
    - [ ] Runs on every PR
    - [ ] Scans package changes for security issues
    - [ ] Blocks merge if critical vulnerabilities found
    - [ ] Reports findings in PR

### Phase 4.3: Dependency Security
- [ ] **Document dependency requirements clearly**
  - [ ] Update manifest schema to include:
    - [ ] `requires.<package>.version: string` (e.g., "python3 >= 3.8")
    - [ ] `requires.<package>.security_requirements: array` (e.g., ["no-eval"])
    - [ ] Add explanatory notes for why each dependency is needed

- [ ] **Create dependency audit process**
  - [ ] For Python dependencies:
    - [ ] Check pip packages for known CVEs using `safety check`
    - [ ] Pin or range-lock versions in requirements.txt
  - [ ] For Node dependencies:
    - [ ] Check npm packages for vulnerabilities using `npm audit`
    - [ ] Pin or range-lock versions in package-lock.json
  - [ ] For system tools (git, bash):
    - [ ] Document minimum versions that include security fixes
    - [ ] Warn users if they have older versions

- [ ] **Add dependency reports to packages**
  - [ ] File: `packages/<name>/docs/DEPENDENCIES.md` for each package
  - [ ] List all dependencies with:
    - [ ] Version requirement
    - [ ] Why it's needed
    - [ ] Known vulnerabilities (if any)
    - [ ] Installation instructions
    - [ ] Security considerations

### Phase 4.4: Vulnerability Disclosure and Response
- [ ] **Create security policy**
  - [ ] File: `SECURITY.md` in repo root
  - [ ] Responsible disclosure process
  - [ ] Security contact email
  - [ ] How to report vulnerabilities (GitHub Security Advisory)
  - [ ] Expected response timeline
  - [ ] CVE assignment process
  - [ ] Security update distribution

- [ ] **Set up vulnerability tracking**
  - [ ] Create GitHub Security Advisory for this repo
  - [ ] Subscribe to CVE feeds for dependencies
  - [ ] Monitor security mailing lists
  - [ ] Quarterly security review process

- [ ] **Document security advisory process**
  - [ ] File: `docs/security-advisory-process.md`
  - [ ] Steps to follow when vulnerability discovered
  - [ ] Severity assessment framework
  - [ ] Patch development timeline
  - [ ] Notification and release procedures
  - [ ] Post-release communication

### Phase 4.5: Security Indicators in Registry and UI
- [ ] **Extend registry with security metadata**
  - [ ] Add to each package entry:
```json
{
  "package_name": {
    "security": {
      "verified_publisher": true,
      "security_level": 2,
      "scanned": true,
      "last_scan": "2025-12-01T00:00:00Z",
      "vulnerabilities": [],
      "dependencies_audited": true,
      "license": "MIT"
    }
  }
}
```

- [ ] **Update package READMEs with security badges**
  - [ ] Add badge showing:
    - [ ] Publisher verification level
    - [ ] Last security scan date
    - [ ] License
    - [ ] Dependency audit status
  - [ ] Example badges:
    ```markdown
    ![Publisher Verified](https://img.shields.io/badge/publisher-verified-green)
    ![Security Scanned](https://img.shields.io/badge/security-scanned-blue)
    ![Vulnerabilities](https://img.shields.io/badge/vulnerabilities-0-green)
    ![License MIT](https://img.shields.io/badge/license-MIT-green)
    ```

- [ ] **Create security dashboard (future web UI)**
  - [ ] Mockup: `docs/ui-mockups/security-dashboard.md`
  - [ ] Shows security status of all packages at a glance
  - [ ] Vulnerability alerts
  - [ ] Publisher verification status
  - [ ] Last security scan date
  - [ ] Remediation actions for issues

### Phase 4.6: Trust Indicators in Discovery
- [ ] **Update package listing with trust indicators**
  - [ ] Each package shows:
    - [ ] Publisher name with verification badge
    - [ ] Security status (safe/warning/critical)
    - [ ] Last security scan date
    - [ ] Download/usage count
    - [ ] Maintenance status (actively maintained, deprecated, archived)
  - [ ] Color coding for quick visual assessment

- [ ] **Add maintenance status tracking**
  - [ ] Add to manifest: `maintenance.status: active|inactive|archived`
  - [ ] Add to manifest: `maintenance.last_update: ISO8601 timestamp`
  - [ ] Add to manifest: `maintenance.support_until: ISO8601 timestamp`
  - [ ] Update registry with maintenance status
  - [ ] Warn users about inactive/archived packages

---

## Implementation Sequence and Dependencies

### Foundation Week (Days 1-5): Version System & Document Cleanup
**Must complete BEFORE other work - foundation for everything else**

**Days 1-2: Version Management System (CCS)**
- [ ] CCS.1: Assess current version mismatches
- [ ] CCS.2: Establish versioning hierarchy and strategy
  - [ ] Create `docs/versioning-strategy.md`
  - [ ] Decide on version.yaml role
- [ ] Fix package manifest versions (if needed)
- [ ] Update all agent frontmatter to match package versions
- [ ] Add version to ALL commands (Phase CCS.3)
- [ ] Add version to ALL skills (Phase CCS.3)
- [ ] Create frontmatter templates (Phase CCS.3)

**Days 3-4: Version Scripts & Automation (CCS)**
- [ ] Create `scripts/audit-versions.sh` (Phase CCS.4)
- [ ] Create `scripts/sync-versions.py` (Phase CCS.4)
- [ ] Create `scripts/compare-versions.sh` (Phase CCS.4)
- [ ] Update registry with version metadata (Phase CCS.5)
- [ ] Add version audit to CI/CD (Phase CCS.4)

**Day 5: Document Cleanup (CCD)**
- [ ] Create .archive directory structure (Phase CCD.1)
- [ ] Update .gitignore (Phase CCD.1)
- [ ] Archive WARP.md (Phase CCD.3)
- [ ] Archive guidelines-0.4.md (Phase CCD.3)
- [ ] Remove .claude.local-backup from tracking (Phase CCD.3)
- [ ] Create archive index (Phase CCD.1 & CCD.3)
- [ ] Create cleanup commit

### Week 1: Registry Metadata + Versioning Docs
**Days 1-2: Registry Schema (Priority 1)**
- [ ] Create registry schema v2.0 (Phase 1.1-1.3)
- [ ] Update registry generation script
- [ ] Test with all existing packages

**Days 3-4: Release Tracking (Priority 2)**
- [ ] Add CHANGELOG.md to all packages (Phase 2.1)
- [ ] Create version support policy (Phase 2.2)
- [ ] Create version compatibility matrix
- [ ] Create CHANGELOG templates

**Day 5: Documentation Hub**
- [ ] Create `docs/DOCUMENTATION-INDEX.md` (Phase CCD.4)
- [ ] Create `docs/ARCHITECTURE.md` from archived v0.4 guide (Phase CCD.3)
- [ ] Create `docs/version-management-guide.md` (Phase CCS.6)
- [ ] Update CONTRIBUTING.md with new sections (Phase CCS.6 & CCD.5)

### Week 2: Documentation Expansion (Priority 3)
**Days 1-2: Use Cases & Integration (Phase 3)**
- [ ] Create use case templates (Phase 3.1)
- [ ] Add USE-CASES.md to all packages (Phase 3.1)
- [ ] Create integration guides (Phase 3.2)
- [ ] Add INTEGRATIONS.md to packages (Phase 3.2)

**Days 3-4: Troubleshooting & Advanced (Phase 3)**
- [ ] Create troubleshooting templates (Phase 3.3)
- [ ] Add TROUBLESHOOTING.md to all packages (Phase 3.3)
- [ ] Create diagnostic tool (Phase 3.3)
- [ ] Add ADVANCED.md to packages (Phase 3.4)
- [ ] Add BEST-PRACTICES.md to packages (Phase 3.4)

**Day 5: Documentation Polish**
- [ ] Create error reference document (Phase 3.3)
- [ ] Update all package READMEs with new links
- [ ] Final doc link verification
- [ ] Create DOCUMENTATION-STATUS.md (Phase CCD.2)

### Week 3: Security & Final Integration (Priority 4)
**Days 1-2: Security Infrastructure (Phase 4)**
- [ ] Define publisher verification levels (Phase 4.1)
- [ ] Create security scanning script (Phase 4.2)
- [ ] Create SECURITY.md policy (Phase 4.3)
- [ ] Create security advisory process (Phase 4.4)

**Days 3-4: Security Implementation (Phase 4)**
- [ ] Update manifests with security fields (Phase 4.2)
- [ ] Verify current publishers (Phase 4.1)
- [ ] Add security metadata to registry (Phase 4.5)
- [ ] Create publisher profiles in registry (Phase 4.1)
- [ ] Add security badges to READMEs (Phase 4.5 & 4.6)

**Day 5: Final Polish & Release**
- [ ] Run full audit: `scripts/audit-versions.sh`
- [ ] Verify registry generation
- [ ] Test all CI/CD checks
- [ ] Update main README with complete links
- [ ] Create release PR with all changes
- [ ] Final testing and review

---

## Success Criteria

### Registry Metadata
- [ ] Registry.json includes: description, author, tags, scope, requires, download_count, security_status
- [ ] Registry validation passes with schema v2.0
- [ ] All packages properly represented in enriched registry
- [ ] Backward compatibility maintained (v1 still accessible)

### Version/Release Tracking
- [ ] All packages have CHANGELOG.md files
- [ ] Version compatibility matrix exists and is accurate
- [ ] Release notes available for significant versions
- [ ] Version verification script passes all checks
- [ ] Upgrade guides provided for major versions

### Documentation
- [ ] Each package has: USE-CASES.md, TROUBLESHOOTING.md, optional ADVANCED.md
- [ ] Integration guides show real workflows combining packages
- [ ] DOCUMENTATION-INDEX.md provides clear navigation
- [ ] Diagnostic tool helps users troubleshoot independently
- [ ] All links in documentation are valid

### Security Indicators
- [ ] Publishers verified in registry
- [ ] Security scanning results published
- [ ] Security badges appear on package READMEs
- [ ] Vulnerability disclosure policy established
- [ ] Security metadata in registry entries

---

## File Checklist

### New Files to Create (Foundation)
**Version Management System (CCS):**
- [ ] `docs/versioning-strategy.md` - Three-layer version management
- [ ] `docs/version-management-guide.md` - How to manage versions
- [ ] `scripts/audit-versions.sh` - Version consistency verification
- [ ] `scripts/sync-versions.py` - Bulk version updates
- [ ] `scripts/compare-versions.sh` - Version comparison tool
- [ ] `templates/agent-frontmatter.template.yaml` - Agent YAML template
- [ ] `templates/command-frontmatter.template.yaml` - Command YAML template
- [ ] `templates/skill-frontmatter.template.yaml` - Skill YAML template
- [ ] `.github/workflows/version-audit.yml` - CI/CD version checking

**Document Cleanup (CCD):**
- [ ] `.archive/README.md` - Archive index and purpose
- [ ] `.archive/docs/WARP.md` - Archived WARP.md
- [ ] `.archive/versioned-docs/README.md` - Versioned docs index
- [ ] `.archive/versioned-docs/guidelines-v0.4/claude-code-skills-agents-guidelines-0.4.md` - Archived guidelines
- [ ] `docs/ARCHITECTURE.md` - Current architecture guide (replaces archived v0.4)
- [ ] `docs/DOCUMENTATION-STATUS.md` - Inventory of all docs and status

### New Files to Create (Priority 1-4)
**Registry & Metadata (Priority 1):**
- [ ] `docs/registry-schema-v2.md` - Registry format documentation
- [ ] `docs/registry-api.md` - Registry programmatic access guide
- [ ] `scripts/generate-registry.py` - Registry generation script

**Version/Release Tracking (Priority 2):**
- [ ] `docs/version-support-policy.md` - Version lifecycle policy
- [ ] `docs/version-compatibility.md` - Compatibility matrix
- [ ] `templates/CHANGELOG.template.md` - CHANGELOG template
- [ ] `templates/RELEASE-NOTES.template.md` - Release notes template

**Documentation (Priority 3):**
- [ ] `docs/DOCUMENTATION-INDEX.md` - Documentation hub
- [ ] `docs/integration-guides.md` - Multi-package workflows
- [ ] `docs/error-reference.md` - Centralized error registry
- [ ] `templates/manifest.template.yaml` - Manifest template
- [ ] `templates/USE-CASES.template.md` - Use case template
- [ ] `templates/TROUBLESHOOTING.template.md` - Troubleshooting template
- [ ] `templates/BEST-PRACTICES.template.md` - Best practices template
- [ ] `templates/ADVANCED.template.md` - Advanced features template
- [ ] `scripts/diagnose.sh` - Diagnostic tool

**Security (Priority 4):**
- [ ] `SECURITY.md` - Security policy in repo root
- [ ] `docs/publisher-verification.md` - Publisher verification process
- [ ] `docs/security-scanning-policy.md` - Security scanning standards
- [ ] `docs/security-advisory-process.md` - Vulnerability handling
- [ ] `scripts/security-scan.sh` - Security scanning

### Files to Modify (Foundation - Artifact Versions)
**Add version to ALL artifact frontmatter:**
- [ ] `packages/delay-tasks/commands/delay.md` - Add version: 1.0.0
- [ ] `packages/delay-tasks/skills/delaying-tasks/SKILL.md` - Add version: 1.0.0
- [ ] `packages/delay-tasks/agents/delay-once.md` - Update to version: 1.0.0
- [ ] `packages/delay-tasks/agents/delay-poll.md` - Update to version: 1.0.0
- [ ] `packages/delay-tasks/agents/git-pr-check-delay.md` - Update to version: 1.0.0
- [ ] `packages/git-worktree/commands/git-worktree.md` - Add version: 1.0.0
- [ ] `packages/git-worktree/skills/managing-worktrees/SKILL.md` - Add version: 1.0.0
- [ ] `packages/git-worktree/agents/worktree-create.md` - Update to version: 1.0.0
- [ ] `packages/git-worktree/agents/worktree-scan.md` - Update to version: 1.0.0
- [ ] `packages/git-worktree/agents/worktree-cleanup.md` - Update to version: 1.0.0
- [ ] `packages/git-worktree/agents/worktree-abort.md` - Update to version: 1.0.0
- [ ] `packages/sc-manage/commands/sc-manage.md` - Add version: 0.4.0
- [ ] `packages/sc-manage/skills/managing-sc-packages/SKILL.md` - Add version: 0.4.0
- [ ] `packages/sc-manage/agents/sc-packages-list.md` - Update to version: 0.4.0
- [ ] `packages/sc-manage/agents/sc-package-install.md` - Update to version: 0.4.0
- [ ] `packages/sc-manage/agents/sc-package-uninstall.md` - Update to version: 0.4.0
- [ ] `packages/sc-manage/agents/sc-package-docs.md` - Update to version: 0.4.0
- [ ] `packages/repomix-nuget/commands/repomix-nuget.md` - Add version: 0.4.0
- [ ] `packages/repomix-nuget/skills/generating-nuget-context/SKILL.md` - Add version: 0.4.0
- [ ] `packages/repomix-nuget/agents/repomix-generate.md` - Update to version: 0.4.0
- [ ] `packages/repomix-nuget/agents/registry-resolve.md` - Update to version: 0.4.0
- [ ] `packages/repomix-nuget/agents/context-assemble.md` - Update to version: 0.4.0

**Update metadata/documentation:**
- [ ] `version.yaml` - Add clarifying comment about being platform version
- [ ] `.gitignore` - Add .archive/ and .claude.local-backup*/
- [ ] `CONTRIBUTING.md` - Add versioning requirements and standards sections

### Files to Update or Create (Priority 1-4)
**Package Documentation (4 packages × 5+ files):**
- [ ] `packages/delay-tasks/CHANGELOG.md` - Add
- [ ] `packages/delay-tasks/docs/USE-CASES.md` - Add
- [ ] `packages/delay-tasks/docs/INTEGRATIONS.md` - Add
- [ ] `packages/delay-tasks/docs/TROUBLESHOOTING.md` - Add
- [ ] `packages/delay-tasks/docs/ADVANCED.md` - Add
- [ ] `packages/delay-tasks/docs/BEST-PRACTICES.md` - Add
- [ ] `packages/delay-tasks/docs/DEPENDENCIES.md` - Add
- [ ] [Repeat for git-worktree, sc-manage, repomix-nuget]

**Core Documentation:**
- [ ] `docs/registries/nuget/registry.json` - Enhance with v2.0 metadata
- [ ] `README.md` - Add documentation links, version info, badges
- [ ] `CONTRIBUTING.md` - Update with version/doc/security sections
- [ ] `.github/workflows/` - Add version-audit.yml workflow

**Total New/Modified Files: ~60+ changes**

---

## Notes and Constraints

### Scope
- Focus on registry metadata, versioning, documentation, and security indicators
- Web UI for discovery is Phase 2 (not in this plan)
- Analytics/download tracking is Phase 2 (tracked in registry but not fully implemented)

### Backward Compatibility
- Maintain v1 registry format for existing consumers
- All changes should be additive to manifests (no removals)
- Version bumping follows SemVer

### Dependencies
- Registry build depends on manifest updates (all at once)
- Documentation updates can be parallelized
- Security scanning depends on registry schema finalization

### External Dependencies
- Python modules: `pyyaml`, `requests` (already used)
- Bash utilities: `jq` (optional but recommended)
- GitHub Actions for CI/CD security scanning
- npm/pip for vulnerability scanning

### Future Considerations
- Web UI for package discovery (separate project)
- Package ratings and reviews system
- Automated package testing before release
- Dependency resolution and auto-installation
- Analytics and telemetry (opt-in)
- Package update notifications

---

## Review Checklist

Before marking complete:
- [ ] All checklist items completed
- [ ] Registry schema validated
- [ ] All packages have complete documentation
- [ ] Security scanning runs successfully
- [ ] Version verification passes
- [ ] CHANGELOG files populated
- [ ] Links in documentation tested
- [ ] PR created and reviewed
- [ ] Documentation deployed
- [ ] Announcement published

