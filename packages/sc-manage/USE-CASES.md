# sc-manage Use Cases

## Introduction

The `sc-manage` package provides centralized package discovery and management for Synaptic Canvas, enabling you to install, uninstall, and manage Claude Code packages at both global and local scopes. Whether you're setting up a new development environment, onboarding new team members, or standardizing package installations across projects, `sc-manage` streamlines the entire package lifecycle.

These use cases demonstrate how `sc-manage` simplifies package management, enables team standardization, and integrates with CI/CD workflows for consistent development environments.

---

## Use Case 1: Installing Packages into New Projects

**Scenario/Context:**
You just created a new project repository and want to install Synaptic Canvas packages locally (repo-specific) to enable specialized workflows. You need an easy way to discover what packages are available and install them without memorizing package names.

**Step-by-step Walkthrough:**

1. Create new repository:
   ```bash
   mkdir my-new-project
   cd my-new-project
   git init
   ```

2. List available packages to see what's offered:
   ```
   /sc-manage --list
   ```
   Output:
   ```
   Available Synaptic Canvas Packages (v0.4.0)

   Package                 | Tier | Scope      | Status  | Description
   ----------------------- | ---- | ---------- | ------- | -----------
   delay-tasks             | T0   | Global     | -       | Schedule delayed waits and polling
   sc-git-worktree            | T1   | Local-only | -       | Manage git worktrees for parallel development
   sc-manage               | T0   | Global     | Global  | Package discovery and management
   repomix-nuget           | T1   | Local-only | -       | Generate AI-optimized NuGet context

   Tier 0: Direct copy, no dependencies
   Tier 1: Token substitution, repo context
   Tier 2: External dependencies required
   ```

3. Install sc-git-worktree locally:
   ```
   /sc-manage --install sc-git-worktree --local
   ```
   Output:
   ```
   Installing sc-git-worktree (v0.4.0) to local scope...

   Detected repository: my-new-project
   Installation path: /path/to/my-new-project/.claude

   Processing artifacts:
   ✓ command: commands/sc-git-worktree.md
   ✓ skill: skills/sc-managing-worktrees/SKILL.md
   ✓ agents: agents/sc-worktree-create.md
   ✓ agents: agents/sc-worktree-scan.md
   ✓ agents: agents/sc-worktree-cleanup.md
   ✓ agents: agents/sc-worktree-abort.md

   Token substitution (Tier 1):
   ✓ REPO_NAME detected: my-new-project

   Installation complete
   ```

4. Verify installation:
   ```bash
   ls -la .claude/commands/
   # Should show sc-git-worktree.md and other commands
   ```

5. Test the installed package:
   ```
   /sc-git-worktree --status
   ```
   Output:
   ```
   Repository: my-new-project
   Worktree Base: ../my-new-project-worktrees/
   ```

6. Install additional packages as needed:
   ```
   /sc-manage --install delay-tasks --local
   /sc-manage --install repomix-nuget --local
   ```

**Expected Outcomes:**
- New project has access to specialized packages
- Packages are installed locally (repo-specific)
- All commands are available immediately
- Token substitution ({{REPO_NAME}}) is automatic
- Clear feedback on what was installed

**Benefits of Using This Approach:**
- Quick project setup with necessary tools
- No guessing about package names or availability
- Automatic context detection (repository name)
- Team members can replicate setup easily
- Clear visibility into what's installed

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [sc-packages-list agent](agents/sc-packages-list.md)
- [sc-package-install agent](agents/sc-package-install.md)

**Tips and Best Practices:**
- Use `--list` first to see available packages
- Check package descriptions to understand purpose
- Use `--local` for repo-specific packages (sc-git-worktree, repomix-nuget)
- Use `--global` for general-purpose packages (delay-tasks, sc-manage)
- Document installed packages in your project README
- Add `.claude/` to git (or `.claude-packages/` in `.gitignore` if using only scripts)

