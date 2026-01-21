# Releasing Synaptic Canvas

This document provides a step-by-step checklist for releasing new versions of Synaptic Canvas packages.

## Quick Reference

```bash
# Set version for all packages + marketplace
python3 scripts/set-package-version.py --all --marketplace <version>

# Validate everything
python3 scripts/validate-all.py

# Commit & PR
git add -A && git commit -m "chore: release v<version>"
git push && gh pr create --base main
```

---

## Release Types

| Type | Command | When to Use |
|------|---------|-------------|
| **Marketplace Release** | `--all --marketplace X.Y.Z` | Major releases, all packages together |
| **All Packages** | `--all X.Y.Z` | Sync all packages to same version |
| **Single Package** | `<package> X.Y.Z` | Individual package update |

---

## Marketplace Release Checklist

Use this checklist for a full marketplace release (all packages + platform version).

### Pre-Release

- [ ] **1. Ensure clean working tree**
  ```bash
  git status  # Should show "nothing to commit"
  git pull    # Get latest changes
  ```

- [ ] **2. Determine version number**
  - Check current version: `cat version.yaml`
  - Follow [SemVer](https://semver.org/):
    - **PATCH** (0.8.1): Bug fixes only
    - **MINOR** (0.9.0): New features, backwards compatible
    - **MAJOR** (1.0.0): Breaking changes

### Version Bump

- [ ] **3. Preview changes (dry run)**
  ```bash
  python3 scripts/set-package-version.py --all --marketplace <version> --dry-run
  ```
  Review the output to ensure all expected files will be updated.

- [ ] **4. Apply version bump**
  ```bash
  python3 scripts/set-package-version.py --all --marketplace <version>
  ```

### Validation

- [ ] **5. Run full validation suite**
  ```bash
  python3 scripts/validate-all.py
  ```
  All validators must pass (except optional "Plugin JSON" which may skip).

- [ ] **6. Run tests**
  ```bash
  pytest tests/ -v
  ```

### Documentation

- [ ] **7. Update CHANGELOGs** (if significant changes)
  - Root `CHANGELOG.md` for marketplace-wide changes
  - Individual `packages/<pkg>/CHANGELOG.md` for package-specific changes

### Commit & PR

- [ ] **8. Review changes**
  ```bash
  git status
  git diff --stat
  ```

- [ ] **9. Commit**
  ```bash
  git add -A
  git commit -m "chore: release v<version>"
  ```

- [ ] **10. Push and create PR**
  ```bash
  git push origin develop
  gh pr create --base main --title "Release: v<version>" --body "## Summary
  - Marketplace version bump to v<version>
  - All packages updated to v<version>

  ## Validation
  - [x] All validation checks pass
  - [x] Tests pass
  "
  ```

- [ ] **11. Wait for CI checks**
  - All GitHub Actions must pass
  - Review any failures and fix if needed

- [ ] **12. Merge PR**
  ```bash
  gh pr merge --squash
  ```

### Post-Release

- [ ] **13. Create GitHub release** (optional)
  ```bash
  gh release create v<version> --title "v<version>" --notes "Release notes here"
  ```

---

## Single Package Release Checklist

For releasing a single package independently.

- [ ] **1. Check current version**
  ```bash
  cat packages/<package>/manifest.yaml | grep version
  ```

- [ ] **2. Preview changes**
  ```bash
  python3 scripts/set-package-version.py <package> <version> --dry-run
  ```

- [ ] **3. Apply version bump**
  ```bash
  python3 scripts/set-package-version.py <package> <version>
  ```

- [ ] **4. Validate**
  ```bash
  python3 scripts/validate-all.py
  ```

- [ ] **5. Update package CHANGELOG**
  - Edit `packages/<package>/CHANGELOG.md`

- [ ] **6. Commit**
  ```bash
  git add -A
  git commit -m "chore(<package>): release v<version>"
  ```

- [ ] **7. PR & merge**

---

## Troubleshooting

### Version Decrement Error

If you get "Version decrement not allowed":

```bash
# Use --force to override (use with caution)
python3 scripts/set-package-version.py --all <version> --force
```

### Validation Failures

If `validate-all.py` fails:

1. Check the specific validator that failed
2. Run it individually for details:
   ```bash
   python3 scripts/validate-marketplace-sync.py
   python3 scripts/validate-cross-references.py
   python3 scripts/audit-versions.py
   ```
3. Fix issues and re-run

### Registry Out of Sync

The `set-package-version.py` script automatically regenerates registries. If you need to manually regenerate:

```bash
python3 scripts/update-registry.py --all
```

---

## Files Modified by Version Bump

When you run `set-package-version.py --all --marketplace <version>`:

### Per Package (×10 packages)
- `packages/<pkg>/manifest.yaml`
- `packages/<pkg>/.claude-plugin/plugin.json`
- `packages/<pkg>/commands/*.md`
- `packages/<pkg>/skills/*/SKILL.md`
- `packages/<pkg>/agents/*.md`

### Registries (regenerated)
- `.claude-plugin/marketplace.json`
- `.claude-plugin/registry.json`
- `docs/registries/nuget/registry.json`

### Platform Version
- `version.yaml` (if `--marketplace` flag used)

---

## Related Documentation

- [Versioning Strategy](versioning-strategy.md) - Version numbering philosophy
- [Dependency Validation](DEPENDENCY-VALIDATION.md) - Validation details
- [Diagnostic Tools](DIAGNOSTIC-TOOLS.md) - Troubleshooting scripts
