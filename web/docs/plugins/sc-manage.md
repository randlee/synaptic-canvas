<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-manage',
    subtitle: '--install pkg --local',
    type: 'entry',
    details: {
      description: 'Entry point for package management. Parses flags to determine operation: list, install, uninstall, or docs.',
      input: {
        flags: {
          '--list': 'boolean - List all packages with install status',
          '--install': 'string - Package name to install',
          '--uninstall': 'string - Package name to uninstall',
          '--docs': 'string - Package name for documentation',
          '--local': 'boolean - Target repo .claude directory',
          '--global': 'boolean - Target global .claude directory'
        }
      },
      output: {
        operation: 'list | install | uninstall | docs',
        params: '{ package?, scope? }'
      },
      context: ['flags', 'operation', 'package_name', 'scope']
    }
  },
  {
    id: 'list',
    label: 'List Agent',
    subtitle: 'sc-packages-list',
    type: 'agent',
    details: {
      description: 'Enumerates available Synaptic Canvas packages by reading manifest.yaml files. Detects installation status (none/local/global/both) by checking for artifacts in .claude directories.',
      input: {
        sc_repo_path: '/Users/user/Documents/github/synaptic-canvas',
        global_claude_dir: '/Users/user/Documents/.claude'
      },
      output: {
        success: true,
        data: {
          packages: [
            { name: 'sc-delay-tasks', installed: 'global', description: 'Schedule delayed actions' },
            { name: 'sc-git-worktree', installed: 'local', description: 'Manage git worktrees' },
            { name: 'sc-manage', installed: 'global', description: 'Package management' }
          ]
        }
      },
      context: ['packages', 'available_count', 'installed_count'],
      errorCodes: [
        { code: 'LIST_FAILED', recoverable: false, action: 'Verify sc_repo_path and permissions' }
      ]
    }
  },
  {
    id: 'list_success',
    label: 'Display Table',
    subtitle: 'packages listed',
    type: 'success',
    details: {
      description: 'List operation completed. Packages are displayed in a formatted table showing name, installed status, and description.',
      context: ['final_status', 'package_list']
    }
  },
  {
    id: 'docs',
    label: 'Docs Agent',
    subtitle: 'sc-package-docs',
    type: 'agent',
    details: {
      description: 'Locates and returns package documentation (README.md). Provides metadata about the documentation file for the skill to present and handle Q&A.',
      input: {
        package: 'sc-git-worktree',
        sc_repo_path: '/Users/user/Documents/github/synaptic-canvas'
      },
      output: {
        success: true,
        data: {
          package: 'sc-git-worktree',
          readme_path: '/path/packages/sc-git-worktree/README.md',
          size_bytes: 2048
        }
      },
      context: ['readme_path', 'package_metadata'],
      errorCodes: [
        { code: 'DOC_NOT_FOUND', recoverable: false, action: 'Ensure README.md exists in package root' }
      ]
    }
  },
  {
    id: 'docs_success',
    label: 'Show Docs',
    subtitle: 'docs displayed',
    type: 'success',
    details: {
      description: 'Documentation displayed to user. README content is presented and user can ask questions about the package.',
      context: ['final_status', 'docs_content']
    }
  },
  {
    id: 'scope_check',
    label: 'Validate Scope',
    subtitle: 'policy check',
    type: 'gate',
    details: {
      description: 'Validates that the requested scope is allowed for the package. Some packages are local-only (e.g., sc-git-worktree), some are global-only. Reads manifest.yaml install.scope policy.',
      gatePrompt: {
        type: 'validation_gate',
        gate_id: 'scope_validation',
        message: 'Checking if package can be installed in requested scope',
        context: {
          package: 'sc-git-worktree',
          requested_scope: 'global',
          allowed_scope: 'local-only'
        },
        options: {
          proceed: 'Scope is allowed',
          reject: 'Scope violates package policy'
        }
      },
      gateResponse: { proceed: true },
      skipCondition: 'Package allows both scopes',
      context: ['scope_valid', 'policy_check']
    }
  },
  {
    id: 'scope_error',
    label: 'Scope Error',
    subtitle: 'policy violation',
    type: 'error',
    details: {
      description: 'Installation aborted due to scope policy violation. Package cannot be installed in the requested scope (e.g., trying to install sc-git-worktree globally).',
      errorCodes: [
        { code: 'SCOPE_NOT_ALLOWED', recoverable: false, action: 'Use correct scope (--local or --global)' }
      ]
    }
  },
  {
    id: 'install',
    label: 'Install Agent',
    subtitle: 'sc-package-install',
    type: 'agent',
    details: {
      description: 'Installs a package by calling sc-install.py with the appropriate destination. Handles token substitution for local installs (REPO_NAME). Validates package exists and copies all artifacts to target .claude directory.',
      input: {
        package: 'sc-git-worktree',
        scope: 'local',
        sc_repo_path: '/Users/user/Documents/github/synaptic-canvas',
        global_claude_dir: '/Users/user/Documents/.claude'
      },
      output: {
        success: true,
        data: {
          package: 'sc-git-worktree',
          scope: 'local',
          dest: '/path/to/repo/.claude'
        }
      },
      context: ['installed_package', 'install_dest', 'artifacts_copied'],
      errorCodes: [
        { code: 'PACKAGE_NOT_FOUND', recoverable: false, action: 'Verify package name with --list' },
        { code: 'GIT_REPO_REQUIRED', recoverable: false, action: 'Initialize git repo for local install' },
        { code: 'PERMISSION_DENIED', recoverable: false, action: 'Check directory permissions' }
      ]
    }
  },
  {
    id: 'install_success',
    label: 'Install Complete',
    subtitle: 'package ready',
    type: 'success',
    details: {
      description: 'Package successfully installed. All artifacts (commands, skills, agents, scripts) are in place and the package is ready to use.',
      context: ['final_status', 'installed_artifacts', 'next_steps']
    }
  },
  {
    id: 'uninstall',
    label: 'Uninstall Agent',
    subtitle: 'sc-package-uninstall',
    type: 'agent',
    details: {
      description: 'Uninstalls a package by calling sc-install.py uninstall. Removes all artifacts from the target .claude directory. Validates package exists and checks scope policy.',
      input: {
        package: 'sc-delay-tasks',
        scope: 'global',
        sc_repo_path: '/Users/user/Documents/github/synaptic-canvas',
        global_claude_dir: '/Users/user/Documents/.claude'
      },
      output: {
        success: true,
        data: {
          package: 'sc-delay-tasks',
          scope: 'global',
          dest: '/Users/user/Documents/.claude'
        }
      },
      context: ['uninstalled_package', 'artifacts_removed'],
      errorCodes: [
        { code: 'PACKAGE_NOT_FOUND', recoverable: false, action: 'Verify package name with --list' },
        { code: 'NOT_INSTALLED', recoverable: false, action: 'Package not installed in specified scope' },
        { code: 'PERMISSION_DENIED', recoverable: false, action: 'Check directory permissions' }
      ]
    }
  },
  {
    id: 'uninstall_success',
    label: 'Uninstall Complete',
    subtitle: 'package removed',
    type: 'success',
    details: {
      description: 'Package successfully uninstalled. All artifacts have been removed from the target .claude directory.',
      context: ['final_status', 'removed_artifacts']
    }
  }
])

