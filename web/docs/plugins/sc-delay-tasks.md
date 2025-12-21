<script setup>
import { ref } from 'vue'

// Define the workflow diagram data
const nodes = ref([
  {
    id: 'command',
    label: '/sc-delay',
    subtitle: '--minutes 2 --action "..."',
    type: 'entry',
    details: {
      description: 'Entry point for delay operations. Parses user flags and determines whether to execute one-shot delay or bounded polling.',
      input: {
        flags: {
          '--minutes': 'number - One-shot delay in minutes',
          '--seconds': 'number - One-shot delay in seconds (min 10s)',
          '--until': 'string - Target time (HH:MM or ISO)',
          '--every': 'number - Poll interval in seconds (min 60s)',
          '--for': 'string - Max duration for polling (e.g., 10m)',
          '--attempts': 'number - Max attempts for polling',
          '--action': 'string - Action text to emit on completion',
          '--stop-on-success': 'boolean - Enable early stop on success',
          '--prompt': 'string - Prompt file name in .prompts/',
          '--prompt-text': 'string - Text to generate prompt file'
        }
      },
      output: {
        operation: 'once | poll | poll-pr-check',
        params: '{ duration?, interval?, action?, prompt? }'
      },
      context: ['flags', 'operation', 'params']
    }
  },
  {
    id: 'validate',
    label: 'Validation',
    subtitle: 'check params',
    type: 'agent',
    details: {
      description: 'Validates delay parameters before execution. Checks duration bounds (10s min, 12h max), interval minimums (60s for polling), and ensures required parameters are present.',
      input: {
        operation: 'once | poll | poll-pr-check',
        duration: 'number (seconds)',
        interval: 'number (seconds)',
        attempts: 'number'
      },
      output: {
        success: true,
        data: {
          validated_params: '{ duration, interval, action }',
          mode: 'once | poll'
        }
      },
      context: ['validated_params'],
      errorCodes: [
        { code: 'validation.duration', recoverable: true, action: 'Adjust duration to 10s-12h range' },
        { code: 'validation.interval', recoverable: true, action: 'Set interval >= 60s' },
        { code: 'validation.missing', recoverable: true, action: 'Provide required parameters' }
      ]
    }
  },
  {
    id: 'route',
    label: 'Route Operation',
    subtitle: 'once/poll/pr-check',
    type: 'gate',
    details: {
      description: 'Routes to appropriate agent based on operation mode. No user interaction, but different code paths for different delay types.',
      gatePrompt: {
        type: 'routing_decision',
        gate_id: 'operation_routing',
        message: 'Determine which delay agent to invoke',
        context: {
          operation: 'once | poll | poll-pr-check',
          params: '{ validated parameters }'
        },
        options: {
          once: 'Invoke delay-once agent',
          poll: 'Invoke delay-poll agent',
          pr_check: 'Invoke git-pr-check-delay agent'
        }
      },
      gateResponse: { route: 'once | poll | pr-check' },
      skipCondition: 'Never skipped',
      context: ['route']
    }
  },
  {
    id: 'delay-once',
    label: 'Delay Once',
    subtitle: 'sc-delay-once',
    type: 'agent',
    details: {
      description: 'Executes a single wait period with minimal heartbeats. Calls delay-run.py helper script and waits for completion. For short waits (< 60s), prints single waiting line. For longer waits, emits periodic heartbeats.',
      input: {
        seconds: 'number (or minutes or until)',
        action: 'string'
      },
      output: {
        success: true,
        data: {
          mode: 'once',
          duration_seconds: 120,
          action: 'verify gh pr actions passed'
        }
      },
      context: ['duration', 'action'],
      errorCodes: [
        { code: 'validation.duration', recoverable: true, action: 'Use 10s-12h range' },
        { code: 'script.execution', recoverable: false, action: 'Check Python installation' }
      ]
    }
  },
  {
    id: 'delay-poll',
    label: 'Delay Poll',
    subtitle: 'sc-delay-poll',
    type: 'agent',
    details: {
      description: 'Performs bounded polling with regular heartbeats. Sleeps on interval, emits heartbeat each interval. For stop-on-success mode, evaluates prompt after each wait. Stops when max duration/attempts reached or success condition met.',
      input: {
        every: 'number (seconds, min 60s)',
        for: 'string (duration) OR attempts: number',
        action: 'string',
        stop_on_success: 'boolean (optional)',
        prompt: 'string (prompt file name)'
      },
      output: {
        success: true,
        data: {
          mode: 'poll',
          interval_seconds: 60,
          total_duration_seconds: 180,
          attempts: 3,
          stopped_early: false,
          action: 'verify gh pr actions passed',
          message: null
        }
      },
      context: ['interval', 'attempts', 'stopped_early', 'action'],
      errorCodes: [
        { code: 'validation.interval', recoverable: true, action: 'Set interval >= 60s' },
        { code: 'validation.bounds', recoverable: true, action: 'Provide --for or --attempts' },
        { code: 'prompt.not_found', recoverable: true, action: 'Create prompt file in .prompts/' }
      ]
    }
  },
  {
    id: 'pr-check',
    label: 'PR Check Delay',
    subtitle: 'sc-git-pr-check-delay',
    type: 'agent',
    details: {
      description: 'Specialized polling agent for GitHub PR required checks. Polls PR status using gh CLI, checking if all required checks pass. Stops on success, failure, or timeout. Uses delay-run.py for heartbeat waits between checks.',
      input: {
        prUrl: 'string (or prId)',
        initialWaitMinutes: 'number (default: 5)',
        pollIntervalMinutes: 'number (default: 2, min: 1)',
        timeoutMinutes: 'number (default: 45, max: 720)',
        requiredChecks: 'array[string] (optional)'
      },
      output: {
        success: true,
        data: {
          prUrl: 'https://github.com/owner/repo/pull/123',
          status: 'succeeded|failed|timeout',
          elapsedMinutes: 12,
          checks: [
            { name: 'unit-tests', status: 'succeeded', url: '...' },
            { name: 'lint', status: 'succeeded', url: '...' }
          ]
        }
      },
      context: ['pr_url', 'status', 'elapsed', 'checks'],
      errorCodes: [
        { code: 'MISSING_PR', recoverable: true, action: 'Provide prUrl or prId' },
        { code: 'CHECK_FETCH_FAILED', recoverable: false, action: 'Verify gh auth and PR URL' },
        { code: 'CI_TIMEOUT', recoverable: false, action: 'Increase timeout or check manually' },
        { code: 'CI_FAILED', recoverable: false, action: 'Review failed checks' }
      ]
    }
  },
  {
    id: 'success-check',
    label: 'Success Check',
    subtitle: 'evaluate prompt',
    type: 'gate',
    details: {
      description: 'Optional gate for stop-on-success polling. Evaluates custom prompt that returns JSON with success/cancelled/message. Only active when --stop-on-success flag is used.',
      gatePrompt: {
        type: 'condition_check',
        gate_id: 'success_evaluation',
        message: 'Check if success condition is met',
        context: {
          prompt_file: '.prompts/<name>.md',
          attempt: 'number',
          elapsed: 'number (seconds)'
        },
        options: {
          continue: 'Continue polling (success: false)',
          stop_success: 'Stop polling (success: true)',
          stop_cancel: 'Cancel polling (cancelled: true)'
        }
      },
      gateResponse: { success: false, cancelled: false, message: 'string' },
      skipCondition: '--stop-on-success not specified',
      context: ['success_result']
    }
  },
  {
    id: 'complete-once',
    label: 'Complete',
    subtitle: 'delay finished',
    type: 'success',
    details: {
      description: 'One-shot delay completed successfully. Action text emitted for caller to perform follow-up operations.',
      context: ['final_status', 'action', 'duration']
    }
  },
  {
    id: 'complete-poll',
    label: 'Complete',
    subtitle: 'polling finished',
    type: 'success',
    details: {
      description: 'Polling delay completed successfully. Either reached max attempts/duration or success condition was met. Action text emitted for follow-up operations.',
      context: ['final_status', 'action', 'attempts', 'stopped_early']
    }
  },
  {
    id: 'complete-pr',
    label: 'PR Checks Pass',
    subtitle: 'all checks succeeded',
    type: 'success',
    details: {
      description: 'All required PR checks passed successfully. PR is ready for merge (though this agent does not perform the merge).',
      context: ['pr_url', 'checks', 'elapsed']
    }
  },
  {
    id: 'validation-error',
    label: 'Validation Error',
    subtitle: 'invalid params',
    type: 'error',
    details: {
      description: 'Parameter validation failed. Duration out of bounds, interval too short, or required parameters missing. No wait was attempted.',
      errorCodes: [
        { code: 'validation.duration', recoverable: true, action: 'Use 10s minimum, 12h maximum' },
        { code: 'validation.interval', recoverable: true, action: 'Use 60s minimum for polling' },
        { code: 'validation.missing', recoverable: true, action: 'Provide required parameters' }
      ]
    }
  },
  {
    id: 'pr-timeout',
    label: 'PR Timeout',
    subtitle: 'checks pending',
    type: 'error',
    details: {
      description: 'PR checks did not complete within timeout period. Some checks may still be pending or running.',
      errorCodes: [
        { code: 'CI_TIMEOUT', recoverable: false, action: 'Increase timeout or check PR manually' }
      ]
    }
  },
  {
    id: 'pr-failed',
    label: 'PR Checks Failed',
    subtitle: 'checks failed',
    type: 'error',
    details: {
      description: 'One or more required PR checks failed. PR cannot be merged until issues are fixed.',
      errorCodes: [
        { code: 'CI_FAILED', recoverable: false, action: 'Review failed checks and fix issues' }
      ]
    }
  },
  {
    id: 'execution-error',
    label: 'Execution Error',
    subtitle: 'script failed',
    type: 'error',
    details: {
      description: 'Delay script execution failed. Python not available, script not found, or runtime error occurred.',
      errorCodes: [
        { code: 'script.not_found', recoverable: false, action: 'Reinstall sc-delay-tasks package' },
        { code: 'script.execution', recoverable: false, action: 'Check Python 3 installation' },
        { code: 'prompt.not_found', recoverable: true, action: 'Create prompt file in .prompts/' }
      ]
    }
  }
])

