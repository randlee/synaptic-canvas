<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-ci-automation',
    subtitle: '--test --yolo',
    type: 'entry',
    details: {
      description: 'Entry point for the CI automation workflow. Parses user flags and determines the operation mode (build-only, test, or full pipeline).',
      input: {
        flags: {
          '--build': 'boolean - Pull + build only (skip tests/PR)',
          '--test': 'boolean - Pull + build + test (skip commit/push/PR)',
          '--dest': 'string - Override target branch for PR',
          '--src': 'string - Override source branch/worktree',
          '--allow-warnings': 'boolean - Allow warnings to pass gates',
          '--patch': 'boolean - Increment patch version before building',
          '--yolo': 'boolean - Auto-commit/push/PR after gates pass'
        }
      },
      output: {
        operation: 'build | test | full',
        params: '{ src_branch?, dest_branch?, allow_warnings?, yolo? }'
      },
      context: ['flags', 'operation', 'src_branch', 'dest_branch']
    }
  },
  {
    id: 'validate',
    label: 'Validate Agent',
    subtitle: 'ci-validate-agent',
    type: 'agent',
    details: {
      description: 'Pre-flight checks to ensure prerequisites are met. Validates clean repo, config presence, and authentication for PR operations.',
      input: {
        repo: 'string (owner/repo)',
        allow_dirty: 'boolean (default: false)',
        config_path: 'string (.claude/ci-automation.yaml)',
        auth_required: 'boolean'
      },
      output: {
        success: true,
        data: {
          summary: 'Validation passed',
          actions: []
        }
      },
      context: ['validation_status'],
      errorCodes: [
        { code: 'VALIDATION.DIRTY_REPO', recoverable: false, action: 'Commit or stash changes' },
        { code: 'VALIDATION.CONFIG_MISSING', recoverable: true, action: 'Create config file' },
        { code: 'VALIDATION.AUTH_MISSING', recoverable: true, action: 'Set GITHUB_TOKEN' }
      ]
    }
  },
  {
    id: 'pull',
    label: 'Pull Agent',
    subtitle: 'ci-pull-agent',
    type: 'agent',
    details: {
      description: 'Pulls latest changes from target branch and handles simple merge conflicts. Ensures working tree is up-to-date before build.',
      input: {
        repo: 'string (owner/repo)',
        dest_branch: 'string (default: main)',
        src_branch: 'string (current branch)'
      },
      output: {
        success: true,
        data: {
          summary: 'Pulled successfully',
          conflicts_resolved: 0,
          commits_pulled: 3
        }
      },
      context: ['pull_status', 'commits_pulled'],
      errorCodes: [
        { code: 'PULL.MERGE_CONFLICT', recoverable: true, action: 'Auto-resolve or escalate' },
        { code: 'PULL.NETWORK_ERROR', recoverable: true, action: 'Retry with backoff' }
      ]
    }
  },
  {
    id: 'build',
    label: 'Build Agent',
    subtitle: 'ci-build-agent',
    type: 'agent',
    details: {
      description: 'Executes build command from config and classifies failures. Detects project type (.NET/Python/Node) and runs appropriate build steps.',
      input: {
        build_command: 'string (e.g., dotnet build)',
        allow_warnings: 'boolean',
        warn_patterns: 'string[] (regex patterns)'
      },
      output: {
        success: true,
        data: {
          summary: 'Build passed',
          warnings: [],
          duration_seconds: 12
        }
      },
      context: ['build_status', 'build_warnings'],
      errorCodes: [
        { code: 'BUILD.COMPILE_FAILED', recoverable: true, action: 'Route to fix agent' },
        { code: 'BUILD.DEPENDENCY_MISSING', recoverable: true, action: 'Route to fix agent' },
        { code: 'BUILD.WARNINGS_EXCEEDED', recoverable: true, action: 'Route to fix agent or block' }
      ]
    }
  },
  {
    id: 'gate1',
    label: 'Build Failed?',
    subtitle: 'fixable?',
    type: 'gate',
    details: {
      description: 'Decision gate when build fails. Determines if issue is straightforward enough for auto-fix or requires root-cause analysis.',
      gatePrompt: {
        type: 'decision_gate',
        gate_id: 'build_failure_decision',
        message: 'Build failed with errors',
        context: {
          errors: ['Missing dependency foo', 'Import not found'],
          classification: 'straightforward'
        },
        options: {
          auto_fix: 'Route to fix agent',
          analyze: 'Route to root-cause agent',
          abort: 'Stop workflow'
        }
      },
      gateResponse: { action: 'auto_fix' },
      skipCondition: 'Build passed',
      context: ['gate1_response']
    }
  },
  {
    id: 'fix',
    label: 'Fix Agent',
    subtitle: 'ci-fix-agent',
    type: 'agent',
    details: {
      description: 'Applies straightforward fixes for build/test failures. Handles missing imports, formatting issues, obvious type errors. Low-risk changes only.',
      input: {
        issue_type: 'BUILD | TEST | WARN',
        details: 'string (compiler/test output)',
        files: 'string[] (affected files)',
        allow_warnings: 'boolean'
      },
      output: {
        success: true,
        data: {
          summary: 'Applied straightforward fixes',
          patch_summary: 'Added missing import; updated dependency',
          risk: 'low',
          files_changed: ['src/app.py'],
          followups: []
        }
      },
      context: ['fix_applied', 'files_changed'],
      errorCodes: [
        { code: 'FIX.NOT_STRAIGHTFORWARD', recoverable: false, action: 'Escalate to root-cause' },
        { code: 'FIX.TOO_MANY_FILES', recoverable: false, action: 'Escalate to root-cause' }
      ]
    }
  },
  {
    id: 'test',
    label: 'Test Agent',
    subtitle: 'ci-test-agent',
    type: 'agent',
    details: {
      description: 'Runs test suite from config and classifies failures/warnings. Detects project type and executes appropriate test commands.',
      input: {
        test_command: 'string (e.g., dotnet test)',
        allow_warnings: 'boolean',
        warn_patterns: 'string[]'
      },
      output: {
        success: true,
        data: {
          summary: 'Tests passed',
          passed: 42,
          failed: 0,
          warnings: [],
          duration_seconds: 25
        }
      },
      context: ['test_status', 'test_results'],
      errorCodes: [
        { code: 'TEST.FAILED', recoverable: true, action: 'Route to fix agent' },
        { code: 'TEST.WARNINGS_EXCEEDED', recoverable: true, action: 'Route to fix agent or block' },
        { code: 'TEST.TIMEOUT', recoverable: true, action: 'Retry or adjust timeout' }
      ]
    }
  },
  {
    id: 'gate2',
    label: 'Test Failed?',
    subtitle: 'fixable?',
    type: 'gate',
    details: {
      description: 'Decision gate when tests fail. Determines if failures are straightforward enough for auto-fix or require root-cause analysis.',
      gatePrompt: {
        type: 'decision_gate',
        gate_id: 'test_failure_decision',
        message: 'Tests failed',
        context: {
          failed: 2,
          failures: ['test_startup_sequence', 'test_config_loading'],
          classification: 'straightforward'
        },
        options: {
          auto_fix: 'Route to fix agent',
          analyze: 'Route to root-cause agent',
          abort: 'Stop workflow'
        }
      },
      gateResponse: { action: 'auto_fix' },
      skipCondition: 'Tests passed',
      context: ['gate2_response']
    }
  },
  {
    id: 'rootcause',
    label: 'Root Cause Agent',
    subtitle: 'ci-root-cause-agent',
    type: 'agent',
    details: {
      description: 'Analyzes unresolved failures and provides actionable recommendations when auto-fix is not possible. Produces clear guidance for human intervention.',
      input: {
        repo: 'string (owner/repo)',
        errors: '[{ code, message, files }]'
      },
      output: {
        success: true,
        data: {
          summary: 'Build failed due to missing dependency',
          root_causes: [{
            category: 'BUILD.DEPENDENCY_MISSING',
            description: 'Package foo missing',
            affected_files: ['requirements.txt'],
            confidence: 'high'
          }],
          recommendations: [{
            action: 'Add foo>=2.0.0 to requirements.txt',
            rationale: 'Dependency missing',
            estimated_effort: '5m',
            risk: 'low'
          }],
          blocking: true,
          requires_human_input: true
        }
      },
      context: ['root_causes', 'recommendations']
    }
  },
  {
    id: 'gate3',
    label: 'PR Confirmation',
    subtitle: 'proceed?',
    type: 'gate',
    details: {
      description: 'User confirmation gate before creating PR. Shows summary of changes and asks permission to commit/push/PR.',
      gatePrompt: {
        type: 'confirmation_gate',
        gate_id: 'pr_confirmation',
        message: 'All quality gates passed. Create PR?',
        context: {
          files_changed: ['src/app.py', 'tests/app.test.py'],
          dest_branch: 'main',
          warnings: 0
        },
        options: {
          proceed: 'Commit, push, and create PR',
          cancel: 'Stop before PR'
        }
      },
      gateResponse: { proceed: true },
      skipCondition: '--yolo flag present',
      context: ['gate3_response']
    }
  },
  {
    id: 'pr',
    label: 'Create PR',
    subtitle: 'ci-pr-agent',
    type: 'agent',
    details: {
      description: 'Commits changes, pushes branch, and creates pull request on GitHub. Uses PR template if configured.',
      input: {
        repo: 'string (owner/repo)',
        src_branch: 'string (feature-x)',
        dest_branch: 'string (main)',
        pr_title: 'string',
        pr_body: 'string',
        pr_template_path: 'string (.github/PULL_REQUEST_TEMPLATE.md)',
        allow_warnings: 'boolean'
      },
      output: {
        success: true,
        data: {
          summary: 'PR created',
          pr_url: 'https://github.com/owner/repo/pull/123',
          branch: 'feature-x'
        }
      },
      context: ['pr_url', 'pr_number'],
      errorCodes: [
        { code: 'PR.NO_CHANGES', recoverable: false, action: 'Skip PR' },
        { code: 'PR.PUSH_FAILED', recoverable: true, action: 'Retry push' },
        { code: 'PR.ALREADY_EXISTS', recoverable: true, action: 'Update existing PR' }
      ]
    }
  },
  {
    id: 'success',
    label: 'Complete',
    subtitle: 'PR created',
    type: 'success',
    details: {
      description: 'Workflow completed successfully. All quality gates passed and PR is ready for review.',
      context: ['final_status', 'summary']
    }
  },
  {
    id: 'build-only',
    label: 'Build Complete',
    subtitle: '--build mode',
    type: 'success',
    details: {
      description: 'Build-only workflow completed. Tests and PR creation skipped per --build flag.',
      context: ['build_status']
    }
  },
  {
    id: 'test-only',
    label: 'Test Complete',
    subtitle: '--test mode',
    type: 'success',
    details: {
      description: 'Test workflow completed. PR creation skipped per --test flag.',
      context: ['test_status', 'test_results']
    }
  },
  {
    id: 'analysis',
    label: 'Analysis Complete',
    subtitle: 'needs human review',
    type: 'error',
    details: {
      description: 'Workflow stopped after root-cause analysis. Issues require human intervention.',
      errorCodes: [
        { code: 'ANALYSIS.MANUAL_REQUIRED', recoverable: false, action: 'Review recommendations and fix manually' }
      ]
    }
  },
  {
    id: 'abort',
    label: 'Abort',
    subtitle: 'quality gate failed',
    type: 'error',
    details: {
      description: 'Workflow aborted due to unresolvable failures or user decision.',
      errorCodes: [
        { code: 'USER.ABORTED', recoverable: false, action: 'Review failures and retry' },
        { code: 'GATE.BLOCKED', recoverable: false, action: 'Fix issues manually' }
      ]
    }
  },
  {
    id: 'cancel',
    label: 'Cancel',
    subtitle: 'user declined PR',
    type: 'error',
    details: {
      description: 'User declined to create PR. Changes remain committed locally.',
      errorCodes: [
        { code: 'USER.CANCELLED', recoverable: false, action: 'No action required' }
      ]
    }
  }
])

