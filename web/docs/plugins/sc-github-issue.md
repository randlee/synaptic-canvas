<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-github-issue',
    subtitle: '--fix --issue 42',
    type: 'entry',
    details: {
      description: 'Entry point for the GitHub issue workflow. Parses user flags and determines the operation mode.',
      input: {
        flags: {
          '--list': 'boolean - List open issues',
          '--fix': 'boolean - Run full fix workflow',
          '--issue': 'number|URL - Issue to fix',
          '--yolo': 'boolean - Skip confirmation prompts',
          '--repo': 'string - Override repository'
        }
      },
      output: {
        operation: 'list | fix | create | update',
        params: '{ issue_number?, repo?, yolo? }'
      },
      context: ['flags', 'repo', 'operation']
    }
  },
  {
    id: 'intake',
    label: 'Intake Agent',
    subtitle: 'sc-github-issue-intake',
    type: 'agent',
    details: {
      description: 'Fetches issue details from GitHub using the gh CLI. Read-only operation that retrieves issue metadata, body, labels, and assignees.',
      input: {
        issue_number: 'number',
        repo: 'string (owner/repo)'
      },
      output: {
        success: true,
        data: {
          issue: {
            number: 42,
            title: 'Application crashes on startup',
            body: 'Full issue description...',
            labels: ['bug', 'priority-high'],
            assignees: ['alice'],
            state: 'open',
            created_at: '2025-12-01T10:00:00Z'
          }
        }
      },
      context: ['issue'],
      errorCodes: [
        { code: 'GH.AUTH.REQUIRED', recoverable: true, action: 'Run gh auth login' },
        { code: 'GH.ISSUE.NOT_FOUND', recoverable: false, action: 'Verify issue number' },
        { code: 'GH.RATE_LIMIT', recoverable: true, action: 'Wait for rate limit reset' }
      ]
    }
  },
  {
    id: 'gate1',
    label: 'Confirm Fix',
    subtitle: 'proceed?',
    type: 'gate',
    details: {
      description: 'User confirmation gate before creating worktree and implementing fix. Shows issue details and proposed worktree location.',
      gatePrompt: {
        type: 'confirmation_gate',
        gate_id: 'fix_confirmation',
        message: 'Ready to fix issue #42 in isolated worktree?',
        context: {
          issue: { number: 42, title: 'Application crashes on startup' },
          worktree: { path: '/worktrees/fix-issue-42', branch: 'fix-issue-42' }
        },
        options: {
          proceed: 'Create worktree and implement fix',
          cancel: 'Abort workflow'
        }
      },
      gateResponse: { proceed: true },
      skipCondition: '--yolo flag present',
      context: ['gate1_response']
    }
  },
  {
    id: 'worktree',
    label: 'Create Worktree',
    subtitle: 'sc-git-worktree-create',
    type: 'agent',
    details: {
      description: 'Delegates to sc-git-worktree plugin to create an isolated worktree for the fix. The worktree provides a clean environment without affecting the main working directory.',
      input: {
        branch: 'fix-issue-42',
        base: 'main',
        purpose: 'Fix GitHub issue #42'
      },
      output: {
        success: true,
        data: {
          worktree_path: '/worktrees/fix-issue-42',
          branch: 'fix-issue-42',
          base: 'main',
          status: 'clean'
        }
      },
      context: ['worktree_path', 'branch'],
      errorCodes: [
        { code: 'WORKTREE.EXISTS', recoverable: true, action: 'Auto-cleanup or prompt user' },
        { code: 'WORKTREE.DIRTY', recoverable: true, action: 'Commit or stash changes' },
        { code: 'GIT.BRANCH_EXISTS', recoverable: true, action: 'Use existing branch or rename' }
      ]
    }
  },
  {
    id: 'fix',
    label: 'Implement Fix',
    subtitle: 'sc-github-issue-fix',
    type: 'agent',
    details: {
      description: 'The core fix implementation agent. Analyzes the issue, implements code changes, runs tests, and commits. This is where Claude does the actual work.',
      input: {
        issue: '{ number, title, body, labels }',
        worktree_path: '/worktrees/fix-issue-42'
      },
      output: {
        success: true,
        data: {
          files_changed: ['src/config.ts', 'tests/config.test.ts'],
          commits: [{ sha: 'abc123', message: 'Fix #42: App crashes on startup' }],
          tests_passed: true,
          test_output: '15 passed, 0 failed'
        }
      },
      context: ['files_changed', 'commits', 'tests_passed'],
      errorCodes: [
        { code: 'TEST.FAILED', recoverable: true, action: 'Prompt user for decision' },
        { code: 'BUILD.FAILED', recoverable: true, action: 'Attempt to fix build errors' }
      ]
    }
  },
  {
    id: 'gate2',
    label: 'Test Approval',
    subtitle: 'tests failed?',
    type: 'gate',
    details: {
      description: 'Decision gate when tests fail after implementation. User can proceed anyway, retry the fix, or abort.',
      gatePrompt: {
        type: 'decision_gate',
        gate_id: 'test_failure_decision',
        message: 'Tests failed after implementing fix',
        context: {
          test_results: { passed: 12, failed: 3 },
          failures: ['test_startup_sequence', 'test_config_loading']
        },
        options: {
          proceed_anyway: 'Continue to PR despite failures',
          retry_fix: 'Attempt to fix test failures',
          abort: 'Stop workflow'
        }
      },
      gateResponse: { action: 'retry_fix' },
      skipCondition: '--yolo auto-selects abort on failure',
      context: ['gate2_response']
    }
  },
  {
    id: 'pr',
    label: 'Create PR',
    subtitle: 'sc-github-issue-pr',
    type: 'agent',
    details: {
      description: 'Creates a pull request on GitHub linking back to the original issue. Uses gh CLI for PR creation with proper templating.',
      input: {
        issue: '{ number, title }',
        branch: 'fix-issue-42',
        commits: '[{ sha, message }]',
        base: 'main'
      },
      output: {
        success: true,
        data: {
          pr_url: 'https://github.com/owner/repo/pull/123',
          pr_number: 123,
          status: 'open'
        }
      },
      context: ['pr_url', 'pr_number'],
      errorCodes: [
        { code: 'GIT.PUSH_FAILED', recoverable: true, action: 'Check network and retry' },
        { code: 'GH.PR_EXISTS', recoverable: true, action: 'Update existing PR' }
      ]
    }
  },
  {
    id: 'success',
    label: 'Complete',
    subtitle: 'PR created',
    type: 'success',
    details: {
      description: 'Workflow completed successfully. The issue fix has been implemented and a PR is ready for review.',
      context: ['final_status', 'summary']
    }
  },
  {
    id: 'cancel',
    label: 'Cancel',
    subtitle: 'early exit',
    type: 'error',
    details: {
      description: 'Workflow cancelled before fix started. No worktree was created, no cleanup needed.',
      errorCodes: [
        { code: 'USER.CANCELLED', recoverable: false, action: 'No action required' }
      ]
    }
  },
  {
    id: 'abort',
    label: 'Abort',
    subtitle: 'fix abandoned',
    type: 'error',
    details: {
      description: 'Workflow aborted after fix attempt. Worktree was created and may need cleanup.',
      errorCodes: [
        { code: 'USER.ABORTED', recoverable: false, action: 'Clean up worktree with sc-worktree-abort' },
        { code: 'TEST.UNRECOVERABLE', recoverable: false, action: 'Review test failures and fix manually' }
      ]
    }
  }
])

