# Troubleshooting

Common issues and solutions for sc-ci-automation.

## Table of Contents

1. [Configuration Issues](#configuration-issues)
2. [Build Failures](#build-failures)
3. [Test Failures](#test-failures)
4. [PR Creation Failures](#pr-creation-failures)
5. [Agent Invocation Issues](#agent-invocation-issues)
6. [Version Bumping Issues](#version-bumping-issues)
7. [General Debugging](#general-debugging)

---

## Configuration Issues

### Error: "Config not found"

**Symptom:** CI automation can't find configuration file.

**Cause:** Missing `.claude/ci-automation.yaml` or `.claude/config.yaml`.

**Solution:**

1. Create `.claude/ci-automation.yaml`:
   ```yaml
   upstream_branch: main
   build_command: dotnet build
   test_command: dotnet test
   warn_patterns:
     - "warning CS\\d+"
   allow_warnings: false
   auto_fix_enabled: true
   ```

2. Or let CI automation auto-detect and prompt you to save config on first run.

---

### Error: "Build command failed"

**Symptom:** Build command from config doesn't work.

**Cause:** Incorrect build command or path.

**Solution:**

1. Test build command manually:
   ```bash
   cd /path/to/repo
   dotnet build  # or your build command
   ```

2. Update config with working command:
   ```yaml
   build_command: dotnet build --configuration Release
   ```

3. Ensure `repo_root` is correct if not at repository root:
   ```yaml
   repo_root: src/
   ```

---

## Build Failures

### Error: "Build failed; unresolved errors"

**Symptom:** Build fails and `ci-fix-agent` can't auto-fix.

**Cause:** Complex build errors requiring manual intervention.

**Solution:**

1. Check build output for specific errors
2. Review `ci-root-cause-agent` analysis
3. Fix manually and re-run:
   ```
   /sc-ci-automation --build
   ```

**Common build issues:**
- Missing dependencies: Run `npm install`, `pip install -r requirements.txt`, etc.
- Syntax errors: Review code changes
- Version conflicts: Update dependency versions

---

### Error: "Dirty repo"

**Symptom:** Validation fails with "Working tree not clean".

**Cause:** Uncommitted changes in working directory.

**Solution:**

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "Your commit message"
   ```

2. **Stash changes temporarily:**
   ```bash
   git stash
   /sc-ci-automation --test
   git stash pop
   ```

3. **Allow dirty repo (not recommended):**
   ```
   /sc-ci-automation --allow-dirty
   ```
   (Note: This flag may not be implemented in v0.1.0)

---

## Test Failures

### Error: "Tests failed; some failures not auto-fixable"

**Symptom:** Tests fail and `ci-fix-agent` can't fix them.

**Cause:** Complex test failures or logic errors.

**Solution:**

1. Run tests locally with verbose output:
   ```bash
   dotnet test --verbosity detailed
   ```

2. Review failing test output
3. Fix test or implementation
4. Re-run CI:
   ```
   /sc-ci-automation --test
   ```

---

### Warning: "Warnings detected"

**Symptom:** Build succeeds but warnings block PR creation.

**Cause:** Compiler/linter warnings present; `allow_warnings: false` in config.

**Solution:**

1. **Fix warnings (recommended):**
   - Review warning messages
   - Update code to eliminate warnings
   - Re-run CI

2. **Allow warnings for this run:**
   ```
   /sc-ci-automation --allow-warnings --yolo
   ```

3. **Allow warnings globally:**
   ```yaml
   # .claude/ci-automation.yaml
   allow_warnings: true
   ```

---

## PR Creation Failures

### Error: "Auth required"

**Symptom:** PR creation fails with authentication error.

**Cause:** Missing `GITHUB_TOKEN` environment variable.

**Solution:**

1. **Set GitHub token:**
   ```bash
   export GITHUB_TOKEN=ghp_your_token_here
   ```

2. **Or authenticate with GitHub CLI:**
   ```bash
   gh auth login
   ```

3. **Verify authentication:**
   ```bash
   gh auth status
   ```

---

### Error: "PR creation failed: branch protection"

**Symptom:** Can't create PR to protected branch.

**Cause:** Branch protection rules prevent direct pushes.

**Solution:**

1. **Verify you're not pushing directly to protected branch:**
   - CI automation should create PR, not push directly
   - Check branch settings on GitHub

2. **Use correct target branch:**
   ```
   /sc-ci-automation --dest main --yolo
   ```

3. **Check permissions:**
   - Ensure you have write access to repository
   - Verify token has `repo` scope

---

### Error: "PR already exists"

**Symptom:** Can't create PR because one already exists.

**Cause:** PR for this branch already open.

**Solution:**

1. **Update existing PR:**
   ```bash
   git push origin your-branch --force-with-lease
   ```

2. **Close old PR and retry:**
   ```bash
   gh pr close <pr-number>
   /sc-ci-automation --yolo
   ```

---

## Agent Invocation Issues

### Error: "Agent not found in registry"

**Symptom:** Agent invocation fails with missing agent error.

**Cause:** Agent not registered in `.claude/agents/registry.yaml`.

**Solution:**

1. **Verify package installation:**
   ```bash
   python3 tools/sc-install.py list
   ```

2. **Reinstall package:**
   ```bash
   python3 tools/sc-install.py uninstall sc-ci-automation
   python3 tools/sc-install.py install sc-ci-automation
   ```

3. **Check registry:**
   ```bash
   cat .claude/agents/registry.yaml | grep ci-
   ```

---

### Error: "Agent version mismatch"

**Symptom:** Agent Runner reports version constraint violation.

**Cause:** Installed agent version doesn't match skill dependency.

**Solution:**

1. **Update package to latest version:**
   ```bash
   python3 tools/sc-install.py upgrade sc-ci-automation
   ```

2. **Check version compatibility:**
   ```bash
   cat packages/sc-ci-automation/manifest.yaml | grep version
   ```

---

## Version Bumping Issues

### Error: "Version file not found"

**Symptom:** `--patch` flag fails with file not found error.

**Cause:** Version file path not configured or doesn't exist.

**Solution:**

1. **Configure version file:**
   ```yaml
   # .claude/ci-automation.yaml
   version_file: version.txt
   ```

2. **Create version file if missing:**
   ```bash
   echo "0.1.0" > version.txt
   git add version.txt
   git commit -m "Add version file"
   ```

3. **For package.json (Node):**
   ```yaml
   version_file: package.json
   version_pattern: '"version": "(\\d+\\.\\d+\\.\\d+)"'
   ```

---

### Error: "Invalid version format"

**Symptom:** Version bump fails with format error.

**Cause:** Version file doesn't follow semver format.

**Solution:**

1. **Use semver format:**
   ```
   MAJOR.MINOR.PATCH (e.g., 1.2.3)
   ```

2. **Update version file:**
   ```bash
   echo "1.0.0" > version.txt
   ```

---

## General Debugging

### Enable Debug Mode

**Check audit logs:**
```bash
cat .claude/state/logs/ci-automation/*.json | jq .
```

**Review agent execution:**
```bash
ls -lah .claude/state/logs/ci-automation/
```

**Verbose output:**
```
/sc-ci-automation --test --verbose
```
(Note: `--verbose` flag may not be implemented in v0.1.0)

---

### Common Error Messages

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `VALIDATION.DIRTY_REPO` | Working tree not clean | Commit or stash changes |
| `VALIDATION.CONFIG_NOT_FOUND` | Missing config file | Create `.claude/ci-automation.yaml` |
| `AUTHENTICATION_FAILED` | GitHub auth missing | Set `GITHUB_TOKEN` or run `gh auth login` |
| `BUILD.COMPILE_FAILED` | Build failed | Check build output, fix errors |
| `TEST.FAILED` | Tests failed | Review test output, fix failures |
| `EXECUTION.TIMEOUT` | Agent exceeded timeout | Split into smaller tasks or increase timeout |

---

### Still Having Issues?

1. **Check logs:**
   ```bash
   cat .claude/state/logs/ci-automation/latest.json
   ```

2. **Review CI agent docs:**
   - `.claude/agents/ci-validate-agent.md`
   - `.claude/agents/ci-build-agent.md`
   - `.claude/agents/ci-test-agent.md`

3. **Report bug:**
   - [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
   - Include error message and relevant config

4. **Ask for help:**
   - Include: error message, config file, command used
   - Sanitize sensitive information (tokens, secrets)

---

## Best Practices

1. **Start with `--test`** before using `--yolo`
2. **Configure once** in `.claude/ci-automation.yaml`
3. **Commit config** so team benefits
4. **Review audit logs** periodically
5. **Keep agents updated** with latest package versions

---

## Related Documentation

- [README.md](README.md) - Overview and quick start
- [USE-CASES.md](USE-CASES.md) - Practical examples
- [CHANGELOG.md](CHANGELOG.md) - Version history
