# sc-delay-tasks Use Cases

## Introduction

The `sc-delay-tasks` package provides powerful tools for scheduling delayed one-shot waits and bounded polling operations with minimal heartbeat output. This is essential for CI/CD workflows, GitHub Actions integration, API polling, retry logic, and any scenario where you need to pause execution and wait for external conditions to be satisfied.

These use cases demonstrate how `sc-delay-tasks` can streamline your development workflows, automate waiting periods, and reduce context pollution in Claude Code conversations.

---

## Use Case 1: Wait Before Checking GitHub PR Actions

**Scenario/Context:**
You've just pushed a commit to a PR and want to verify that all required checks pass before merging. However, GitHub Actions takes time to initialize and run. Instead of manually checking repeatedly, you want to wait a reasonable time, then ask Claude to verify the PR status.

**Step-by-step Walkthrough:**

1. Push your commit and get the PR URL:
   ```bash
   git push origin feature-x
   # Output: https://github.com/owner/repo/pull/123
   ```

2. Use the sc-delay-tasks `/delay` command with a 2-minute wait:
   ```
   /delay --minutes 2 --action "Check GitHub PR actions and verify all required checks passed"
   ```

3. Expected output:
   ```
   Waiting 2m...
   Waiting 1m 45s...
   ...
   Action: Check GitHub PR actions and verify all required checks passed
   ```

4. Claude receives the action and performs the check

**Expected Outcomes:**
- Automatic 2-minute delay with minimal output
- No manual polling or repeated status checks
- Clear action directive ready for follow-up verification

**Benefits of Using This Approach:**
- Eliminates context pollution from repeated manual checks
- Respects GitHub Actions initialization time
- Provides clear action prompt for systematic PR verification
- Can be composed into larger workflows

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-once agent](agents/delay-once.md)

**Tips and Best Practices:**
- Use `--minutes` for waits over 60 seconds
- The action text should describe what you want to verify afterward
- Start with conservative delays (2-3 minutes) and adjust based on your CI/CD speed
- Works great with GitHub Actions workflows that have known execution times

**Common Pitfalls to Avoid:**
- Don't use extremely long delays; for >30 minutes, consider scheduled jobs instead
- Ensure your action text is specific to avoid confusion in large conversations

---

## Use Case 2: Poll for CI/CD Pipeline Completion

**Scenario/Context:**
Your build pipeline takes 5-15 minutes to complete. Instead of checking manually every minute, you want Claude to poll at regular intervals and report back when complete. The sc-delay-tasks polling feature is perfect for this.

**Step-by-step Walkthrough:**

1. Trigger your build:
   ```bash
   git push origin release/v1.2.0
   # Pipeline starts...
   ```

2. Set up bounded polling that checks every 2 minutes for up to 15 minutes:
   ```
   /delay --every 120 --for 15m --action "Verify pipeline completed successfully and all artifacts are available"
   ```

3. Claude waits and polls. Output includes heartbeats:
   ```
   Polling every 120s for up to 15m...
   Waiting 2m...
   Waiting 4m...
   Waiting 6m...
   ...
   Waiting 14m...
   Action: Verify pipeline completed successfully and all artifacts are available
   ```

4. Claude performs the verification action after polling completes

**Expected Outcomes:**
- Regular polling intervals without constant manual checking
- Heartbeat messages showing progress
- Clean completion with action prompt
- No tool traces or context pollution

**Benefits of Using This Approach:**
- Eliminates manual pipeline monitoring
- Scales to various pipeline durations
- Provides bounded waiting (won't hang indefinitely)
- Keeps conversation context clean

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-poll agent](agents/delay-poll.md)

**Tips and Best Practices:**
- Calculate polling frequency based on expected pipeline duration
  - 5-10 minute pipelines: every 60 seconds
  - 10-30 minute pipelines: every 120 seconds
  - 30+ minute pipelines: every 300 seconds