const edges = ref([
  { from: 'command', to: 'intake', label: 'parse flags' },
  { from: 'intake', to: 'gate1', label: 'issue fetched' },
  { from: 'gate1', to: 'worktree', label: 'proceed' },
  { from: 'gate1', to: 'cancel', label: 'cancel' },
  { from: 'worktree', to: 'fix', label: 'worktree ready' },
  { from: 'fix', to: 'pr', label: 'tests pass' },
  { from: 'fix', to: 'gate2', label: 'tests fail' },
  { from: 'gate2', to: 'pr', label: 'proceed' },
  { from: 'gate2', to: 'abort', label: 'abort' },
  { from: 'pr', to: 'success', label: 'PR created' }
])
</script>

# sc-github-issue

GitHub issue lifecycle management with worktree isolation.

<PluginFlowVisualizer
  plugin-name="sc-github-issue"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-github-issue` plugin provides a complete workflow for managing GitHub issues directly from Claude Code. It supports:

- **Listing** open issues in a repository
- **Creating** new issues with proper formatting
- **Updating** existing issues (labels, assignees, status)
- **Fixing** issues with automated implementation in isolated worktrees

The fix workflow is the most powerful feature, orchestrating a full cycle from issue analysis to PR creation.

## Quick Start

```bash
# List open issues
/sc-github-issue --list