const edges = ref([
  { from: 'command', to: 'validate', label: 'parse flags' },
  { from: 'validate', to: 'pull', label: 'validation passed' },
  { from: 'pull', to: 'build', label: 'pulled latest' },
  { from: 'build', to: 'gate1', label: 'build failed' },
  { from: 'build', to: 'build-only', label: '--build mode' },
  { from: 'build', to: 'test', label: 'build passed' },
  { from: 'gate1', to: 'fix', label: 'auto-fix' },
  { from: 'gate1', to: 'rootcause', label: 'analyze' },
  { from: 'gate1', to: 'abort', label: 'abort' },
  { from: 'fix', to: 'build', label: 'fixes applied' },
  { from: 'test', to: 'gate2', label: 'tests failed' },
  { from: 'test', to: 'test-only', label: '--test mode' },
  { from: 'test', to: 'gate3', label: 'tests passed' },
  { from: 'gate2', to: 'fix', label: 'auto-fix' },
  { from: 'gate2', to: 'rootcause', label: 'analyze' },
  { from: 'gate2', to: 'abort', label: 'abort' },
  { from: 'rootcause', to: 'analysis', label: 'recommendations' },
  { from: 'gate3', to: 'pr', label: 'proceed' },
  { from: 'gate3', to: 'cancel', label: 'cancel' },
  { from: 'pr', to: 'success', label: 'PR created' }
])
</script>