- Always specify either `--for <duration>` or `--attempts <N>` to prevent infinite polling
- Action text should reference what you want verified once polling completes
- Use in GitHub Actions workflows by invoking Claude Code within the action

**Common Pitfalls to Avoid:**
- Minimum interval is 60 seconds; don't specify `--every 30`
- Forgetting to set a max duration/attempts leads to unbounded polling
- Setting polling interval too short wastes resources

**Variations for Different Scenarios:**

For faster pipelines (5 minutes):
```
/delay --every 60 --for 5m --action "Verify build completed"
```

For slower pipelines (30 minutes):
```
/delay --every 300 --for 30m --action "Verify deployment finished"
```

Using attempts instead of duration:
```
/delay --every 120 --attempts 10 --action "Check if service is healthy"
```

---

## Use Case 3: Scheduled Health Checks for Services

**Scenario/Context:**
You maintain a microservice that sometimes needs a few minutes to stabilize after deployment. You want Claude to wait before running comprehensive health checks, ensuring the service has time to initialize.

**Step-by-step Walkthrough:**

1. Deploy your service:
   ```bash
   kubectl apply -f deployment.yaml
   # Service pods starting...
   ```

2. Schedule a health check after waiting for stabilization:
   ```
   /delay --minutes 3 --action "Run comprehensive health checks on all service endpoints"
   ```

3. After 3 minutes, Claude receives action and runs checks:
   - Verify all pods are running
   - Check service readiness endpoints
   - Validate database connections
   - Test critical API endpoints

**Expected Outcomes:**
- 3-minute wait period with minimal output
- Action trigger for comprehensive health checks
- High confidence that service is ready

**Benefits of Using This Approach:**
- Prevents false negatives from premature health checks
- Reduces flaky test results
- Automates the waiting period completely
- Integrates seamlessly with deployment workflows

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-once agent](agents/delay-once.md)

**Tips and Best Practices:**
- Determine stabilization time from your service documentation or empirical observation
- Health checks after delay are more reliable than immediate checks
- Combine with CI/CD webhooks to automate completely
- Log the delay action for troubleshooting

**Common Pitfalls to Avoid:**
- Guessing stabilization time; measure and document it
- Running checks before the delay completes (defeats the purpose)
- Not accounting for external dependencies' startup times (databases, caches)

---

## Use Case 4: Retry Logic with Exponential Backoff

**Scenario/Context:**
You need to retry a flaky operation (e.g., API call, deployment step) but don't want to hammer the service. Using multiple delay commands in sequence, you can implement exponential backoff.

**Step-by-step Walkthrough:**

**Attempt 1 - Immediate:**
```bash
curl https://api.example.com/deploy --max-time 30
# Request times out
```

**Attempt 2 - After 30 seconds:**
```
/delay --seconds 30 --action "Retry deployment endpoint"
```

Claude retries, which fails again.

**Attempt 3 - After 2 minutes:**
```
/delay --minutes 2 --action "Retry deployment endpoint again with longer timeout"
```

Claude retries with increased timeout.

**Attempt 4 - After 5 minutes:**
```
/delay --minutes 5 --action "Final retry of deployment endpoint"
```

**Expected Outcomes:**
- Exponential backoff timing: 30s, 2m, 5m (with longer timeouts)
- Service has time to recover between attempts
- Failure after multiple attempts signals a real issue
- Manual steps are minimized

**Benefits of Using This Approach:**
- Avoids overwhelming services with repeated requests
- Implements standard retry pattern without complex code
- Provides human checkpoints between retries
- Clear audit trail of all attempts

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-once agent](agents/delay-once.md)

**Tips and Best Practices:**
- Start with 30 seconds for first retry
- Double the wait time for each subsequent attempt
- Cap total retry time to prevent indefinite loops
- Log results after each attempt for debugging

