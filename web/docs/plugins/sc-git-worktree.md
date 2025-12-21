<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-git-worktree',
    subtitle: '--create feature-x main',
    type: 'entry',
    details: {
      description: 'Entry point for git worktree management. Parses user flags and determines the operation mode (list, create, update, cleanup, abort).',
      input: {
        flags: {
          '--list/--status': 'boolean - List worktrees and show status',
          '--create': 'args: branch, base - Create worktree',
          '--update': 'args: branch? - Update protected branch(es)',
          '--cleanup': 'args: branch - Clean up merged worktree',
          '--abort': 'args: branch - Abandon worktree',
          '--help': 'boolean - Show options and guidance'
        }
      },
      output: {
        operation: 'list | create | update | cleanup | abort',
        params: '{ branch?, base?, protected_branches }'
      },
      context: ['flags', 'operation', 'branch', 'base']
    }
  },
  {
    id: 'scan',
    label: 'Scan Agent',
    subtitle: 'sc-worktree-scan',
    type: 'agent',
    details: {
      description: 'Read-only scan of worktrees. Lists all worktrees, checks status (clean/dirty), cross-references tracking document, and provides recommendations.',
      input: {
        repo_root: 'string - Current repository path',
        worktree_base: 'string - Base path for worktrees',
        tracking_enabled: 'boolean - Whether tracking is enabled',
        tracking_path: 'string - Path to tracking document'
      },
      output: {
        success: true,
        data: {
          worktrees: [
            { branch: 'feature-x', path: '../repo-worktrees/feature-x', status: 'clean', tracked: true }
          ],
          tracking_missing_rows: [],
          tracking_extra_rows: [],
          recommendations: ['run cleanup on merged branches']
        }
      },
      context: ['worktrees', 'recommendations'],
      errorCodes: [
        { code: 'TRACKING.MISSING', recoverable: true, action: 'Create tracking doc or disable tracking' }
      ]
    }
  },
  {
    id: 'create',
    label: 'Create Agent',
    subtitle: 'sc-worktree-create',
    type: 'agent',
    details: {
      description: 'Creates a new worktree at the standard sibling location. Creates branch if it does not exist, otherwise reuses existing branch. Updates tracking document when enabled.',
      input: {
        branch: 'string - Branch name to use/create',
        base: 'string - Base branch (main, develop, etc.)',
        purpose: 'string - Reason for worktree',
        owner: 'string - Agent or user handle',
        worktree_base: 'string - Base path',
        tracking_enabled: 'boolean',
        tracking_path: 'string'
      },
      output: {
        success: true,
        data: {
          action: 'create',
          branch: 'feature-x',
          path: '../repo-worktrees/feature-x',
          status: 'clean',
          tracking_row: { branch: 'feature-x', base: 'main', purpose: 'implement feature X' },
          tracking_update_required: true
        }
      },
      context: ['worktree_path', 'branch', 'tracking_row'],
      errorCodes: [
        { code: 'WORKTREE.DIRTY', recoverable: false, action: 'Commit or stash changes' },
        { code: 'PATH.EXISTS', recoverable: false, action: 'Choose different branch name' }
      ]
    }
  },
  {
    id: 'update',
    label: 'Update Agent',
    subtitle: 'sc-worktree-update',
    type: 'agent',
    details: {
      description: 'Updates protected branches (main, develop, master) in their worktrees by pulling latest changes. Handles merge conflicts by returning control to caller.',
      input: {
        branch: 'string? - Protected branch to update (omit for all)',
        path: 'string - Worktree path',
        protected_branches: 'string[] - List of protected branches',
        tracking_enabled: 'boolean',
        tracking_path: 'string'
      },
      output: {
        success: true,
        data: {
          action: 'update',
          branch: 'main',
          commits_pulled: 5,
          old_commit: 'abc1234',
          new_commit: 'def5678',
          tracking_update: 'last_checked updated'
        }
      },
      context: ['commits_pulled', 'old_commit', 'new_commit'],
      errorCodes: [
        { code: 'WORKTREE.DIRTY', recoverable: true, action: 'Commit or stash changes' },
        { code: 'MERGE.CONFLICTS', recoverable: true, action: 'Resolve conflicts in worktree and commit' },
        { code: 'BRANCH.NOT_PROTECTED', recoverable: false, action: 'Use cleanup/abort for non-protected branches' }
      ]
    }
  },
  {
    id: 'gate_conflicts',
    label: 'Merge Conflicts',
    subtitle: 'conflicts detected?',
    type: 'gate',
    details: {
      description: 'Decision gate when merge conflicts occur during protected branch update. User must resolve conflicts manually in the worktree.',
      gatePrompt: {
        type: 'user_resolution_required',
        gate_id: 'merge_conflicts',
        message: 'Merge conflicts detected during pull',
        context: {
          conflicted_files: ['src/foo.cs', 'src/bar.cs'],
          worktree_path: '../repo-worktrees/main',
          resolution_steps: [
            'Navigate to worktree',
            'Resolve conflicts in listed files',
            'Stage resolved files with git add',
            'Commit the merge',
            'Re-run update to verify'
          ]
        },
        options: {
          resolved: 'User resolves conflicts and re-runs update',
          abort_merge: 'User aborts merge with git merge --abort'
        }
      },
      gateResponse: { action: 'resolved' },
      skipCondition: 'No conflicts detected',
      context: ['conflict_resolution_status']
    }
  },
  {
    id: 'gate_cleanup',
    label: 'Cleanup Check',
    subtitle: 'merged & clean?',
    type: 'gate',
    details: {
      description: 'Decision gate before cleanup. Verifies worktree is clean, branch is merged (for non-protected), and confirms protected branch handling.',
      gatePrompt: {
        type: 'confirmation_gate',
        gate_id: 'cleanup_confirmation',
        message: 'Ready to clean up worktree?',
        context: {
          branch: 'feature-x',
          is_protected: false,
          merged: true,
          unique_commits: 0,
          worktree_path: '../repo-worktrees/feature-x',
          actions: {
            protected: 'Remove worktree only (preserve branch)',
            non_protected_merged: 'Remove worktree and delete branch (local + remote)',
            non_protected_unmerged: 'Requires explicit approval to delete unmerged branch'
          }
        },
        options: {
          proceed: 'Clean up worktree and delete branch if appropriate',
          cancel: 'Keep worktree'
        }
      },
      gateResponse: { proceed: true },
      skipCondition: 'Standard cleanup for merged non-protected branches',
      context: ['cleanup_approval']
    }
  },
  {
    id: 'cleanup',
    label: 'Cleanup Agent',
    subtitle: 'sc-worktree-cleanup',
    type: 'agent',
    details: {
      description: 'Safely removes completed worktrees. For non-protected branches: deletes branch locally and remotely if merged. For protected branches: removes worktree only, never deletes branch.',
      input: {
        branch: 'string - Branch/worktree to clean',
        path: 'string - Worktree path',
        merged: 'boolean - Whether branch is merged',
        require_clean: 'boolean - Require clean worktree',
        protected_branches: 'string[] - Protected branch list (required)',
        tracking_enabled: 'boolean',
        tracking_path: 'string'
      },
      output: {
        success: true,
        data: {
          action: 'cleanup',
          branch: 'feature-x',
          is_protected: false,
          merged: true,
          worktree_removed: true,
          branch_deleted_local: true,
          branch_deleted_remote: true,
          tracking_update: 'removed'
        }
      },
      context: ['worktree_removed', 'branch_deleted', 'tracking_update'],
      errorCodes: [
        { code: 'WORKTREE.DIRTY', recoverable: true, action: 'Commit or request explicit approval' },
        { code: 'WORKTREE.UNMERGED', recoverable: true, action: 'Merge branch or provide explicit approval' },
        { code: 'PROTECTED_BRANCHES.MISSING', recoverable: false, action: 'Provide protected_branches list' }
      ]
    }
  },
  {
    id: 'gate_abort',
    label: 'Abort Confirm',
    subtitle: 'discard work?',
    type: 'gate',
    details: {
      description: 'Decision gate before abandoning worktree. Confirms user wants to discard uncommitted changes and optionally delete branch.',
      gatePrompt: {
        type: 'confirmation_gate',
        gate_id: 'abort_confirmation',
        message: 'Abandon worktree and discard work?',
        context: {
          branch: 'feature-x',
          is_protected: false,
          dirty: true,
          uncommitted_changes: ['M src/foo.cs', '?? src/bar.txt'],
          worktree_path: '../repo-worktrees/feature-x',
          actions: {
            protected: 'Remove worktree only (preserve branch)',
            non_protected: 'Remove worktree and optionally delete branch'
          }
        },
        options: {
          proceed: 'Abandon worktree and discard all changes',
          cancel: 'Keep worktree and preserve work'
        }
      },
      gateResponse: { proceed: true, allow_force: true, allow_delete_branch: false },
      skipCondition: 'Never skipped (explicit approval always required)',
      context: ['abort_approval', 'allow_force', 'allow_delete_branch']
    }
  },
  {
    id: 'abort',
    label: 'Abort Agent',
    subtitle: 'sc-worktree-abort',
    type: 'agent',
    details: {
      description: 'Abandons a worktree and discards work. For non-protected branches: optionally deletes branch with explicit approval. For protected branches: removes worktree only, never deletes branch.',
      input: {
        branch: 'string - Branch/worktree to abandon',
        path: 'string - Worktree path',
        allow_delete_branch: 'boolean - Explicit approval to delete branch',
        allow_force: 'boolean - Approval to force-remove dirty worktree',
        protected_branches: 'string[] - Protected branch list (required)',
        tracking_enabled: 'boolean',
        tracking_path: 'string'
      },
      output: {
        success: true,
        data: {
          action: 'abort',
          branch: 'feature-x',
          is_protected: false,
          worktree_removed: true,
          branch_deleted_local: false,
          branch_deleted_remote: false,
          tracking_update: 'removed'
        }
      },
      context: ['worktree_removed', 'branch_deleted', 'tracking_update'],
      errorCodes: [
        { code: 'WORKTREE.DIRTY', recoverable: true, action: 'Provide allow_force approval' },
        { code: 'PROTECTED_BRANCHES.MISSING', recoverable: false, action: 'Provide protected_branches list' }
      ]
    }
  },
  {
    id: 'success_list',
    label: 'Status Displayed',
    subtitle: 'worktree list',
    type: 'success',
    details: {
      description: 'Successfully listed all worktrees with status, tracking information, and recommendations. No mutations performed.',
      context: ['worktrees', 'tracking_status', 'recommendations']
    }
  },
  {
    id: 'success_create',
    label: 'Worktree Created',
    subtitle: 'ready to use',
    type: 'success',
    details: {
      description: 'Successfully created worktree with clean status. Tracking document updated if enabled. Worktree is ready for development work.',
      context: ['worktree_path', 'branch', 'status', 'tracking_row']
    }
  },
  {
    id: 'success_update',
    label: 'Branch Updated',
    subtitle: 'commits pulled',
    type: 'success',
    details: {
      description: 'Successfully pulled latest changes into protected branch worktree. Tracking document updated with last_checked timestamp.',
      context: ['commits_pulled', 'new_commit', 'tracking_update']
    }
  },
  {
    id: 'success_cleanup',
    label: 'Cleaned Up',
    subtitle: 'worktree removed',
    type: 'success',
    details: {
      description: 'Successfully cleaned up worktree. For non-protected branches: branch deleted locally and remotely if merged. For protected branches: worktree removed only.',
      context: ['worktree_removed', 'branch_deleted', 'tracking_update']
    }
  },
  {
    id: 'success_abort',
    label: 'Abandoned',
    subtitle: 'work discarded',
    type: 'success',
    details: {
      description: 'Successfully abandoned worktree. Work discarded. Branch optionally deleted for non-protected branches with explicit approval.',
      context: ['worktree_removed', 'branch_deleted', 'tracking_update']
    }
  },
  {
    id: 'error_dirty',
    label: 'Dirty Worktree',
    subtitle: 'uncommitted changes',
    type: 'error',
    details: {
      description: 'Operation blocked due to uncommitted changes in worktree. User must commit, stash, or provide explicit approval to proceed.',
      errorCodes: [
        { code: 'WORKTREE.DIRTY', recoverable: true, action: 'Commit/stash changes or provide approval' }
      ]
    }
  },
  {
    id: 'error_config',
    label: 'Config Error',
    subtitle: 'missing config',
    type: 'error',
    details: {
      description: 'Operation failed due to missing or invalid configuration. Protected branches list is required for cleanup, abort, and update operations.',
      errorCodes: [
        { code: 'PROTECTED_BRANCHES.MISSING', recoverable: false, action: 'Provide protected_branches list from git_flow config' },
        { code: 'BRANCH.NOT_PROTECTED', recoverable: false, action: 'Use cleanup/abort for non-protected branches' }
      ]
    }
  },
  {
    id: 'cancel_operation',
    label: 'Cancelled',
    subtitle: 'user cancelled',
    type: 'error',
    details: {
      description: 'Operation cancelled by user before any changes were made. No cleanup needed.',
      errorCodes: [
        { code: 'USER.CANCELLED', recoverable: false, action: 'No action required' }
      ]
    }
  }
])

