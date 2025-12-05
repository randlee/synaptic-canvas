# Marketplace Package Manager - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Marketplace Package Manager skill.

## Quick Diagnostics

Before diving into specific issues, run these quick checks:

```
# Check CLI availability
sc-install --help

# Check marketplace configuration
cat ~/.claude/config.yaml

# Verify registries
/marketplace registry list

# Test network connectivity
ping github.com
```

---

## Common Issues and Solutions

### Issue 1: "Registry not accessible" or "Cannot fetch registry"

**Symptoms:**
- Error message: "Failed to fetch registry from [URL]"
- Timeout when listing packages
- Empty package list

**Possible Causes:**
1. No network connection
2. Registry URL is incorrect
3. Registry server is down
4. Firewall blocking access
5. Invalid registry path

**Solutions:**

**Solution 1A: Check Network Connection**
```bash
# Test connectivity
ping github.com
curl -I https://github.com

# If behind proxy, configure:
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

**Solution 1B: Verify Registry URL**
```bash
# List registries
/marketplace registry list

# Check URL is correct
# Should start with https:// or http://

# Test URL manually
curl -L https://github.com/randlee/synaptic-canvas/raw/main/docs/registries/nuget/registry.json
```

**Solution 1C: Fix Registry Configuration**
```bash
# Remove broken registry
/marketplace registry remove broken-registry

# Re-add with correct URL
/marketplace registry add synaptic-canvas https://github.com/randlee/synaptic-canvas --path docs/registries/nuget/registry.json
```

**Solution 1D: Check Registry Path**
- Verify the --path parameter points to registry.json
- Path should be relative to repository root
- Common path: `docs/registries/nuget/registry.json`

**Prevention:**
- Verify URLs before adding registries
- Test registry access with curl before adding
- Keep registry list clean and up-to-date

---

### Issue 2: "Package not found"

**Symptoms:**
- Error: "Package [name] not found"
- Package doesn't appear in search results
- Installation fails with "Package does not exist"

**Possible Causes:**
1. Package name misspelled
2. Package not in configured registries
3. Registry cache is stale
4. Package was removed or renamed

**Solutions:**

**Solution 2A: Verify Package Name**
```bash
# List all packages to see exact names
/marketplace list

# Search for similar packages
/marketplace search [partial-name]

# Common package names:
# - delay-tasks (not "delay" or "tasks")
# - git-worktree (not "worktree" or "git")
# - repomix-nuget (not "repomix" or "nuget")
# - sc-manage (not "sc-manager" or "manage")
```

**Solution 2B: Check Registry Coverage**
```bash
# List registries
/marketplace registry list

# Add missing registry if package is there
/marketplace registry add custom-reg https://github.com/org/marketplace

# Search in specific registry
/marketplace search [package] --registry custom-reg
```

**Solution 2C: Refresh Registry Cache**
```bash
# If Phase 3 implements caching:
# Clear cache and re-query
/marketplace refresh

# Or remove and re-add registry
/marketplace registry remove synaptic-canvas
/marketplace registry add synaptic-canvas https://github.com/randlee/synaptic-canvas --path docs/registries/nuget/registry.json
```

**Solution 2D: Check Package Status**
- Package may be deprecated or archived
- Check registry.json directly for package status
- Look for replacement packages

**Prevention:**
- Use tab completion for package names
- Search before attempting install
- Keep registries up to date

---

### Issue 3: "Installation failed" or "Permission denied"

**Symptoms:**
- Error: "Permission denied writing to ~/.claude"
- Installation aborts with file system error
- Files not created in destination

**Possible Causes:**
1. No write permission to destination directory
2. Disk space full
3. File system read-only
4. Incorrect destination path
5. Directory doesn't exist

**Solutions:**

**Solution 3A: Check Permissions**
```bash
# Check ~/.claude ownership
ls -la ~/.claude

# Fix ownership if needed
sudo chown -R $USER:$USER ~/.claude

# Fix permissions
chmod -R u+w ~/.claude
```

**Solution 3B: Verify Disk Space**
```bash
# Check available space
df -h ~