**Common Pitfalls to Avoid:**
- Retrying immediately (first attempt should succeed most of the time)
- Not increasing wait time between retries (defeats backoff purpose)
- Retrying operations that can't possibly succeed (check preconditions first)

**Variations for Different Scenarios:**

Quick retry for network hiccups:
```
/delay --seconds 10 --action "Retry API call"
```

Aggressive backoff for deployment:
```
/delay --seconds 30 --action "First retry"
# If fails:
/delay --minutes 1 --action "Second retry with debug info"
# If fails:
/delay --minutes 3 --action "Final retry with manual intervention"
```

---

## Use Case 5: API Polling with Bounded Waits

**Scenario/Context:**
You're waiting for an async API job to complete (e.g., file processing, model training, report generation). The job is typically done in 5-10 minutes, but you don't know exactly when. Polling with a timeout ensures you don't wait indefinitely.

**Step-by-step Walkthrough:**

1. Submit async job to API:
   ```bash
   curl -X POST https://api.example.com/jobs \
     -d '{"type":"process_video","file":"input.mp4"}' \
     -o job-id.json
   # Returns: {"job_id": "job_12345", "status": "pending"}
   ```

2. Poll for completion with 10-minute timeout:
   ```
   /delay --every 60 --for 10m --action "Check job status and download results if complete"
   ```

3. Polling progression:
   ```
   Polling every 60s for up to 10m...
   Waiting 1m...  (Claude checks: job still processing)
   Waiting 2m...  (Claude checks: job still processing)
   Waiting 3m...  (Claude checks: job still processing)
   Waiting 4m...  (Claude checks: job still processing)
   Waiting 5m...  (Claude checks: job completed!)
   Action: Check job status and download results if complete
   ```

4. Claude validates completion and downloads results

**Expected Outcomes:**
- Regular polling at 60-second intervals
- Early return if job completes before timeout
- Clear signal when action should be taken
- Bounded wait prevents infinite polling

**Benefits of Using This Approach:**
- Automated polling without manual intervention
- Clean, predictable behavior
- Works for any async API pattern
- No context pollution from repeated status checks

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-poll agent](agents/delay-poll.md)

**Tips and Best Practices:**
- Choose polling interval based on typical job duration
  - Short jobs (1-5m): poll every 30-60 seconds
  - Medium jobs (5-20m): poll every 120 seconds
  - Long jobs (20+ min): poll every 300-600 seconds
- Set timeout 20-30% longer than typical job duration
- Include job context (job ID, type) in action text
- Document typical job durations in your code

**Common Pitfalls to Avoid:**
- Polling too frequently (unnecessary resource usage)
- Polling too infrequently (missing completion signals)
- Not accounting for occasional slow jobs (set generous timeout)
- Forgetting to parse job status correctly

---

## Use Case 6: GitHub Actions Integration

**Scenario/Context:**
You want to automate a workflow within GitHub Actions that involves waiting for external systems to be ready. You can invoke Claude Code within a GitHub Actions workflow to use sc-delay-tasks.

**Step-by-step Walkthrough:**

**GitHub Actions Workflow (.github/workflows/deploy-and-verify.yml):**
```yaml
name: Deploy and Verify
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy service
        run: |
          kubectl apply -f deployment.yaml
          echo "Deployment initiated, waiting for service stabilization..."

      - name: Wait and verify service health
        run: |
          npx claude-code --exec-mode sync <<'CLAUDE_SCRIPT'
          /delay --minutes 2 --action "Verify all service instances are healthy and responding to requests"

          # Claude will:
          # 1. Wait 2 minutes
          # 2. Check pod status
          # 3. Verify service endpoints
          # 4. Report health status
          CLAUDE_SCRIPT

      - name: Run integration tests
        run: npm run test:integration
```

**Step-by-step Workflow:**
1. GitHub Actions pushes code and starts workflow
2. Service deployment initiated
3. Claude Code executed within workflow (waits 2 minutes via /delay)
4. After delay, Claude verifies service health
5. If healthy, integration tests proceed
6. Workflow completes successfully or fails with clear error