# sc-ci-automation

Run CI quality gates with optional auto-fix and PR creation.

<PluginFlowVisualizer
  plugin-name="sc-ci-automation"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-ci-automation` plugin provides an automated CI workflow that runs quality gates and optionally fixes issues and creates PRs. It supports:

- **Build-only** mode (`--build`) - Pull and build without tests or PR
- **Test** mode (`--test`) - Pull, build, and test without PR creation
- **Full pipeline** - Pull → build → test → fix → PR with optional auto-commit
- **Auto-fix** - Straightforward fixes for common build/test failures
- **Root-cause analysis** - Deep analysis when auto-fix isn't possible

The workflow is conservative by default, stopping before commit/push/PR unless `--yolo` mode is enabled.

## Quick Start

```bash
# Run tests without creating PR
/sc-ci-automation --test

# Full pipeline with auto-PR after gates pass
/sc-ci-automation --yolo

# Build and test with version bump
/sc-ci-automation --patch --yolo

# Allow warnings to pass quality gates
/sc-ci-automation --allow-warnings --yolo
```

## Command Reference

| Flag | Type | Description |
|------|------|-------------|
| `--build` | boolean | Pull + build only (skip tests/PR) |
| `--test` | boolean | Pull + build + test (skip commit/push/PR) |
| `--dest` | string | Override target branch for PR (default: inferred) |
| `--src` | string | Override source branch/worktree (default: current) |
| `--allow-warnings` | boolean | Allow warnings to pass quality gates |
| `--patch` | boolean | Increment patch version before building |
| `--yolo` | boolean | Auto-commit/push/PR after gates pass |
| `--help` | boolean | Show usage and examples |

## Workflow States

### Entry Point

The command parser determines the operation mode based on flags:

- No flags → Full pipeline (conservative mode)
- `--build` → Build-only workflow
- `--test` → Test workflow (no PR)
- `--yolo` → Full pipeline with auto-PR

### User Decision Gates

This plugin has three potential user interaction points:

1. **Build Failure Decision** (gate1) — When build fails, choose how to proceed
   - **Auto-fix**: Route to fix agent for straightforward fixes
   - **Analyze**: Route to root-cause agent for deep analysis
   - **Abort**: Stop workflow

2. **Test Failure Decision** (gate2) — When tests fail, choose how to proceed
   - **Auto-fix**: Route to fix agent for straightforward fixes
   - **Analyze**: Route to root-cause agent for deep analysis
   - **Abort**: Stop workflow

3. **PR Confirmation** (gate3) — Before creating PR, confirm changes
   - **Proceed**: Commit, push, and create PR
   - **Cancel**: Stop before PR creation

All gates can be skipped with `--yolo`, which auto-proceeds when gates pass and auto-aborts on unrecoverable failures.

> **Note**: The fix agent can loop back to build/test for retry attempts. These loops are not shown in the diagram for visual clarity.

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `operation`, `src_branch`, `dest_branch` |
| Validate Agent | `validation_status` |
| Pull Agent | `pull_status`, `commits_pulled` |
| Build Agent | `build_status`, `build_warnings` |
| Gate 1 | `gate1_response` |
| Fix Agent | `fix_applied`, `files_changed` |
| Test Agent | `test_status`, `test_results` |
| Gate 2 | `gate2_response` |
| Root Cause Agent | `root_causes`, `recommendations` |
| Gate 3 | `gate3_response` |
| PR Agent | `pr_url`, `pr_number` |

## Configuration

Create `.claude/ci-automation.yaml` (or use `.claude/config.yaml` as fallback):

```yaml
upstream_branch: main
build_command: dotnet build
test_command: dotnet test
warn_patterns:
  - "warning CS\\d+"
  - "WARN:"