const edges = ref([
  { from: 'command', to: 'scan', label: '--list/--status' },
  { from: 'command', to: 'create', label: '--create' },
  { from: 'command', to: 'update', label: '--update' },
  { from: 'command', to: 'gate_cleanup', label: '--cleanup' },
  { from: 'command', to: 'gate_abort', label: '--abort' },
  { from: 'scan', to: 'success_list', label: 'status shown' },
  { from: 'create', to: 'success_create', label: 'worktree created' },
  { from: 'create', to: 'error_dirty', label: 'dirty state' },
  { from: 'update', to: 'gate_conflicts', label: 'conflicts detected' },
  { from: 'update', to: 'success_update', label: 'clean pull' },
  { from: 'update', to: 'error_dirty', label: 'dirty worktree' },
  { from: 'update', to: 'error_config', label: 'not protected' },
  { from: 'gate_conflicts', to: 'success_update', label: 'resolved' },
  { from: 'gate_conflicts', to: 'cancel_operation', label: 'abort merge' },
  { from: 'gate_cleanup', to: 'cleanup', label: 'proceed' },
  { from: 'gate_cleanup', to: 'cancel_operation', label: 'cancel' },
  { from: 'cleanup', to: 'success_cleanup', label: 'cleaned' },
  { from: 'cleanup', to: 'error_dirty', label: 'dirty/unmerged' },
  { from: 'cleanup', to: 'error_config', label: 'config missing' },
  { from: 'gate_abort', to: 'abort', label: 'proceed' },
  { from: 'gate_abort', to: 'cancel_operation', label: 'cancel' },
  { from: 'abort', to: 'success_abort', label: 'abandoned' },
  { from: 'abort', to: 'error_dirty', label: 'no force approval' },
  { from: 'abort', to: 'error_config', label: 'config missing' }
])
</script>