**Expected Outcomes:**
- Automated waiting within GitHub Actions workflow
- No manual intervention needed
- Service is guaranteed to be ready before integration tests
- Clear audit trail in workflow logs

**Benefits of Using This Approach:**
- Fully automated deployment verification
- No flaky tests from premature checks
- Clear, human-readable workflow definition
- Integrates with existing CI/CD pipeline

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-once agent](agents/delay-once.md)

**Tips and Best Practices:**
- Use `--minutes` for typical waits in CI/CD (usually 1-5 minutes)
- Set timeout slightly longer than typical deployment time
- Include descriptive action text for workflow documentation
- Add logging/debugging steps after delay for troubleshooting

**Common Pitfalls to Avoid:**
- Extremely long delays in CI/CD (slows down your release cycle)
- Not accounting for different environment initialization times (dev vs. prod)
- Forgetting to fail the workflow if verification fails

**Example: Deployment Pipeline with Multiple Checks**
```yaml
name: Multi-Stage Deployment

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: ./scripts/deploy-staging.sh

      - name: Wait for staging readiness
        run: |
          npx claude-code --exec-mode sync <<'SCRIPT'
          /delay --minutes 1 --action "Verify staging environment is ready"
          SCRIPT

      - name: Run smoke tests
        run: npm run test:smoke

      - name: Deploy to production
        run: ./scripts/deploy-prod.sh

      - name: Wait for production readiness
        run: |
          npx claude-code --exec-mode sync <<'SCRIPT'
          /delay --minutes 2 --action "Verify production environment is fully operational"
          SCRIPT

      - name: Run final verification
        run: ./scripts/verify-production.sh
```

---

## Use Case 7: Development and Testing Scenarios

**Scenario/Context:**
During development, you often need to wait for various conditions: local server startup, database migrations, cache warming, build compilation. Instead of repeatedly checking, use sc-delay-tasks to automate the wait and trigger follow-up actions.

**Step-by-step Walkthrough:**

**Scenario A: Wait for Local Development Server**

1. Start development server (takes ~15 seconds to initialize):
   ```bash
   npm run dev &
   # Server starting on port 3000...
   ```

2. Wait for server readiness:
   ```
   /delay --seconds 20 --action "Test development server endpoints and verify hot-reload works"
   ```

3. Claude tests endpoints and verifies hot-reload capability

**Scenario B: Bounded Testing After Code Generation**

1. Generate code using AI tool:
   ```bash
   ai generate-component --name Button
   # Generated: src/components/Button.tsx
   ```

2. Wait for linter/type checker:
   ```
   /delay --seconds 30 --action "Verify generated component compiles without errors and passes all linter checks"
   ```

3. Claude verifies code quality and compilation

**Scenario C: Database Migration Polling**

```bash
npm run migrate:latest &
# Migrations starting...
```

Then:
```
/delay --every 30 --for 5m --action "Verify all database migrations completed successfully and check data integrity"
```

**Expected Outcomes:**
- Development process is automated and reproducible
- No manual checking required
- Clear action prompts guide next steps
- Testing happens at the right moment

**Benefits of Using This Approach:**
- Streamlines development workflow
- Reduces manual intervention
- Makes onboarding easier (new devs follow same patterns)
- Improves test reliability

**Related Documentation:**
- [/delay command reference](commands/delay.md)
- [delay-once and delay-poll agents](agents/)

**Tips and Best Practices:**
- Use short delays for local development (10-30 seconds)
- Timing should match your typical initialization time
- Pair with clear action text describing what to verify
- Document expected timing in your development guide

**Common Pitfalls to Avoid:**
- Using exact timing that varies by machine (be generous with delays)
- Not accounting for first run vs. subsequent runs
- Delays that are shorter than actual initialization time

---

## Common Patterns

