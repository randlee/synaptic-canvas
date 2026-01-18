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
      flags: "i"  # Case insensitive
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

## Related Documentation

| Document | Location |
|----------|----------|
| Test Harness Design Spec | `docs/requirements/test-harness-design-spec.md` |
| sc-test-harness README | `../sc-test-harness/README.md` |
| Environment Isolation | `../sc-test-harness/docs/spike-1-clean-environment-configuration.md` |
| Hook Observability | `../sc-test-harness/docs/spike-2-hook-observability.md` |
| PQA Role Prompt | `pm/PQA.md` |