# sc-git-worktree

Git worktree management with parallel development isolation and protected branch safeguards.

<PluginFlowVisualizer
  plugin-name="sc-git-worktree"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-git-worktree` plugin provides comprehensive git worktree management for parallel development workflows. It supports:

- **Listing** worktrees with status and tracking information
- **Creating** worktrees with automatic branch creation and tracking
- **Updating** protected branches (main, develop, master) in their worktrees
- **Cleaning up** merged worktrees with automatic branch deletion for non-protected branches
- **Aborting** abandoned work with safe discard and optional branch deletion

The plugin enforces a standard sibling-folder layout (`../repo-worktrees/<branch>`) and provides optional tracking documents for multi-worktree coordination. Protected branch safeguards prevent accidental deletion of critical branches.

## Quick Start

```bash
# List all worktrees and show status
/sc-git-worktree --list

# Create a feature branch worktree from main
/sc-git-worktree --create feature-x main

# Update protected branch in its worktree
/sc-git-worktree --update main

# Clean up merged worktree (removes worktree and deletes branch if merged)
/sc-git-worktree --cleanup feature-x

# Abandon unfinished work (requires confirmation)
/sc-git-worktree --abort experiment-branch
```

## Command Reference

| Flag | Arguments | Description |
|------|-----------|-------------|
| `--list` / `--status` | none | List worktrees with status and tracking sync |
| `--create` | branch, base | Create worktree (and branch if needed) from base |
| `--update` | branch? | Update protected branch(es); omit branch for all |
| `--cleanup` | branch | Remove worktree; delete branch if merged (non-protected) |
| `--abort` | branch | Abandon worktree and discard work (requires approval) |
| `--help` | none | Show available options and guidance |

## Workflow States

### Entry Point

The command parser determines the operation mode based on flags:

- `--list` or `--status` → Scan workflow (read-only, shows worktree status)
- `--create branch base` → Create workflow (new worktree from base branch)
- `--update [branch]` → Update workflow (pull latest for protected branches)
- `--cleanup branch` → Cleanup workflow (remove merged worktree)
- `--abort branch` → Abort workflow (discard work)

### User Decision Gates

This plugin has multiple potential user interaction points:

1. **Merge Conflicts** (gate_conflicts) — When updating protected branches encounters conflicts
   - **Resolved**: User navigates to worktree, resolves conflicts, commits, and re-runs update
   - **Abort Merge**: User runs `git merge --abort` and keeps current state

2. **Cleanup Confirmation** (gate_cleanup) — Before cleaning up worktree
   - **Proceed**: Remove worktree and delete branch if appropriate
   - **Cancel**: Keep worktree and continue working
   - Auto-proceeds for standard merged non-protected branches

3. **Abort Confirmation** (gate_abort) — Before abandoning work (always required)
   - **Proceed**: Discard all changes and remove worktree
   - **Cancel**: Keep worktree and preserve work
   - Requires explicit approval for dirty worktrees and branch deletion

### Protected Branch Handling

Protected branches (main, develop, master) have special rules:

- **Update**: Only protected branches can be updated in worktrees
- **Cleanup**: Protected branches are NEVER deleted (worktree removed only)
- **Abort**: Protected branches are NEVER deleted (worktree removed only)
- **Configuration**: Protected branches must be configured via `git_flow` config:

```yaml
git_flow:
  enabled: true
  main_branch: "main"
  develop_branch: "develop"