const edges = ref([
  { from: 'command', to: 'validate', label: 'parse flags' },
  { from: 'validate', to: 'route', label: 'params valid' },
  { from: 'validate', to: 'validation-error', label: 'invalid' },
  { from: 'route', to: 'delay-once', label: 'once mode' },
  { from: 'route', to: 'delay-poll', label: 'poll mode' },
  { from: 'route', to: 'pr-check', label: 'pr-check mode' },
  { from: 'delay-once', to: 'complete-once', label: 'wait done' },
  { from: 'delay-once', to: 'execution-error', label: 'script error' },
  { from: 'delay-poll', to: 'success-check', label: 'stop-on-success' },
  { from: 'delay-poll', to: 'complete-poll', label: 'max reached' },
  { from: 'delay-poll', to: 'execution-error', label: 'script error' },
  { from: 'success-check', to: 'delay-poll', label: 'continue' },
  { from: 'success-check', to: 'complete-poll', label: 'success/cancel' },
  { from: 'pr-check', to: 'complete-pr', label: 'checks pass' },
  { from: 'pr-check', to: 'pr-timeout', label: 'timeout' },
  { from: 'pr-check', to: 'pr-failed', label: 'checks fail' },
  { from: 'pr-check', to: 'execution-error', label: 'fetch error' }
])
</script>