const edges = ref([
  { from: 'command', to: 'list', label: '--list' },
  { from: 'command', to: 'docs', label: '--docs' },
  { from: 'command', to: 'scope_check', label: '--install | --uninstall' },
  { from: 'list', to: 'list_success', label: 'packages enumerated' },
  { from: 'docs', to: 'docs_success', label: 'docs found' },
  { from: 'scope_check', to: 'scope_error', label: 'policy violation' },
  { from: 'scope_check', to: 'install', label: 'valid (install)' },
  { from: 'scope_check', to: 'uninstall', label: 'valid (uninstall)' },
  { from: 'install', to: 'install_success', label: 'installed' },
  { from: 'uninstall', to: 'uninstall_success', label: 'removed' }
])
</script>

# sc-manage

Synaptic Canvas package management for listing, installing, and uninstalling plugins.

<PluginFlowVisualizer
  plugin-name="sc-manage"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-manage` plugin provides centralized package discovery and management for Synaptic Canvas. It enables you to:

- **List** available packages with installation status (none/local/global/both)
- **Install** packages into local (repo `.claude`) or global (user `.claude`) scopes
- **Uninstall** packages from selected scope with clean artifact removal
- **View docs** for any package with interactive Q&A

The plugin enforces package policies (e.g., sc-git-worktree is local-only) and handles token substitution for local installations (REPO_NAME detection).

## Quick Start

```bash
# List all available packages
/sc-manage --list