protected_branches:
  - "main"
  - "develop"
  - "master"
```

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `operation`, `branch`, `base` |
| Scan Agent | `worktrees`, `recommendations`, `tracking_status` |
| Create Agent | `worktree_path`, `branch`, `status`, `tracking_row` |
| Update Agent | `commits_pulled`, `old_commit`, `new_commit` |
| Conflict Gate | `conflict_resolution_status`, `conflicted_files` |
| Cleanup Gate | `cleanup_approval`, `is_protected`, `merged` |
| Cleanup Agent | `worktree_removed`, `branch_deleted`, `tracking_update` |
| Abort Gate | `abort_approval`, `allow_force`, `allow_delete_branch` |
| Abort Agent | `worktree_removed`, `branch_deleted`, `tracking_update` |

## Dependencies

This plugin depends on:

- **git** (≥ 2.20) — For worktree management and version control
- **git worktree** support — Built-in git feature for parallel working directories

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `WORKTREE.DIRTY` | Warning | Commit/stash or provide explicit approval |
| `WORKTREE.UNMERGED` | Warning | Merge branch or provide explicit approval |
| `MERGE.CONFLICTS` | Warning | Resolve conflicts manually in worktree |
| `BRANCH.NOT_PROTECTED` | Error | Use cleanup/abort for non-protected branches |
| `PROTECTED_BRANCHES.MISSING` | Error | Provide protected_branches from git_flow config |
| `PATH.EXISTS` | Error | Choose different branch name |
| `TRACKING.MISSING` | Warning | Create tracking doc or disable tracking |

## Tracking Documents

The plugin optionally maintains a tracking document at `../repo-worktrees/worktree-tracking.md` with:

- Branch name and worktree path
- Base branch and creation date
- Purpose and owner information
- Status (active, merged, abandoned)
- Last checked timestamp
- Notes and issues

Tracking can be disabled by setting `tracking_enabled: false` in agent parameters.

## Related

- [sc-github-issue](/plugins/sc-github-issue) — Issue management (uses sc-git-worktree for isolation)
- [sc-ci-automation](/plugins/sc-ci-automation) — CI integration (complementary for testing)
