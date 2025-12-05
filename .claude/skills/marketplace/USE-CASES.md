# Marketplace Package Manager - Use Cases

This document provides detailed use cases for the Marketplace Package Manager skill, demonstrating real-world scenarios and workflows.

## Use Case 1: Discover Available Marketplace Packages

**Scenario**: You're new to Synaptic Canvas and want to explore what packages are available in the marketplace.

**Goal**: Get a comprehensive view of all available packages and understand what each one offers.

### Steps

1. **List all packages:**
   ```
   /marketplace list
   ```

2. **Review the output:**
   ```
   Available packages:

   • delay-tasks (v0.4.0) - beta
     "Schedule delayed or interval-based actions with minimal heartbeats"
     Tags: delay, polling, tasks, ci, automation
     Artifacts: 1 command, 1 skill, 3 agents, 1 script

   • sc-git-worktree (v0.4.0) - beta
     "Create, manage, scan, and clean up git worktrees for parallel development"
     Tags: git, worktree, branches, development, parallel
     Artifacts: 1 command, 1 skill, 4 agents

   • sc-manage (v0.4.0) - beta
     "Interface for managing Synaptic Canvas packages"
     Tags: package-manager, discovery, marketplace, tools
     Artifacts: 1 command, 1 skill, 4 agents

   • repomix-nuget (v0.4.0) - beta
     "Generate comprehensive NuGet repository context for AI analysis"
     Tags: nuget, csharp, .net, documentation, analysis
     Artifacts: 1 command, 1 skill, 3 agents, 1 script
   ```

3. **Get more details on a specific package:**
   ```
   Tell me more about delay-tasks
   ```

4. **Claude responds with:**
   - Full package description
   - Use cases and scenarios
   - Installation command
   - Dependencies and requirements

### Expected Outcome

- Clear understanding of available packages
- Knowledge of what each package provides
- Ability to identify packages useful for your needs
- Ready to install relevant packages

### Variations

- **Filter by category**: "Show me automation packages"
- **Compare packages**: "What's the difference between delay-tasks and sc-git-worktree?"
- **Check package count**: "How many packages are available?"

---

## Use Case 2: Search for Specific Package Functionality

**Scenario**: You need a package to help with CI/CD workflows where you need to wait for GitHub Actions to complete.

**Goal**: Find packages that provide delay, polling, or CI/CD automation capabilities.

### Steps

1. **Search by functionality:**
   ```
   /marketplace search ci automation
   ```
   or naturally:
   ```
   Find packages that help with CI/CD automation
   ```

2. **Review search results:**
   ```
   Found 1 package matching "ci automation":

   • delay-tasks (v0.4.0)
     "Schedule delayed or interval-based actions with minimal heartbeats.
      Ideal for waiting before running checks (e.g., GH Actions, PR status)
      or polling on a bounded interval."
     Tags: delay, polling, tasks, ci, automation

     Install with: /marketplace install delay-tasks --global
   ```

3. **Refine search if needed:**
   ```
   /marketplace search delay polling
   ```

4. **Read package documentation:**
   ```
   Show me the README for delay-tasks
   ```

5. **Install the package:**
   ```
   /marketplace install delay-tasks --global
   ```

### Expected Outcome

- Found the right package for CI/CD needs
- Understood package capabilities
- Successfully installed the package
- Ready to use delay commands in workflows

### Variations

- **Search by tag**: `/marketplace search --tag ci`
- **Search multiple terms**: "Find packages for git and automation"
- **Exclude terms**: "Find automation packages but not git-related"

---

## Use Case 3: Install Package from Marketplace

**Scenario**: You've identified the `delay-tasks` package as useful and want to install it for use across all your projects.

**Goal**: Install the package globally with proper verification.

### Steps

1. **Choose installation scope:**
   ```
   /marketplace install delay-tasks --global
   ```

2. **Monitor installation progress:**
   ```
   Installing delay-tasks to ~/.claude...
   ✓ Validating package: delay-tasks
   ✓ Checking dependencies: none required
   ✓ Installing artifacts:
     - commands/delay.md
     - skills/delay/SKILL.md
     - agents/delay-runner.md
     - agents/delay-waiter.md
     - agents/delay-poller.md
     - scripts/delay-run.py
   ✓ Making scripts executable
   ✓ Updating registry: ~/.claude/agents/registry.yaml
   ✓ Verifying installation

   Successfully installed delay-tasks (v0.4.0)

   Installed artifacts:
   - 1 command: /delay
   - 1 skill: delay-tasks
   - 3 agents: delay-runner, delay-waiter, delay-poller
   - 1 script: delay-run.py
   ```

3. **Verify installation:**
   ```
   Check if delay command is available
   ```

4. **Test the new package:**
   ```
   /delay help
   ```

### Expected Outcome

- Package installed successfully to ~/.claude
- All artifacts (commands, skills, agents, scripts) available
- Registry updated with new package
- Ready to use delay-tasks features

### Variations