# Clean up if needed
rm -rf ~/.claude/.tmp/*
```

**Solution 3C: Create Directory Structure**
```bash
# Ensure directories exist
mkdir -p ~/.claude/{commands,skills,agents,scripts}

# Set permissions
chmod -R u+rwX ~/.claude
```

**Solution 3D: Use Correct Installation Scope**
```bash
# For global install (requires write to ~/.claude)
/marketplace install [package] --global

# For local install (current project)
/marketplace install [package] --local

# Verify destination path
echo $HOME/.claude
```

**Prevention:**
- Ensure ~/.claude exists before first install
- Maintain correct permissions
- Monitor disk space
- Use --local for testing

---

### Issue 4: "Command not found after installation"

**Symptoms:**
- Package installs successfully
- `/[command]` not recognized by Claude
- "No such command" error

**Possible Causes:**
1. Command file not in correct location
2. File name doesn't match command name
3. Claude hasn't reloaded commands
4. Installation to wrong .claude directory

**Solutions:**

**Solution 4A: Verify Installation Location**
```bash
# Check where package was installed
ls -la ~/.claude/commands/

# Should see command files like:
# delay.md
# git-worktree.md
# sc-manage.md
```

**Solution 4B: Verify File Names**
```bash
# Command file should match command name
# /delay requires commands/delay.md
# /git-worktree requires commands/git-worktree.md

# Check installed files
cat ~/.claude/commands/delay.md | head -n 5
```

**Solution 4C: Reload Claude**
- Claude may need to reload command list
- Try: "Reload commands" or restart Claude session
- Check if commands appear in autocomplete

**Solution 4D: Reinstall Package**
```bash
# Force reinstall
/marketplace install [package] --global --force

# Verify files are copied
ls -la ~/.claude/commands/
```

**Prevention:**
- Verify installation success message
- Check file locations after install
- Test commands immediately after installation

---

### Issue 5: "Script execution errors"

**Symptoms:**
- Scripts not executable
- "Permission denied" when running scripts
- Scripts fail with import errors

**Possible Causes:**
1. Scripts not marked as executable
2. Python not in PATH
3. Missing Python dependencies
4. Wrong Python version

**Solutions:**

**Solution 5A: Fix Script Permissions**
```bash
# Make scripts executable
chmod +x ~/.claude/scripts/*.py
chmod +x ~/.claude/scripts/*.sh

# Verify
ls -la ~/.claude/scripts/
```

**Solution 5B: Check Python**
```bash
# Verify Python 3.12+
python3 --version

# Check Python path
which python3

# If not found, install Python 3.12+
# macOS: brew install python@3.12
# Linux: apt-get install python3.12
```

**Solution 5C: Install Dependencies**
```bash
# Install PyYAML if needed
pip3 install PyYAML

# Check package dependencies
/marketplace info [package]
```

**Solution 5D: Reinstall with Force**
```bash
# Reinstall to fix permissions
/marketplace install [package] --global --force
```

**Prevention:**
- Ensure Python 3.12+ installed
- Install dependencies before packages
- Verify script permissions after install

---

### Issue 6: "Version mismatch" or "Incompatible version"

**Symptoms:**
- Error: "Package version X.Y.Z incompatible with marketplace version A.B.C"
- Features not working as documented
- Unexpected behavior

**Possible Causes:**
1. Package too old for current marketplace
2. Package too new for current marketplace
3. Mixed versions from different registries
4. CLI version outdated

**Solutions:**

**Solution 6A: Check Version Compatibility**
```bash
# Check CLI version
sc-install --version

# Check package version
/marketplace info [package]

# Check marketplace version
cat ~/.claude/config.yaml | grep version
```

**Solution 6B: Update CLI**
```bash
# Get latest CLI
cd /path/to/synaptic-canvas
git pull
pip3 install -e .

# Verify update
sc-install --version
```

**Solution 6C: Install Compatible Package Version**
```bash
# Check compatibility matrix
# Look in docs/version-compatibility-matrix.md

# Install specific version if available
/marketplace install [package]@[version] --global
```

**Solution 6D: Check Registry Compatibility**
```bash
# Ensure registry supports current marketplace version
cat registry.json | grep versionCompatibility

# Update registry if needed
/marketplace registry add synaptic-canvas https://github.com/randlee/synaptic-canvas --path docs/registries/nuget/registry.json --force
```

**Prevention:**
- Keep CLI updated
- Check version compatibility before install
- Use packages from official registry
- Review changelogs for breaking changes

---

### Issue 7: "Agent not responding" or "Agent error"

**Symptoms:**
- Agent doesn't respond to queries
- Agent throws errors
- Unexpected agent behavior

**Possible Causes:**
1. Agent file not installed correctly
2. Agent not registered in registry.yaml
3. Agent markdown syntax errors
4. Missing agent dependencies

**Solutions:**

**Solution 7A: Verify Agent Installation**
```bash
# Check agent files
ls -la ~/.claude/agents/ | grep [package]

# Check registry
cat ~/.claude/agents/registry.yaml
```

**Solution 7B: Verify Agent Registration**
```bash
# Registry should list all agents
cat ~/.claude/agents/registry.yaml

# Should see entries like:
# delay-runner:
#   version: "0.4.0"
#   path: ".claude/agents/delay-runner.md"
```

**Solution 7C: Reinstall Package**
```bash
# Reinstall to fix agent registration
/marketplace install [package] --global --force
```

**Solution 7D: Check Agent Syntax**
```bash
# Verify agent markdown is valid
cat ~/.claude/agents/[agent-name].md

# Look for:
# - Frontmatter (between ---)
# - Clear instructions
# - No syntax errors
```

**Prevention:**
- Verify agent registration after install
- Test agents immediately after installation
- Keep packages updated

---

### Issue 8: "Slow performance" or "Timeout"

**Symptoms:**
- Commands take too long to execute
- Package list query times out
- Installation hangs

**Possible Causes:**
1. Network latency
2. Large registry files
3. Too many registries configured
4. Slow disk I/O

**Solutions:**

**Solution 8A: Optimize Registry Configuration**
```bash
# Remove unused registries
/marketplace registry list
/marketplace registry remove unused-registry

# Keep only essential registries
```

**Solution 8B: Check Network Performance**
```bash
# Test registry fetch time
time curl -L https://github.com/randlee/synaptic-canvas/raw/main/docs/registries/nuget/registry.json

# Should complete in < 2 seconds
```

**Solution 8C: Use Local Cache (if available)**
```bash
# If Phase 3 implements caching
# Enable cache in config
echo "cache_enabled: true" >> ~/.claude/config.yaml
```

**Solution 8D: Optimize Installation**
```bash
# Install to local first for testing
/marketplace install [package] --local

# Then install to global after verification
/marketplace install [package] --global
```

**Prevention:**
- Keep registry list minimal
- Use fast, reliable registries
- Monitor network performance
- Test on local first

---

## Diagnostic Commands

### Check System Health

```bash
# Verify CLI is installed
which sc-install

# Check Python
python3 --version

# Check PyYAML
python3 -c "import yaml; print(yaml.__version__)"

# Check Git
git --version

# Check disk space
df -h ~

# Check permissions
ls -la ~/.claude
```

### Check Configuration

```bash
# View full config
cat ~/.claude/config.yaml

# Check registries
/marketplace registry list

# Check installed packages
ls -la ~/.claude/{commands,skills,agents,scripts}
```

### Check Network

```bash
# Test registry access
curl -I https://github.com/randlee/synaptic-canvas

# Test registry fetch
curl -L https://github.com/randlee/synaptic-canvas/raw/main/docs/registries/nuget/registry.json

# Check DNS
nslookup github.com
```

---

## Error Message Reference

### "Invalid URL format"
- **Cause**: Registry URL doesn't start with https:// or http://
- **Fix**: Use complete URL: `https://github.com/org/repo`

### "Registry name invalid"
- **Cause**: Registry name contains invalid characters
- **Fix**: Use only alphanumeric, dash, underscore

### "Must specify one of: --global, --local, or --dest"
- **Cause**: Installation scope not specified
- **Fix**: Add `--global` or `--local` to install command

### "Package already exists (use --force to overwrite)"
- **Cause**: Package files already present
- **Fix**: Add `--force` flag or uninstall first

### "No registries configured"
- **Cause**: config.yaml has no registries
- **Fix**: Add default registry: `/marketplace registry add synaptic-canvas ...`

### "PyYAML not installed"
- **Cause**: Missing Python dependency
- **Fix**: `pip3 install PyYAML`

---

## Getting Further Help

### Resources

1. **Documentation**
   - README.md - User guide
   - USE-CASES.md - Detailed scenarios
   - SKILL.md - Technical reference

2. **Package Documentation**
   - Each package has its own README
   - Check CHANGELOG for recent changes
   - Review TROUBLESHOOTING in package directory

3. **Community**
   - GitHub Issues
   - Discussions
   - Wiki

### Reporting Issues

When reporting issues, include:

1. **Environment**
   - OS version
   - Python version
   - CLI version
   - Marketplace version

2. **Steps to Reproduce**
   - Exact commands run
   - Expected behavior
   - Actual behavior

3. **Error Output**
   - Full error message
   - Stack trace if available
   - Log files

4. **Configuration**
   - config.yaml contents (redact sensitive data)
   - Registry list
   - Installed packages

### Debug Mode

```bash
# Enable verbose output (if implemented)
export SC_DEBUG=1
/marketplace list

# Check logs (if implemented)
cat ~/.claude/logs/marketplace.log
```

---

## Preventive Maintenance

### Regular Checks

```bash
# Monthly:
# - Update CLI to latest version
# - Check for package updates
# - Clean up unused registries
# - Verify installations

# Weekly:
# - Check disk space
# - Review error logs
# - Test critical packages

# After major updates:
# - Review compatibility matrix
# - Test all installed packages
# - Update documentation
```

### Best Practices

1. **Keep CLI Updated**: `git pull && pip3 install -e .`
2. **Minimal Registries**: Only add registries you use
3. **Test Locally First**: Use --local before --global
4. **Read Changelogs**: Before updating packages
5. **Backup Config**: Before major changes
6. **Document Custom Registries**: For team knowledge

---

## FAQ

**Q: Why is my package installation slow?**
A: Check network speed, registry size, and disk I/O. Use --local for testing.

**Q: Can I install multiple versions of the same package?**
A: No, only one version per scope (global or local). Use different scopes for different versions.

**Q: How do I uninstall a package?**
A: Use `sc-install uninstall [package] --dest ~/.claude`

**Q: Can I create my own packages?**
A: Yes! See package creation documentation in CONTRIBUTING.md

**Q: What happens if registry is down?**
A: Queries will fail. Add fallback registries or wait for registry to recover.

**Q: How do I report security issues?**
A: Use GitHub Security Advisories or email maintainers directly.

**Q: Can I use marketplace without internet?**
A: Only if packages are pre-installed or if using local registry files.

**Q: How often should I update packages?**
A: Check monthly for updates, apply critical security updates immediately.

---

**Still having issues?** Open an issue on GitHub with full diagnostic output.
