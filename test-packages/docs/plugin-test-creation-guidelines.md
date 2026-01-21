# Plugin Test Creation Guidelines

Guidelines for creating valid, maintainable test fixtures for Synaptic Canvas plugins.

---

## Overview

Every plugin test fixture must:
1. **Reference a valid plugin** with a markdown file (skill/command/agent)
2. **Install the plugin** via `setup.plugins` (not manual file copying)
3. **Verify installation** before running tests
4. **Generate observable reports** for human debugging

---

## Test Fixture Lifecycle

```
1. RESET      → Revert sc-test-harness to pristine state (remote main)
2. INSTALL    → Install plugin locally via `claude plugin install`
3. VERIFY     → Confirm plugin is installed (fail fast if not)
4. EXECUTE    → Run test #1, test #2, ... test #N
5. CLEANUP    → Remove plugin, restore pristine state
```

---

## Plugin Installation in Test Fixtures

Test fixtures can specify plugins to install in their `fixture.yaml` setup section:

```yaml
setup:
  plugins:
    - sc-startup@synaptic-canvas
    - sc-git-worktree@synaptic-canvas
```

### How Plugin Installation Works

The test harness uses two different approaches for plugin installation depending on the package being tested:

1. **For all packages except sc-manage**: The harness uses `sc-install.py` directly (via subprocess) to install package files into the test project's `.claude/` directory. This ensures packages are available even in isolated test environments.

2. **For sc-manage package**: The harness has Claude invoke `/sc-manage --install <package> --local` as part of the test execution. This is necessary to test sc-manage's own installation functionality.

### Prerequisites

- The synaptic-canvas repo must be available (set `SC_SYNAPTIC_CANVAS_PATH` environment variable or place it as a sibling directory)
- For sc-manage testing: sc-manage must be pre-installed in the test harness via:
  ```bash
  python3 /path/to/synaptic-canvas/tools/sc-install.py install sc-manage --dest /path/to/sc-test-harness/.claude
  ```

### Plugin Specification Format

Plugins are specified as `<package-name>@<marketplace>`:
- `sc-startup@synaptic-canvas` - installs sc-startup from synaptic-canvas
- `sc-manage@synaptic-canvas` - triggers Claude-based installation for testing

---

## Fixture Structure

```
test-packages/fixtures/<plugin-name>/
├── fixture.yaml           # Fixture configuration (REQUIRED)
└── tests/
    ├── test_basic.yaml    # Individual test files
    ├── test_advanced.yaml
    └── ...
```

### fixture.yaml (Required Fields)

```yaml
# REQUIRED: Fixture metadata
name: my-plugin
description: Tests for my-plugin skill
package: my-plugin@synaptic-canvas  # MUST be valid marketplace reference

# REQUIRED: Plugin installation
setup:
  plugins:
    - my-plugin@synaptic-canvas  # Use setup.plugins, NOT file copying!
  commands: []  # Optional additional setup

teardown:
  commands: []  # Optional cleanup

tests_dir: tests
```

### test_*.yaml (Required Fields)

```yaml
# REQUIRED: Test identification
test_id: my-plugin-001
test_name: Basic invocation
description: Verify plugin responds correctly

# REQUIRED: Execution configuration
execution:
  prompt: "/my-command --help"  # The prompt to send
  model: haiku                   # Model to use
  tools:                         # Tools to allow
    - Bash
    - Read
  timeout_ms: 60000              # Timeout in milliseconds

# REQUIRED: At least one expectation
expectations:
  - id: exp-001
    description: Should show help output
    type: output_contains
    expected:
      pattern: "(usage|options|help)"
      flags: "i"
```

---

## Validation Rules (Fail Fast)

The test harness will **fail immediately** if:

| Rule | Error |
|------|-------|
| `package` field missing or empty | "Fixture must specify a valid package" |
| Plugin not in marketplace registry | "Plugin not found in marketplace" |
| Plugin has no markdown file | "Plugin must have skill/command/agent definition" |
| `setup.plugins` empty when `package` specified | "setup.plugins must include the package" |
| Plugin installation fails | "Failed to install plugin: <error>" |

---

## Common Mistakes to Avoid

### DON'T: Copy files manually instead of using plugins

```yaml
# WRONG - Don't do this!
setup:
  plugins: []
  commands:
    - cp packages/my-plugin/commands/cmd.md .claude/commands/
```

```yaml
# CORRECT - Use plugin installation
setup:
  plugins:
    - my-plugin@synaptic-canvas
  commands: []
```

### DON'T: Reference non-existent plugins

```yaml
# WRONG - Plugin doesn't exist
package: nonexistent-plugin@synaptic-canvas
setup:
  plugins:
    - nonexistent-plugin@synaptic-canvas
```

### DON'T: Skip the package field

```yaml
# WRONG - Missing package reference
name: my-test
setup:
  plugins:
    - my-plugin@synaptic-canvas
# Missing: package: my-plugin@synaptic-canvas
```

---