**Common Pitfalls to Avoid:**
- Installing local-only packages globally (will fail)
- Not checking available packages before installing
- Forgetting to commit `.claude/` to git (others won't have it)
- Installing globally when local installation is more appropriate

---

## Use Case 2: Discovering Available Packages

**Scenario/Context:**
You're starting a new development workflow and want to understand what Synaptic Canvas packages are available, what each does, and which ones would be useful for your project.

**Step-by-step Walkthrough:**

1. List all available packages:
   ```
   /sc-manage --list
   ```
   Output shows all packages with descriptions

2. Get detailed documentation for a package:
   ```
   /sc-manage --docs delay-tasks
   ```
   Output:
   ```
   Package: delay-tasks (v0.4.0)
   Tier: 0 (Direct Copy)
   Scope: Global or Local

   Description:
   Schedule delayed one-shot waits or bounded polling with minimal heartbeats.
   Provides a /delay command and agents reusable by other skills.

   Quick Start:
   python3 tools/sc-install.py install delay-tasks --dest /Users/<you>/Documents/.claude

   Usage:
   - /delay --once --minutes 2 --action "go"
   - /delay --poll --every 60 --for 5m --action "done"

   Agents:
   - delay-once (v0.4.0)
   - delay-poll (v0.4.0)
   - git-pr-check-delay (v0.4.0)

   [Full README content]
   ```

3. Ask follow-up questions about the package:
   ```
   Can I use delay-tasks for checking GitHub Actions status?
   ```

4. Get docs for another package:
   ```
   /sc-manage --docs sc-git-worktree
   ```

5. Ask comparison question:
   ```
   When would I use sc-git-worktree vs. just using git branches normally?
   ```

6. Review package compatibility:
   ```
   /sc-manage --docs repomix-nuget
   ```

7. Make informed decision about which packages to install based on:
   - Project requirements
   - Workflow needs
   - Package scope (local vs. global)
   - External dependencies (Tier 2)

**Expected Outcomes:**
- Clear understanding of available packages
- Detailed documentation for each package
- Answers to questions about package capabilities
- Informed decisions about installations
- No guesswork about package purpose

**Benefits of Using This Approach:**
- Discover packages without reading GitHub
- Compare packages side-by-side
- Ask questions and get clarification
- Understand use cases before installing
- Make informed installation decisions

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [sc-packages-list agent](agents/sc-packages-list.md)
- [sc-package-docs agent](agents/sc-package-docs.md)

**Tips and Best Practices:**
- Use `--list` for quick overview
- Use `--docs` for detailed information
- Ask follow-up questions about packages
- Share package descriptions with your team
- Document which packages your team uses

**Common Pitfalls to Avoid:**
- Installing packages without understanding them
- Installing packages that don't fit your workflow
- Forgetting to check package tier (Tier 2 may require external tools)

---

## Use Case 3: Managing Multiple Package Installations

**Scenario/Context:**
You maintain multiple projects with different package requirements:
- Project A: needs sc-git-worktree and delay-tasks
- Project B: needs repomix-nuget only
- Your global Claude Code setup: needs sc-manage globally

You want to track what's installed where and manage installations consistently.

**Step-by-step Walkthrough:**

1. Global setup: Install sc-manage globally
   ```
   /sc-manage --install sc-manage --global
   ```

2. Project A setup: Install multiple packages
   ```bash
   cd ~/project-a
   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local
   ```

3. Project B setup: Install specific package
   ```bash
   cd ~/project-b
   /sc-manage --install repomix-nuget --local
   ```

4. Check installations across projects:

   In Project A:
   ```
   /sc-manage --list
   ```
   Output:
   ```
   Installations in ~/project-a

   Package                 | Local | Global | Status
   ----------------------- | ----- | ------ | ---------
   delay-tasks             | Yes   | -      | Installed (Local)
   sc-git-worktree            | Yes   | -      | Installed (Local)
   sc-manage               | -     | Yes    | Installed (Global)
   repomix-nuget           | -     | -      | Not installed
   ```

   In Project B:
   ```
   /sc-manage --list
   ```
   Output:
   ```
   Installations in ~/project-b

   Package                 | Local | Global | Status
   ----------------------- | ----- | ------ | ---------
   delay-tasks             | -     | -      | Not installed
   sc-git-worktree            | -     | -      | Not installed
   sc-manage               | -     | Yes    | Installed (Global)
   repomix-nuget           | Yes   | -      | Installed (Local)
   ```

5. Update installations as projects evolve:

   Project A needs repomix-nuget:
   ```bash
   cd ~/project-a
   /sc-manage --install repomix-nuget --local
   ```

6. View complete installation status across all projects:
   ```
   # Each project maintains own .claude/ directory
   # Status is always available via /sc-manage --list
   ```

**Expected Outcomes:**
- Clear visibility into what's installed where
- Easy updates as project needs change
- Global packages available everywhere
- Local packages specific to each project
- No conflicts between installations

**Benefits of Using This Approach:**
- Manage multiple projects efficiently
- Different tools for different projects
- Global/local separation provides flexibility
- Easy to understand installation status
- Consistent across team

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [sc-packages-list agent](agents/sc-packages-list.md)
- [sc-package-install agent](agents/sc-package-install.md)
- [sc-package-uninstall agent](agents/sc-package-uninstall.md)

**Tips and Best Practices:**
- Global packages: sc-manage, delay-tasks (general purpose)
- Local packages: sc-git-worktree, repomix-nuget (repo-specific)
- Check list regularly to understand current state
- Document package choices in project README
- Keep installations consistent across team members

**Common Pitfalls to Avoid:**
- Installing local-only packages globally
- Forgetting which packages are installed where
- Not updating tracking when changes are made

---

## Use Case 4: Checking Package Versions and Compatibility

**Scenario/Context:**
You want to ensure all team members have the same package versions, and you need to verify that installed packages are compatible with your project's requirements.

**Step-by-step Walkthrough:**

1. Check current package versions:
   ```
   /sc-manage --list
   ```
   Output includes version numbers for all available packages:
   ```
   Package                 | Version | Status
   ----------------------- | ------- | ---------
   delay-tasks             | 0.4.0   | -
   sc-git-worktree            | 0.4.0   | -
   sc-manage               | 0.4.0   | Global
   repomix-nuget           | 0.4.0   | -
   ```

2. Verify installed packages match expected versions:
   ```bash
   cat .claude/commands/sc-git-worktree.md | grep "version: "
   # Should show: version: 0.4.0
   ```

3. Document package versions in project:
   ```bash
   # Create or update .claude/PACKAGES.md
   cat > .claude/PACKAGES.md << 'EOF'
   # Installed Synaptic Canvas Packages

   - delay-tasks v0.4.0
   - sc-git-worktree v0.4.0
   - repomix-nuget v0.4.0

   Last Updated: 2025-12-02
   EOF
   ```

4. Share version requirements with team:
   ```markdown
   # Project Setup

   Required Synaptic Canvas packages (v0.4.0):
   - sc-git-worktree v0.4.0 (local)
   - delay-tasks v0.4.0 (local)

   Install via:
   ```bash
   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local
   ```
   ```

5. In CI/CD, verify correct versions are installed:
   ```yaml
   - name: Verify Synaptic Canvas packages
     run: |
       /sc-manage --list | grep "sc-git-worktree" | grep "0.4.0"
       /sc-manage --list | grep "delay-tasks" | grep "0.4.0"
   ```

6. New team member follows setup:
   ```bash
   git clone repo
   cd repo
   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local
   # Automatically installs correct versions
   ```

**Expected Outcomes:**
- All team members have same package versions
- Version requirements documented in project
- CI/CD validates package versions
- Easy onboarding with clear version info
- No version conflicts or surprises

**Benefits of Using This Approach:**
- Consistent development environments
- Clear version documentation
- Automated verification in CI/CD
- Easy debugging of version-related issues
- Team alignment on package versions

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [Versioning Strategy](../../docs/versioning-strategy.md)

**Tips and Best Practices:**
- Always check available versions before installation
- Document required versions in README
- Verify versions in CI/CD
- Update all team members when upgrading packages
- Keep PACKAGES.md (or similar) in repo

**Common Pitfalls to Avoid:**
- Installing different versions on different machines
- Not documenting version requirements
- Forgetting to verify versions in CI/CD

---

## Use Case 5: Uninstalling and Updating Packages

**Scenario/Context:**
Project requirements change: you no longer need a package, or a new version is available and you want to upgrade. You need a clean way to remove old packages and install new versions.

**Step-by-step Walkthrough:**

**Scenario A: Uninstalling Unused Package**

1. Determine which packages are no longer needed:
   ```
   /sc-manage --list
   ```

2. Project no longer does parallel feature development; uninstall sc-git-worktree:
   ```
   /sc-manage --uninstall sc-git-worktree --local
   ```
   Output:
   ```
   Uninstalling sc-git-worktree (v0.4.0) from local scope...

   Removal plan:
   ✓ commands/sc-git-worktree.md
   ✓ skills/sc-managing-worktrees/SKILL.md
   ✓ agents/sc-worktree-create.md
   ✓ agents/sc-worktree-scan.md
   ✓ agents/sc-worktree-cleanup.md
   ✓ agents/sc-worktree-abort.md

   Uninstall complete
   ```

3. Verify removal:
   ```
   /sc-manage --list
   ```
   Output: sc-git-worktree no longer listed as installed

4. Commit changes:
   ```bash
   git add .
   git commit -m "chore: remove sc-git-worktree package (no longer needed)"
   ```

**Scenario B: Updating to New Package Version**

1. New version available (v0.5.0):
   ```
   /sc-manage --uninstall delay-tasks --local
   ```

2. Install new version:
   ```
   /sc-manage --install delay-tasks --local
   ```
   Output:
   ```
   Installing delay-tasks (v0.5.0) to local scope...
   [Installation complete with new features]
   ```

3. Test new functionality:
   ```
   /delay --help
   # Shows new options from v0.5.0
   ```

4. Commit update:
   ```bash
   git add .
   git commit -m "chore: upgrade delay-tasks to v0.5.0"
   ```

5. Update team documentation:
   ```bash
   # Update PACKAGES.md
   # Update README setup instructions
   # Notify team of new features/changes
   ```

**Expected Outcomes:**
- Clean removal of unused packages
- Straightforward upgrade to new versions
- No leftover files or conflicts
- Updated project documentation
- Team is informed of changes

**Benefits of Using This Approach:**
- Easy package lifecycle management
- No accumulation of unused packages
- Straightforward upgrade path
- Clean project repository
- Clear audit trail in git

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [sc-package-uninstall agent](agents/sc-package-uninstall.md)

**Tips and Best Practices:**
- Check package documentation before upgrading
- Test new versions locally before team-wide rollout
- Update README and documentation after changes
- Commit package changes separately from code changes
- Communicate package updates to team

**Common Pitfalls to Avoid:**
- Uninstalling packages that are still in use
- Upgrading to new versions without testing
- Forgetting to update documentation after changes

---

## Use Case 6: Integration with CI/CD Pipelines

**Scenario/Context:**
You want CI/CD to use Synaptic Canvas packages for automation. The CI/CD pipeline should verify that required packages are installed, use them for workflow automation, and report package-related issues.

**Step-by-step Walkthrough:**

**GitHub Actions Example:**

1. Create CI/CD workflow file (`.github/workflows/setup-and-verify.yml`):
   ```yaml
   name: Setup and Verify with Synaptic Canvas

   on:
     push:
       branches: [main, develop]
     pull_request:

   jobs:
     setup:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Verify Synaptic Canvas installation
           run: |
             # List available packages
             npx claude-code --exec-mode sync '/sc-manage --list'

         - name: Install required packages
           run: |
             npx claude-code --exec-mode sync <<'SCRIPT'
             /sc-manage --install sc-git-worktree --local
             /sc-manage --install delay-tasks --local
             SCRIPT

         - name: Verify installations
           run: |
             npx claude-code --exec-mode sync '/sc-manage --list'

         - name: Use delay-tasks for pre-test wait
           run: |
             npx claude-code --exec-mode sync '/delay --seconds 30 --action "Run tests"'

         - name: Run tests
           run: npm run test

         - name: Generate NuGet context (if applicable)
           run: |
             npx claude-code --exec-mode sync <<'SCRIPT'
             /sc-manage --install repomix-nuget --local
             /repomix-nuget --generate --output ./artifacts/nuget-context.xml
             SCRIPT
   ```

2. Workflow execution:
   - Verifies packages are available
   - Installs required packages
   - Uses packages for CI/CD tasks
   - Reports any failures

3. Results:
   ```
   ✓ Package verification passed
   ✓ Installations completed
   ✓ Pre-test delay completed
   ✓ Tests passed
   ✓ NuGet context generated
   ```

**Scenario: Multi-Stage Pipeline with Package Management**

```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Synaptic Canvas packages
        run: |
          npx claude-code --exec-mode sync <<'SCRIPT'
          /sc-manage --install sc-git-worktree --local
          /sc-manage --install delay-tasks --local
          /sc-manage --install repomix-nuget --local
          SCRIPT

  build:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Build with package support
        run: npm run build

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Wait before testing
        run: |
          npx claude-code --exec-mode sync '/delay --seconds 30 --action "Start tests"'

      - name: Run full test suite
        run: npm run test:full

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy and verify
        run: |
          npm run deploy
          npx claude-code --exec-mode sync '/delay --minutes 2 --action "Verify deployment"'
```

**Expected Outcomes:**
- CI/CD pipeline leverages Synaptic Canvas packages
- Automated package verification and installation
- Package-powered workflow automation
- Clear reporting of package-related issues
- Consistent CI/CD behavior

**Benefits of Using This Approach:**
- Automated package management in CI/CD
- Consistent package versions across environments
- Package-powered workflow automation
- Clear separation of package setup from build steps
- Repeatable, documented workflows

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [delay-tasks USE-CASES.md](../delay-tasks/USE-CASES.md#use-case-6-github-actions-integration)

**Tips and Best Practices:**
- Verify packages in first CI/CD step
- Install packages needed for pipeline
- Use delay-tasks for timing-dependent operations
- Generate NuGet context for .NET projects
- Document package setup in CI/CD file

**Common Pitfalls to Avoid:**
- Installing local-only packages in CI/CD global scope
- Not verifying packages before using them
- Forgetting to install packages before using commands

---

## Use Case 7: Team Standardization on Package Sets

**Scenario/Context:**
You lead a team of 5 developers working on multiple projects. You want to ensure consistent Synaptic Canvas package adoption across all projects, standardize workflows, and reduce onboarding time for new team members.

**Step-by-step Walkthrough:**

1. Define team standards:
   - All projects use sc-git-worktree for feature development
   - All projects use delay-tasks for CI/CD delays
   - .NET projects use repomix-nuget for AI context generation
   - All developers have sc-manage installed globally

2. Create team template repository:
   ```bash
   # Create template with standardized .claude directory
   mkdir synaptic-canvas-team-template
   cd synaptic-canvas-team-template
   git init
   ```

3. Set up standard package configuration:
   ```bash
   # Create template .claude/README.md
   cat > .claude/README.md << 'EOF'
   # Synaptic Canvas Packages

   This repository uses the following Synaptic Canvas packages:
   - sc-git-worktree (v0.4.0) - Manage parallel feature development
   - delay-tasks (v0.4.0) - Schedule CI/CD delays and polling

   For .NET projects, also install:
   - repomix-nuget (v0.4.0) - Generate AI context for NuGet packages

   ## Installation

   ```bash
   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local
   /sc-manage --install repomix-nuget --local  # .NET projects only
   ```

   ## Usage

   See individual package documentation:
   - `/sc-git-worktree --help`
   - `/delay --help`
   - `/repomix-nuget --help`
   EOF
   ```

4. Document team workflows:
   ```bash
   cat > DEVELOPMENT.md << 'EOF'
   # Development Workflow

   ## Creating a Feature

   1. Create feature worktree:
      ```
      /sc-git-worktree --create feature-name develop
      ```

   2. Work in the isolated directory:
      ```
      cd ../repo-name-worktrees/feature-name
      ```

   3. When done, clean up:
      ```
      /sc-git-worktree --cleanup feature-name
      ```

   ## Common Patterns

   - Use `/delay` for CI/CD waits
   - Use `/sc-git-worktree --status` to check parallel work
   - Use `/sc-manage --list` to verify installations

   EOF
   ```

5. Create setup script for new projects:
   ```bash
   cat > scripts/setup-packages.sh << 'EOF'
   #!/bin/bash
   set -euo pipefail

   # Install standard Synaptic Canvas packages
   echo "Installing Synaptic Canvas packages..."

   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local

   # For .NET projects, optionally install repomix-nuget
   if find . -name "*.csproj" -o -name "*.sln" | grep -q .; then
     echo "Detected .NET project, installing repomix-nuget..."
     /sc-manage --install repomix-nuget --local
   fi

   echo "Synaptic Canvas packages installed successfully"
   /sc-manage --list
   EOF
   chmod +x scripts/setup-packages.sh
   ```

6. Onboard new team member:
   ```bash
   git clone template my-new-project
   cd my-new-project
   ./scripts/setup-packages.sh
   # All packages installed automatically
   ```

7. Create team communication:
   ```markdown
   # Synaptic Canvas Team Standards

   All team members should have these packages installed:

   **Globally:**
   - sc-manage (package manager)

   **Per Project:**
   - sc-git-worktree (parallel feature development)
   - delay-tasks (CI/CD automation)
   - repomix-nuget (if .NET project)

   Benefits:
   - Consistent development workflows
   - Reduced onboarding time
   - Standardized CI/CD patterns
   - Shared knowledge across team

   Setup: Run `./scripts/setup-packages.sh` in any new project
   ```

8. Track adoption:
   ```bash
   # Quarterly check: verify all projects have standard packages
   for project in ~/projects/*/; do
     cd "$project"
     echo "=== $(basename $project) ==="
     /sc-manage --list | grep -E "sc-git-worktree|delay-tasks"
   done
   ```

**Expected Outcomes:**
- All team members use same Synaptic Canvas packages
- Consistent development workflows across projects
- Faster onboarding for new team members
- Reduced setup time for new projects
- Shared knowledge and best practices
- Clear standards documented and maintained

**Benefits of Using This Approach:**
- Team efficiency through standardization
- Reduced time explaining package usage
- Consistent development experience
- Easier collaboration across projects
- Documented best practices

**Related Documentation:**
- [/sc-manage command reference](commands/sc-manage.md)
- [Synaptic Canvas Contributing Guide](/CONTRIBUTING.md)

**Tips and Best Practices:**
- Document team standards in central wiki
- Create template repositories with standard setup
- Automate installation via scripts
- Share knowledge during team meetings
- Regular reviews of package adoption
- Update standards when new packages released

**Common Pitfalls to Avoid:**
- Forcing packages on teams that don't need them
- Not documenting why standards exist
- Forgetting to update standards when packages change
- Not supporting exceptions when justified

---

## Common Patterns

### Pattern 1: Quick Package Discovery
```
/sc-manage --list
```

### Pattern 2: Install Package Locally
```
/sc-manage --install package-name --local
```

### Pattern 3: Install Package Globally
```
/sc-manage --install package-name --global
```

### Pattern 4: Read Package Documentation
```
/sc-manage --docs package-name
```

### Pattern 5: Clean Up Unused Package
```
/sc-manage --uninstall package-name --local
```

---

## Integration Examples

### With Setup Script
```bash
#!/bin/bash
# new-project-setup.sh

/sc-manage --install sc-git-worktree --local
/sc-manage --install delay-tasks --local
echo "Packages installed"
/sc-manage --list
```

### With GitHub Actions
```yaml
- name: Install Synaptic Canvas packages
  run: |
    npx claude-code --exec-mode sync <<'SCRIPT'
    /sc-manage --install sc-git-worktree --local
    /sc-manage --install delay-tasks --local
    SCRIPT
```

### With Team Documentation
```markdown
## Getting Started

1. Install Synaptic Canvas packages:
   ```
   /sc-manage --install sc-git-worktree --local
   /sc-manage --install delay-tasks --local
   ```

2. Verify installation:
   ```
   /sc-manage --list
   ```

3. Start developing:
   ```
   /sc-git-worktree --create my-feature develop
   ```
```

---

## Team Workflows

### New Developer Onboarding
1. New developer clones repo
2. Runs setup script: `./scripts/setup-packages.sh`
3. All required packages installed automatically
4. Developer is ready to start working

### Package Update Communication
1. New package version available
2. Team lead updates documentation
3. Team members run: `/sc-manage --install package-name --local`
4. New version is installed, ready to use

### Cross-Team Coordination
1. Multiple teams using Synaptic Canvas
2. Share standards and best practices
3. New packages discovered and evaluated
4. Team leads coordinate adoption

---

## Troubleshooting

### Scenario: Can't install local-only package globally
```
Error: sc-git-worktree can only be installed locally
```
**Solution:** Use `--local` flag instead:
```
/sc-manage --install sc-git-worktree --local
```

### Scenario: Package installation fails
**Solution:**
1. Verify package name: `/sc-manage --list`
2. Check scope: `--local` or `--global`
3. Verify .claude directory exists or will be created
4. Check permissions to install directory

### Scenario: Installed package not available
**Solution:**
- Verify installation: `/sc-manage --list`
- Check that you're in repo directory for local packages
- Restart Claude Code session if recently installed

### Scenario: Multiple versions of same package installed
**Solution:**
```
/sc-manage --uninstall package-name --local
/sc-manage --uninstall package-name --global
/sc-manage --install package-name --local  # or --global
```

### Scenario: Unsure which scope to use
**Solution:**
- `--local`: package is repo-specific (sc-git-worktree, repomix-nuget)
- `--global`: package is general-purpose (sc-manage, delay-tasks)
- Check package documentation: `/sc-manage --docs package-name`

---

## Getting Started

### Minimum Setup
```bash
# Install sc-manage globally (one-time)
python3 tools/sc-install.py install sc-manage --dest /Users/<you>/Documents/.claude

# In any project, list packages
/sc-manage --list

# Install packages as needed
/sc-manage --install sc-git-worktree --local
```

### First Use
1. List available packages: `/sc-manage --list`
2. Read package docs: `/sc-manage --docs package-name`
3. Install package: `/sc-manage --install package-name --local`
4. Use package: `/package-command --help`

### Common Starting Patterns
- **First project**: `/sc-manage --install sc-git-worktree --local`
- **CI/CD automation**: `/sc-manage --install delay-tasks --local`
- **Discovery**: `/sc-manage --list` then `/sc-manage --docs package-name`
- **Team setup**: Create template with standard packages

---

## See Also

- [sc-manage README](README.md)
- [/sc-manage Command Reference](commands/sc-manage.md)
- [Synaptic Canvas Package Registry](../../docs/registries/)
- [Synaptic Canvas Contributing Guide](/CONTRIBUTING.md)
- [Synaptic Canvas Repository](https://github.com/randlee/synaptic-canvas)

---

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Maintainer:** Synaptic Canvas Contributors