### Pattern 1: Simple One-Shot Wait
```
/delay --minutes 2 --action "Verify deployment successful"
```

### Pattern 2: Bounded Polling
```
/delay --every 120 --for 15m --action "Check if job completed"
```

### Pattern 3: Attempts-Based Polling
```
/delay --every 60 --attempts 10 --action "Verify service is responding"
```

### Pattern 4: Short Wait with Seconds
```
/delay --seconds 30 --action "Retry failed operation"
```

### Pattern 5: Until a Specific Time
```
/delay --until 14:30 --action "Check build pipeline status"
```

---

## Integration Examples

### With GitHub Actions
```yaml
- name: Deploy and Wait
  run: |
    ./scripts/deploy.sh
    npx claude-code --exec-mode sync <<'SCRIPT'
    /delay --minutes 2 --action "Verify deployment health"
    SCRIPT
```

### With Make/Task Files
```makefile
deploy-and-verify:
	@./scripts/deploy.sh
	@npx claude-code --exec-mode sync '/delay --minutes 3 --action "Run smoke tests"'
	@npm run test:smoke
```

### With Shell Scripts
```bash
#!/usr/bin/env bash
set -euo pipefail

# Start process
./start-service.sh

# Wait and verify
npx claude-code --exec-mode sync '/delay --minutes 1 --action "Verify service endpoints"'

# Run tests
npm run test:integration
```

---

## Team Workflows

### Distributed Team Coordination
When team members work across time zones and need to coordinate deployments:

1. Team lead deploys to staging
2. Team lead uses sc-delay-tasks to wait
3. Other team members get automated notification when staging is ready
4. All can verify simultaneously without repeated status checks

### Code Review Checkpoints
```
/delay --minutes 5 --action "Verify CI checks passed and gather feedback from reviewers"
```

Ensures CI has time to complete before expecting review feedback.

### Release Coordination
```
/delay --every 120 --for 20m --action "Verify all release artifacts are published and checksums verified"
```

Polls for release completion across multiple services/platforms.

---

## Troubleshooting

### Scenario: Delay seems shorter than specified
- Claude may already have results cached; check actual elapsed time
- Verify the --minutes or --seconds value is correct
- Check if stop-on-success might have triggered early

### Scenario: Polling never triggers action
- Verify polling duration (--for or --attempts) is sufficient
- Check that interval (--every) is reasonable
- Ensure polling is running by looking for "Waiting X..." messages

### Scenario: Action text is confusing
- Make action text specific and actionable
- Include what to verify or what to do next
- Avoid ambiguous terms; be precise

### Scenario: Polling interval is too aggressive
- Increase --every interval (minimum 60 seconds)
- Check your polling frequency against system load
- Consider impact on external services being polled

---

## Getting Started

### Minimum Setup
```bash
# Install sc-delay-tasks globally
python3 tools/sc-install.py install sc-delay-tasks --dest /Users/<you>/Documents/.claude

# Use /delay command anywhere
/delay --minutes 1 --action "Do something"
```

### First Use
1. Start with simple one-shot delays: `/delay --minutes 2 --action "Verify done"`
2. Test with short durations to confirm behavior
3. Add to your workflows once comfortable
4. Explore polling patterns for longer waits

### Common Starting Patterns
- **First deployment**: `/delay --minutes 2 --action "Verify service deployed"`
- **API polling**: `/delay --every 120 --for 10m --action "Check if job complete"`
- **Local dev**: `/delay --seconds 30 --action "Test server"`
- **CI/CD**: `/delay --minutes 1 --action "Run tests"`

---

## See Also

- [sc-delay-tasks README](README.md)
- [/delay Command Reference](commands/delay.md)
- [Synaptic Canvas Contributing Guide](/CONTRIBUTING.md)
- [Synaptic Canvas Repository](https://github.com/randlee/synaptic-canvas)

---

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Maintainer:** Synaptic Canvas Contributors