## Expectation Types

### output_contains
Checks if Claude's response contains a pattern.

```yaml
expectations:
  - type: output_contains
    expected:
      pattern: "(success|complete|done)"
      # Defaults:
      # - case-insensitive matching
      # - response_filter: assistant_all
      # - exclude_prompt: true
      #
      # Optional overrides:
      # flags: "im"
      # case_sensitive: true
      # response_filter: assistant_last
      # exclude_prompt: false
```

### allow_warnings (restricted)
Warnings are failures by default. To suppress warnings you must provide
explicit, documented approval:

```yaml
allow_warnings: true
allow_warnings_reason: "Approved by user <name/date>: <reason>"
```

### tool_call
Checks if a specific tool was called.

```yaml
expectations:
  - type: tool_call
    expected:
      tool: Bash
      pattern: "git status"
```

### hook_event
Checks for specific hook events (SubagentStart, etc.).

```yaml
expectations:
  - type: hook_event
    expected:
      event: SubagentStart
      agent_type: "Explore"
```

---

## Report Observability

Every test generates HTML and JSON reports showing:

| Section | Contents |
|---------|----------|
| Setup | Plugins installed, commands run |
| Execution | Prompt sent, model used |
| Timeline | Tool calls, responses, events |
| Expectations | Pass/fail with actual vs expected |
| Claude Session Log | Raw stdout/stderr from Claude CLI |
| Reproduce | Commands to reproduce the test |

**Reports location:** `test-packages/reports/<fixture-name>.html`

---

## Running Tests

```bash
# Run all fixture tests
pytest test-packages/fixtures/ -v --open-on-fail

# Run specific plugin tests
pytest test-packages/fixtures/my-plugin/ -v --open-report

# Always open report (for development)
pytest test-packages/fixtures/my-plugin/ -v --open-report
```

---

## Checklist Before Committing

- [ ] `package` field references valid marketplace plugin
- [ ] `setup.plugins` includes the package
- [ ] Plugin has markdown file (skill/command/agent)
- [ ] At least one expectation defined
- [ ] Test runs successfully locally
- [ ] HTML report shows expected behavior

---

## Log Warning Behavior

### Default: Warnings Cause Test Failure

By default, any warning or error in the test logs will cause the test to fail. This is intentional to ensure silent failures are caught immediately.

```yaml
# This test will FAIL if ANY warnings appear in logs
test_id: my-plugin-001
test_name: Basic invocation
execution:
  prompt: "/my-command --help"
  model: haiku
```

**Why?** Silent failures are unacceptable. Warnings often indicate:
- Deprecated API usage that will break in future versions
- Configuration issues that cause subtle bugs
- Resource leaks or performance problems
- Security concerns

### Overriding Warning Behavior (REQUIRES APPROVAL)

The `allow_warnings: true` option can override this behavior, but it **requires explicit user approval** before merging.

```yaml
# REQUIRES EXPLICIT USER APPROVAL
# This override MUST be documented and approved before merging
test_id: deprecated-api-test-001
test_name: Test deprecated API still works

# APPROVAL REQUIRED - see documentation below
allow_warnings: true

execution:
  prompt: "/deprecated-command"
  model: haiku
```

### When Override is Appropriate

| Scenario | Appropriate? | Notes |
|----------|--------------|-------|
| Testing deprecated API warning behavior | Yes | Document in comments |
| Testing error handling paths | Yes | Explicitly expecting warnings |
| Third-party library warnings | Maybe | Consider if fixable |
| Production code | **NEVER** | Fix the warning instead |
| Convenience/laziness | **NEVER** | Fix the warning instead |

### Requesting Override Approval

To use `allow_warnings: true`:

1. **Document the reason** in test YAML comments explaining why warnings are expected
2. **Get explicit user approval** before merging - tag reviewer in PR
3. **Create follow-up issue** if the warning should eventually be fixed
4. **Include approval metadata** in the test file

**Example with proper documentation:**

```yaml
# APPROVED BY: @reviewer-username on 2026-01-18
# REASON: Testing that deprecated API warning message is shown correctly
# FOLLOW-UP: Issue #123 to migrate to new API by 2026-Q2
allow_warnings: true

test_id: deprecated-api-warning-test
test_name: Verify deprecation warning shown
description: Tests that using deprecated API shows proper warning message
```

### Overrides Without Approval Will Be Rejected

- PRs with undocumented `allow_warnings: true` will be blocked
- Reviewers should check for proper approval metadata
- CI may automatically flag unapproved overrides

---

## Related Documentation

| Document | Location |
|----------|----------|
| Test Harness Design Spec | `docs/requirements/test-harness-design-spec.md` |
| sc-test-harness README | `../sc-test-harness/README.md` |
| Environment Isolation | `../sc-test-harness/docs/spike-1-clean-environment-configuration.md` |
| Hook Observability | `../sc-test-harness/docs/spike-2-hook-observability.md` |
| PQA Role Prompt | `pm/PQA.md` |