allow_warnings: false
auto_fix_enabled: true
pr_template_path: .github/PULL_REQUEST_TEMPLATE.md
repo_root: .
```

The plugin auto-detects your project stack (.NET/Python/Node) and prompts to save suggested commands if config is missing.

## Dependencies

This plugin depends on:

- **git** (≥ 2.20) — For version control operations
- **gh CLI** (≥ 2.0) — For GitHub PR creation (optional, only needed for `--yolo` or manual PR)

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `VALIDATION.DIRTY_REPO` | Error | Commit or stash changes |
| `VALIDATION.CONFIG_MISSING` | Warning | Auto-detect and prompt |
| `PULL.MERGE_CONFLICT` | Warning | Auto-resolve or escalate |
| `BUILD.COMPILE_FAILED` | Warning | Route to fix agent |
| `BUILD.WARNINGS_EXCEEDED` | Warning | Fix or use `--allow-warnings` |
| `TEST.FAILED` | Warning | Route to fix agent |
| `FIX.NOT_STRAIGHTFORWARD` | Error | Escalate to root-cause |
| `PR.NO_CHANGES` | Info | Skip PR creation |
| `PR.PUSH_FAILED` | Error | Auto-retry (3x) |

## Safety Features

- **Conservative by default**: Auto-fix only; stops before commit/PR unless clean and confirmed
- **`--yolo` mode**: Enables auto-commit/push/PR after gates pass
- **No force-push**: Respects protected branches and git hooks
- **Warning gates**: Warnings block PR unless `--allow-warnings` or config override
- **Explicit confirmation**: PRs to main/master require confirmation unless `--dest main` provided
- **Audit logs**: All agent invocations logged to `.claude/state/logs/ci-automation/`

## Related

- [sc-git-worktree](/plugins/sc-git-worktree) — Worktree management (complementary)
- [sc-github-issue](/plugins/sc-github-issue) — Issue lifecycle management (complementary)