# sc-delay-tasks

Schedule delayed one-shot waits or bounded polling with minimal heartbeats.

<PluginFlowVisualizer
  plugin-name="sc-delay-tasks"
  :nodes="nodes"
  :edges="edges"
/>

## Overview

The `sc-delay-tasks` plugin provides workflow orchestration for scheduling delays and polling operations. It supports:

- **One-shot delays** - Wait for a specified duration then emit an action
- **Bounded polling** - Repeat delays with heartbeats until max duration/attempts reached
- **Stop-on-success polling** - Poll with early termination when custom condition is met
- **PR check monitoring** - Specialized polling for GitHub PR required checks

All delay operations emit minimal heartbeat output to avoid context pollution, making them ideal for CI/CD workflows, API polling, and scheduled verifications.

## Quick Start

```bash
# Wait 2 minutes then emit action
/sc-delay --minutes 2 --action "Verify deployment health"

# Poll every 60s for up to 10 minutes
/sc-delay --every 60 --for 10m --action "Check job status"

# Poll with max 10 attempts
/sc-delay --every 120 --attempts 10 --action "Verify service ready"

# Wait until specific time
/sc-delay --until 14:30 --action "Check build pipeline"

# Short wait (seconds)
/sc-delay --seconds 30 --action "Retry operation"
```