- **Local installation**: Use `--local` for project-specific install
- **Force reinstall**: Add `--force` to overwrite existing files
- **Specific registry**: Add `--registry custom-reg` to use non-default registry

---

## Use Case 4: List Packages in Specific Registry

**Scenario**: You have multiple registries configured (default synaptic-canvas and a custom org registry) and want to see what packages are available in each.

**Goal**: Query specific registries to understand their package offerings.

### Steps

1. **List all configured registries:**
   ```
   /marketplace registry list
   ```

2. **Review registry information:**
   ```
   Configured registries:

   * synaptic-canvas    https://github.com/randlee/synaptic-canvas
     path:              docs/registries/nuget/registry.json
     status:            active
     added:             2025-12-04

     my-org             https://github.com/my-org/marketplace
     path:              packages/registry.json
     status:            active
     added:             2025-12-04
   ```

3. **Query specific registry:**
   ```
   /marketplace list --registry my-org
   ```

4. **Compare packages across registries:**
   ```
   Show me packages from my-org registry vs synaptic-canvas
   ```

5. **Switch default registry if needed:**
   ```
   /marketplace registry set-default my-org
   ```

### Expected Outcome

- Clear view of all configured registries
- Understanding of package availability per registry
- Ability to query specific registries
- Knowledge of which registry provides which packages

### Variations

- **Search in specific registry**: `/marketplace search automation --registry my-org`
- **Add new registry**: `/marketplace registry add team-packages https://...`
- **Remove registry**: `/marketplace registry remove old-registry`

---

## Use Case 5: Compare Packages Across Registries

**Scenario**: Multiple registries offer packages with similar functionality, and you need to choose the best one for your needs.

**Goal**: Compare package features, versions, and quality indicators across registries.

### Steps

1. **Search across all registries:**
   ```
   Find all packages related to git workflows
   ```

2. **Claude queries all registries and responds:**
   ```
   Found 3 packages matching "git workflows":

   From synaptic-canvas registry:
   • sc-git-worktree (v0.4.0) - beta
     "Create, manage, scan, and clean up git worktrees"
     Artifacts: 1 command, 1 skill, 4 agents
     Last updated: 2025-12-02

   From my-org registry:
   • git-tools (v1.2.0) - stable
     "Comprehensive git workflow automation"
     Artifacts: 3 commands, 2 skills, 8 agents
     Last updated: 2025-11-15

   From community registry:
   • simple-git (v0.1.0) - alpha
     "Basic git operations"
     Artifacts: 1 command, 2 agents
     Last updated: 2025-10-01
   ```

3. **Compare package details:**
   ```
   Compare sc-git-worktree from synaptic-canvas with git-tools from my-org
   ```

4. **Review comparison:**
   - Version and stability (stable vs beta)
   - Feature completeness (artifacts count)
   - Documentation quality
   - Last update date
   - Publisher verification
   - Dependencies

5. **Make informed decision:**
   ```
   /marketplace install sc-git-worktree --global --registry synaptic-canvas
   ```

### Expected Outcome

- Comprehensive view of similar packages across registries
- Understanding of differences in features and maturity
- Informed decision on which package to install
- Knowledge of registry quality indicators

### Variations

- **Filter by status**: "Show me only stable packages"
- **Sort by date**: "Show newest packages first"
- **Check dependencies**: "Compare dependencies for these packages"

---

## Use Case 6: Update Package Installation

**Scenario**: You have delay-tasks v0.3.0 installed, and v0.4.0 is now available. You want to update to the latest version.

**Goal**: Safely update the package while preserving custom configurations.

### Steps

1. **Check current version:**
   ```
   What version of delay-tasks do I have installed?
   ```

2. **Claude checks and responds:**
   ```
   Currently installed: delay-tasks v0.3.0 (global)
   Latest available: delay-tasks v0.4.0

   Update recommended: Yes
   Breaking changes: No
   ```

3. **Review changelog:**
   ```
   Show me what's new in delay-tasks v0.4.0
   ```

4. **Update the package:**
   ```
   /marketplace install delay-tasks --global --force
   ```

5. **Monitor update process:**
   ```
   Updating delay-tasks from v0.3.0 to v0.4.0...
   ✓ Backing up existing configuration
   ✓ Removing old version files
   ✓ Installing new version
   ✓ Restoring configuration
   ✓ Verifying update

   Successfully updated delay-tasks to v0.4.0

   Changes:
   - Added: New polling strategies
   - Improved: Error handling in delay-runner
   - Fixed: Race condition in interval scheduling
   ```

6. **Verify update:**
   ```
   Test the updated delay command
   ```

### Expected Outcome

- Package updated to latest version
- Configurations preserved where possible
- Understanding of what changed
- Verification that update was successful

### Variations

- **Rollback if needed**: Reinstall specific older version
- **Update all packages**: Check and update all installed packages
- **Preview changes**: See what will change before updating

---

## Use Case 7: Troubleshoot Package Issues