# Install a package locally (repo-specific)
/sc-manage --install sc-git-worktree --local

# Install a package globally (user-wide)
/sc-manage --install sc-delay-tasks --global

# View package documentation
/sc-manage --docs sc-git-worktree

# Uninstall a package
/sc-manage --uninstall sc-delay-tasks --global
```

## Command Reference

| Flag | Type | Description |
|------|------|-------------|
| `--list` | boolean | List all packages with install status |
| `--install` | string | Package name to install (requires scope) |
| `--uninstall` | string | Package name to uninstall (requires scope) |
| `--docs` | string | Package name to view documentation (alias: `--doc`) |
| `--local` | boolean | Target current repository's `.claude` directory |
| `--global` | boolean | Target global `.claude` directory |

## Workflow States

### Entry Point

The command parser determines the operation based on flags:

- `--list` → List workflow (read-only, shows all packages)
- `--docs <pkg>` → Docs workflow (read-only, displays README)
- `--install <pkg>` → Install workflow (requires `--local` or `--global`)
- `--uninstall <pkg>` → Uninstall workflow (requires `--local` or `--global`)

### Validation Gate

For install and uninstall operations, the plugin validates scope against package policy:

- **Scope Check** — Ensures the requested scope is allowed by the package
  - **Proceed**: Scope is valid, continue to install/uninstall
  - **Reject**: Policy violation (e.g., trying to install local-only package globally)

This gate is automatic and does not require user interaction. If scope is invalid, the workflow terminates immediately with an error.

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `operation`, `package_name`, `scope` |
| List Agent | `packages`, `available_count`, `installed_count` |
| Docs Agent | `readme_path`, `package_metadata` |
| Scope Check | `scope_valid`, `policy_check` |
| Install Agent | `installed_package`, `install_dest`, `artifacts_copied` |
| Uninstall Agent | `uninstalled_package`, `artifacts_removed` |

## Dependencies

This plugin depends on:

- **python3** (≥ 3.8) — For running sc-install.py installer
- **git** (≥ 2.25) — For detecting repo root in local installs
- **Synaptic Canvas repo** — Source of package manifests and artifacts

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `LIST_FAILED` | Error | Verify sc_repo_path and permissions |
| `DOC_NOT_FOUND` | Error | Ensure README.md exists in package |
| `SCOPE_NOT_ALLOWED` | Error | Use correct scope (--local or --global) |
| `PACKAGE_NOT_FOUND` | Error | Verify package name with --list |
| `GIT_REPO_REQUIRED` | Error | Initialize git repo for local install |
| `NOT_INSTALLED` | Warning | Package not in specified scope |
| `PERMISSION_DENIED` | Error | Check directory permissions |

## Package Scope Policies

Some packages enforce scope restrictions:

| Package | Allowed Scopes | Reason |
|---------|----------------|--------|
| `sc-git-worktree` | Local only | Requires repo context (REPO_NAME) |
| `sc-repomix-nuget` | Local only | Operates on specific repository |
| `sc-manage` | Both | General-purpose tool |
| `sc-delay-tasks` | Both | General-purpose utility |

## Related

- [sc-git-worktree](/plugins/sc-git-worktree) — Local-only package for worktree management
- [sc-delay-tasks](/plugins/sc-delay-tasks) — Multi-scope package for scheduling
- [Package Development Guide](/guides/package-development) — Creating new packages