## Command Reference

| Flag | Type | Description |
|------|------|-------------|
| `--minutes` | number | One-shot delay in minutes |
| `--seconds` | number | One-shot delay in seconds (min 10s) |
| `--until` | string | One-shot until target time (HH:MM or ISO) |
| `--every` | number | Poll interval in seconds (min 60s) |
| `--for` | string | Max duration for polling (e.g., 10m, 600s) |
| `--attempts` | number | Max attempts for polling |
| `--action` | string | Action text to emit on completion |
| `--stop-on-success` | boolean | Enable early stop when condition met |
| `--prompt` | string | Prompt file name in `.prompts/` for success check |
| `--prompt-text` | string | Text to generate prompt file |
| `--help` | boolean | Show options concisely |

## Workflow States

### Entry Point

The command parser determines the operation mode:

- `--minutes` or `--seconds` or `--until` → One-shot delay (delay-once agent)
- `--every` with `--for` or `--attempts` → Bounded polling (delay-poll agent)
- PR-specific parameters → PR check polling (git-pr-check-delay agent)

### Operation Modes

**One-Shot Mode** - Single wait period, then emit action:
- Duration: 10 seconds to 12 hours
- Heartbeats for waits > 60s
- Single line output for waits < 60s

**Polling Mode** - Repeated delays with bounded execution:
- Interval: minimum 60 seconds
- Bounds: must specify `--for` (duration) or `--attempts` (count)
- Heartbeat every interval
- Optional early stop with `--stop-on-success`

**PR Check Mode** - Specialized GitHub PR monitoring:
- Default: 5 minute initial wait, 2 minute poll interval, 45 minute timeout
- Monitors required checks using `gh` CLI
- Stops on success, failure, or timeout
- Returns detailed check status

### User Decision Gates

This plugin has one optional user interaction point:

**Success Check Evaluation** (success-check gate) - Only active with `--stop-on-success`
- Custom prompt evaluates success condition
- Returns JSON: `{ "success": true|false, "cancelled": true|false, "message": "..." }`
- **Continue**: Keep polling (success: false)
- **Stop Success**: Stop polling (success: true)
- **Stop Cancel**: Abort polling (cancelled: true)

The prompt is evaluated after each wait interval. For example, you might check if a CI job completed, an API returned expected status, or a file exists.

> **Note**: The retry loop (success-check → delay-poll) continues until success/cancel or max bounds reached.

### Context Accumulation

As the workflow progresses, context grows:

| Stage | Context Added |
|-------|---------------|
| Command Entry | `flags`, `operation`, `params` |
| Validation | `validated_params` |
| Route Decision | `route` |
| Delay Once Agent | `duration`, `action` |
| Delay Poll Agent | `interval`, `attempts`, `stopped_early`, `action` |
| PR Check Agent | `pr_url`, `status`, `elapsed`, `checks` |
| Success Check | `success_result` |

## Dependencies

This plugin requires:

- **python3** (≥ 3.8) — For delay-run.py helper script
- **bash** — For script execution
- **gh CLI** (≥ 2.0) — Only for git-pr-check-delay agent

No other Synaptic Canvas plugins required. Can be installed globally or locally.

## Error Handling

| Error Code | Severity | Recovery |
|------------|----------|----------|
| `validation.duration` | Error | Adjust to 10s-12h range |
| `validation.interval` | Error | Set interval >= 60s |
| `validation.missing` | Error | Provide required parameters |
| `script.not_found` | Error | Reinstall sc-delay-tasks |
| `script.execution` | Error | Check Python 3 installation |
| `prompt.not_found` | Error | Create prompt file in .prompts/ |
| `MISSING_PR` | Error | Provide prUrl or prId |
| `CHECK_FETCH_FAILED` | Error | Verify gh auth and PR URL |
| `CI_TIMEOUT` | Warning | Increase timeout or check manually |
| `CI_FAILED` | Warning | Review and fix failed checks |