**Scenario**: After installing sc-git-worktree, you're getting errors when trying to use the `/sc-git-worktree` command.

**Goal**: Diagnose and resolve the issue using marketplace troubleshooting capabilities.

### Steps

1. **Report the issue:**
   ```
   I'm getting an error when I try to use /sc-git-worktree
   ```

2. **Claude initiates diagnostics:**
   ```
   Let me help troubleshoot this issue.

   Checking:
   ✓ Package installed: Yes (sc-git-worktree v0.4.0)
   ✓ Command file exists: Yes (~/.claude/commands/sc-git-worktree.md)
   ✓ Agents registered: Yes (4 agents found)
   ✗ Script permissions: Issue found

   Issue identified: Scripts not executable
   ```

3. **Review suggested fix:**
   ```
   The sc-git-worktree scripts are not marked as executable.

   To fix this, run:
   chmod +x ~/.claude/scripts/sc-git-worktree-*.sh

   Or reinstall the package:
   /marketplace install sc-git-worktree --global --force
   ```

4. **Apply the fix:**
   ```
   Reinstall sc-git-worktree with correct permissions
   ```

5. **Verify resolution:**
   ```
   Re-installing sc-git-worktree...
   ✓ Setting executable permissions on scripts
   ✓ Installation complete

   Please try /sc-git-worktree again.
   ```

6. **Test the command:**
   ```
   /sc-git-worktree help
   ```

### Expected Outcome

- Issue diagnosed correctly
- Clear fix provided
- Problem resolved
- Package working as expected

### Common Issues Addressed

1. **Package not found**
   - Cause: Registry configuration issue
   - Fix: Verify registry URL and connectivity

2. **Installation fails**
   - Cause: Permission denied
   - Fix: Check write permissions on ~/.claude

3. **Command not available**
   - Cause: File not copied or in wrong location
   - Fix: Reinstall with --force

4. **Version conflicts**
   - Cause: Multiple versions installed
   - Fix: Uninstall old version first

5. **Dependency errors**
   - Cause: Missing required software
   - Fix: Install dependencies (Python, Git, etc.)

6. **Registry unreachable**
   - Cause: Network issues or invalid URL
   - Fix: Check connection and registry configuration

7. **Corrupted installation**
   - Cause: Partial install or interrupted process
   - Fix: Clean uninstall and fresh install

8. **Script execution errors**
   - Cause: Scripts not executable
   - Fix: chmod +x on script files

### Troubleshooting Workflow

```
Issue reported
    ↓
Run diagnostics
    ↓
Identify root cause
    ↓
Suggest fix
    ↓
Apply fix (automated or manual)
    ↓
Verify resolution
    ↓
Issue resolved ✓
```

### Variations

- **Check logs**: View installation logs for errors
- **Validate config**: Ensure config.yaml is correct
- **Test connectivity**: Verify registry access
- **Clean reinstall**: Remove and reinstall package

---

## Advanced Use Cases

### Use Case 8: Create Custom Registry for Team Packages

**Scenario**: Your team has internal packages that should be shared across the organization.

**Steps**:
1. Create registry.json following schema
2. Host on GitHub or internal server
3. Add to marketplace: `/marketplace registry add team-packages <url>`
4. Team members can now discover and install

### Use Case 9: Automate Package Installation in CI/CD

**Scenario**: New developers need standard packages installed automatically.

**Steps**:
1. Create installation script
2. List required packages
3. Run: `sc-install install <pkg> --global` for each
4. Verify installations in CI pipeline

### Use Case 10: Monitor Package Updates

**Scenario**: Stay informed about new package versions and features.

**Steps**:
1. Check for updates: "Are there updates for my installed packages?"
2. Review changelogs
3. Plan update schedule
4. Test updates in local environment first
5. Roll out to global installation

---

## Tips for Effective Use

### Discovery
- Start with `/marketplace list` to see everything
- Use tags for focused searches
- Read package descriptions thoroughly
- Check artifact counts to gauge package size

### Installation
- Test locally before global install
- Review dependencies first
- Check disk space and permissions
- Verify installation after completing

### Troubleshooting
- Read error messages completely
- Check TROUBLESHOOTING.md first
- Verify prerequisites are met
- Try reinstalling with --force

### Registry Management
- Keep registries up to date
- Remove unused registries
- Use descriptive registry names
- Document custom registries for team

---

## Success Criteria

For each use case, success is achieved when:

1. **Discovery**: User finds relevant packages quickly
2. **Search**: Search results match user intent
3. **Installation**: Package installs without errors
4. **Registry Listing**: User understands available registries
5. **Comparison**: User can make informed decisions
6. **Updates**: Package updates without data loss
7. **Troubleshooting**: Issues are resolved efficiently

---

## Next Steps

After mastering these use cases:

1. Explore advanced features in package documentation
2. Create custom registries for your organization
3. Contribute feedback on package quality
4. Share useful packages with the community

---

**Need help?** Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) or [README.md](./README.md)