# Fix an issue (interactive)
/sc-github-issue --fix --issue 42

# Fix with no prompts (yolo mode)
/sc-github-issue --fix --issue 42 --yolo
```

## Command Reference

| Flag | Type | Description |
|------|------|-------------|
| `--list` | boolean | List open issues in the current repo |
| `--fix` | boolean | Run the full fix workflow |
| `--issue` | number/URL | Issue to operate on (required with `--fix`) |
| `--create` | boolean | Create a new issue interactively |
| `--update` | number | Update an existing issue |
| `--yolo` | boolean | Skip all confirmation prompts |
| `--repo` | string | Override repository (default: current) |

## Workflow States

### Entry Point

The command parser determines the operation mode based on flags:

- `--list` → List workflow (read-only)
- `--fix --issue N` → Fix workflow (full cycle)
- `--create` → Create workflow
- `--update N` → Update workflow

### User Decision Gates

This plugin has two potential user interaction points:

1. **Fix Confirmation** (gate1) — Before creating worktree, confirm the proposed fix
   - **Proceed**: Create worktree and implement fix
   - **Cancel**: Exit early (no cleanup needed)

2. **Test Failure Decision** (gate2) — If tests fail, choose how to proceed
   - **Proceed**: Continue to PR despite test failures
   - **Retry**: Have Claude attempt to fix the failing tests (loops back to fix agent)
   - **Abort**: Stop workflow (worktree cleanup may be needed)

Both gates can be skipped with `--yolo`, which auto-proceeds on success and auto-aborts on failure.

> **Note**: The retry loop (gate2 → fix) is not shown in the diagram for visual clarity, but exists in the actual workflow.

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `repo`, `operation` |
| Intake Agent | `issue` (full details) |
| Gate 1 | `gate1_response` |
| Worktree Agent | `worktree_path`, `branch` |
| Fix Agent | `files_changed`, `commits`, `tests_passed` |
| Gate 2 | `gate2_response` |
| PR Agent | `pr_url`, `pr_number` |

## Dependencies

This plugin depends on:

- **sc-git-worktree** (≥ 0.6.0) — For worktree creation and management
- **gh CLI** (≥ 2.0) — For GitHub API interactions
- **git** (≥ 2.25) — For version control operations

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `GH.AUTH.REQUIRED` | Error | Run `gh auth login` |
| `GH.ISSUE.NOT_FOUND` | Error | Verify issue number |
| `WORKTREE.EXISTS` | Warning | Auto-cleanup available |
| `TEST.FAILED` | Warning | User decision gate |
| `GIT.PUSH_FAILED` | Error | Auto-retry (3x) |

## Related

- [sc-git-worktree](/plugins/sc-git-worktree) — Worktree management (dependency)
- [sc-ci-automation](/plugins/sc-ci-automation) — CI integration (complementary)