## Use Cases

### CI/CD Integration

Wait for deployments to stabilize before running tests:

```bash
# Deploy service
kubectl apply -f deployment.yaml

# Wait for stabilization
/sc-delay --minutes 2 --action "Run health checks on all endpoints"

# Claude performs health checks after delay
```

### API Polling

Poll for async job completion:

```bash
# Submit job to API
curl -X POST https://api.example.com/jobs -d '{"type":"process"}' -o job.json

# Poll until complete (max 10 minutes)
/sc-delay --every 60 --for 10m --action "Check job status and download results"
```

### GitHub PR Checks

Monitor PR checks with specialized agent:

```bash
# Push changes and create PR
git push origin feature-branch
gh pr create --title "Feature" --body "Description"

# Wait for checks (initial 5m wait, poll every 2m, timeout 45m)
/sc-delay --pr-url https://github.com/owner/repo/pull/123
```

### Retry with Backoff

Implement exponential backoff for flaky operations:

```bash
# Attempt 1 - immediate
curl https://api.example.com/deploy

# Attempt 2 - after 30s
/sc-delay --seconds 30 --action "Retry deployment"

# Attempt 3 - after 2m
/sc-delay --minutes 2 --action "Final retry with longer timeout"
```

### Development Workflows

Wait for local server startup:

```bash
# Start dev server
npm run dev &

# Wait for initialization
/sc-delay --seconds 20 --action "Test endpoints and verify hot-reload"
```

## Stop-on-Success Pattern

For polling that stops when a condition is met:

```bash
# Create prompt file .prompts/ci-success.md
# Prompt should return JSON: {"success": true|false, "cancelled": true|false, "message": "..."}

/sc-delay --every 120 --for 30m --stop-on-success --prompt ci-success --action "Continue deployment"
```

Or generate prompt from text:

```bash
/sc-delay --every 120 --for 30m --stop-on-success \
  --prompt-text "Check if all pods are running and healthy" \
  --action "Deploy to production"
```

The prompt is evaluated after each interval. Polling stops early when:
- `success: true` - Condition met, proceed with action
- `cancelled: true` - User/system cancelled, abort polling

## Agents

The plugin includes three specialized agents:

### sc-delay-once
Single wait with minimal output. Invoked for `--minutes`, `--seconds`, or `--until`.

**Key behaviors:**
- Validates duration bounds (10s-12h)
- Emits heartbeats for waits > 60s
- Single line for waits < 60s
- Returns action text only

### sc-delay-poll
Bounded polling with regular heartbeats. Invoked for `--every` with `--for` or `--attempts`.

**Key behaviors:**
- Validates interval >= 60s
- Requires max duration or attempts
- Optional stop-on-success with custom prompt
- Returns attempts, duration, stopped_early flag

### sc-git-pr-check-delay
Specialized PR check monitoring. Invoked for PR-specific parameters.

**Key behaviors:**
- Default: 5m initial wait, 2m interval, 45m timeout
- Fetches PR checks via `gh` CLI
- Stops on success, failure, or timeout
- Returns detailed check status

## Related

- [sc-github-issue](/plugins/sc-github-issue) — GitHub issue management (uses delays for checks)
- [sc-ci-automation](/plugins/sc-ci-automation) — CI integration (complementary)

## Installation

```bash
# Global install (available in all repos)
python3 tools/sc-install.py install sc-delay-tasks --dest ~/Documents/.claude

# Local install (repo-specific)
python3 tools/sc-install.py install sc-delay-tasks --dest ./.claude
```

## Troubleshooting

See [TROUBLESHOOTING.md](https://github.com/randlee/synaptic-canvas/blob/main/packages/sc-delay-tasks/TROUBLESHOOTING.md) for detailed diagnostics.

**Common issues:**
- Command not found → Verify installation path and scope
- Python3 not found → Install Python >= 3.8
- Interval too short → Use >= 60s for polling
- Duration validation → Use 10s-12h range

**Quick diagnostics:**
```bash
# Verify installation
ls -la .claude/commands/sc-delay.md
ls -la .claude/scripts/sc-delay-run.py

# Test script directly
python3 .claude/scripts/sc-delay-run.py --seconds 10 --action "test"

# Check Python version
python3 --version
```
