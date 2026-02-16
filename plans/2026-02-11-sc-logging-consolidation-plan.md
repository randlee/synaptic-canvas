# SC Logging Consolidation Plan

**Created**: 2026-02-11
**Status**: Draft
**Goal**: Migrate all packages to structured Pydantic logging with Jenga templates

---

## Executive Summary

### Problem
- **12+ packages** with inconsistent logging implementations
- **11 duplicated copies** of `sc_shared.py` (agent runner auditing)
- **3 different patterns** (centralized, package-specific, mixed)
- No validation, type safety, or standard schema
- Documentation inconsistencies across 20+ files

### Solution
- **Jenga templates** for self-contained packages:
  - `sc-logging.jenga.py` - Structured logging with Pydantic (✅ created)
  - `sc-shared.jenga.py` - Agent runner functionality (NEW)
- **Base test infrastructure** with reusable validation helpers
- **One sprint per package group** with unit tests
- **Documentation sprint** to update 20+ outdated files

### Success Metrics
- ✅ All packages use Pydantic-validated logging
- ✅ Zero code duplication (templates only)
- ✅ 100% test coverage for logging paths
- ✅ All documentation updated and consistent

---

## Sprint 0: Foundation (Jenga Templates + Base Tests)

**Duration**: 3-5 days
**Deliverables**: Templates, test infrastructure, validation helpers

### Tasks

#### 1. Create `sc-shared.jenga.py` Template
**Status**: ✅ `sc-logging.jenga.py` done, need `sc-shared.jenga.py`

Extract agent runner functionality from duplicated `sc_shared.py` files:
- [ ] Create `templates/sc-shared.jenga.py` with:
  - Agent runner invocation (find agent file, validate, execute)
  - SHA-256 computation
  - Audit logging integration (uses sc-logging template)
  - Error handling patterns
  - Jenga variables: `{{PACKAGE_NAME}}`, `{{AGENT_TYPES}}`, `{{CUSTOM_VALIDATION}}`

- [ ] Document in PLUGIN-STORAGE-CONVENTIONS.md:
  - How to expand sc-shared template
  - Integration with sc-logging
  - Custom validation patterns

**Reference**: Analyze canonical `/packages/shared/scripts/sc_shared.py`

#### 2. Base Test Infrastructure
- [ ] Create `tests/logging/test_base.py`:
  - `LoggingTestCase` base class
  - `assert_log_entry_valid(entry, schema)` - Pydantic validation
  - `assert_log_file_exists(package, event_type)` - File existence
  - `assert_no_secrets_logged(log_dir)` - Security validation
  - `read_log_entries(package, event_type, limit)` - Test helper
  - `mock_hook_stdin(data)` - Hook testing helper

- [ ] Create `tests/logging/schemas.py`:
  - Reusable test schemas
  - Common field validators
  - Schema inheritance patterns

- [ ] Create `tests/logging/fixtures.py`:
  - Temporary log directories
  - Mock hook payloads
  - Sample log entries

#### 3. Pydantic Custom Validators
- [ ] Add to sc-logging.jenga.py template:
  - `@field_validator` for file path existence
  - `@field_validator` for package directory validation
  - `@field_validator` for import path checking
  - `validate_log_directory()` - Ensures .claude/state/logs/<pkg> exists

- [ ] Create `templates/validators.py` (reusable validators):
  ```python
  @field_validator('script_path')
  def validate_script_exists(cls, v):
      if not Path(v).exists():
          raise ValueError(f"Script not found: {v}")
      return v

  @field_validator('package_name')
  def validate_package_dir(cls, v):
      pkg_dir = Path(f"packages/{v}")
      if not pkg_dir.exists():
          raise ValueError(f"Package not found: {v}")
      return v
  ```

- [ ] Add to base tests:
  - Test validators catch missing files
  - Test validators allow valid paths
  - Test error messages are clear

#### 4. Environment Variable Testing & Validation
**Context**: `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT` are only available in hook contexts

- [ ] Comprehensive environment variable testing:
  - Test hooks get variables (✅ partially done in .claude/scripts/tests/)
  - Test frontmatter hooks (agent .md files) - do they get variables?
  - Test Bash tool - does NOT get variables ❌
  - Test background agents - do they get variables?
  - Test named teammates - do they get variables?
  - Document: **WHERE** variables are available

- [ ] Create `tests/test_env_vars.py`:
  ```python
  class TestEnvVarAvailability(unittest.TestCase):
      def test_hook_has_env_vars(self):
          """PreToolUse hooks get CLAUDE_PROJECT_DIR"""
          # Test via mock hook execution

      def test_bash_no_env_vars(self):
          """Bash tool does NOT get CLAUDE_PROJECT_DIR"""
          # Verify variables not in bash context

      def test_frontmatter_hooks(self):
          """Agent frontmatter hooks - verify availability"""
          # Test if frontmatter hooks get variables
  ```

- [ ] Code audit for incorrect usage:
  - [ ] Search for hardcoded `.claude/` paths → should use `$CLAUDE_PROJECT_DIR`
  - [ ] Search for relative paths in hooks → should use env vars
  - [ ] Find scripts assuming variables exist → add fallbacks
  - [ ] Update validate-hook-paths.py to check frontmatter too

- [ ] Update sc-logging template with env var patterns:
  ```python
  import os
  from pathlib import Path

  # Correct pattern: fallback for non-hook contexts
  def get_project_dir() -> Path:
      return Path(os.getenv("CLAUDE_PROJECT_DIR") or os.getcwd())

  def get_plugin_root() -> Path:
      return Path(os.getenv("CLAUDE_PLUGIN_ROOT") or Path(__file__).parent.parent)

  LOGS_DIR = get_project_dir() / ".claude" / "state" / "logs" / PACKAGE_NAME
  ```

#### 5. Documentation
- [ ] Create `templates/README.md`:
  - How Jenga templates work
  - When to use each template
  - Expansion guide with examples

- [ ] Document environment variable availability:
  - Update agent-tool-use-best-practices.md
  - Add section: "Where Environment Variables Work"
  - Table: Hook contexts (✓) vs Bash tool (✗) vs frontmatter (?)
  - Code examples with fallbacks

**Exit Criteria**:
- ✅ Both Jenga templates created and documented
- ✅ Base test infrastructure with 100% coverage
- ✅ Pydantic validators for file paths implemented
- ✅ Environment variable availability tested and documented
- ✅ Example expansion in one package (sc-commit-push-pr)

---

## Sprint 1: Hook Scripts (High Priority)

**Duration**: 2-3 days
**Target**: Centralized hook scripts in `.claude/scripts/`

### Packages
- `.claude/scripts/log-task-input.py` (PreToolUse-Task logging)
- `.claude/scripts/tests/test-hook-env-vars.py` (Environment variable testing)
- Any other hook scripts discovered

### Tasks
- [ ] Migrate `log-task-input.py`:
  - Copy `sc-logging.jenga.py` to `.claude/scripts/sc_logging.py`
  - Expand with PACKAGE_NAME="hooks"
  - Update logging calls
  - Add unit tests using `LoggingTestCase`

- [ ] Migrate `test-hook-env-vars.py`:
  - Update to use structured logging
  - Add tests for log validation

- [ ] Document in `docs/agent-tool-use-best-practices.md`:
  - Hook logging pattern with sc-logging template

**Exit Criteria**:
- ✅ All hook scripts use structured logging
- ✅ Unit tests pass with 100% coverage
- ✅ Documentation updated

---

## Sprint 2: sc-commit-push-pr (Reference Implementation)

**Duration**: 3-4 days
**Target**: `packages/sc-commit-push-pr/`

### Why First?
- Already has structured preflight logging
- Good reference for other packages
- Medium complexity

### Current State (from Agent 2 survey)
- Preflight logging: `.claude/state/logs/sc-commit-push-pr/preflight-{YYYY-MM-DD}.jsonl`
- Entry structure: `{ timestamp, level, message, context }`
- Uses `preflight_utils.py`

### Tasks
- [ ] Copy templates:
  - `sc-logging.jenga.py` → `scripts/sc_logging.py`
  - `sc-shared.jenga.py` → `scripts/sc_shared.py`

- [ ] Expand Jenga variables:
  - PACKAGE_NAME="sc-commit-push-pr"
  - Add preflight-specific fields to LogEntry

- [ ] Migrate existing logging:
  - `scripts/preflight_utils.py` → use `sc_logging`
  - Update all `log_*()` calls

- [ ] Update agent scripts:
  - `scripts/commit_push_agent_start_hook.py`
  - `scripts/create_pr_agent_start_hook.py`
  - Use sc-shared template for agent runner

- [ ] Add unit tests:
  - `tests/test_preflight_logging.py`
  - `tests/test_agent_runner.py`
  - Use `LoggingTestCase` base class

- [ ] Update documentation:
  - `README.md` - Logs section
  - `DESIGN.md` - Logging architecture
  - Agent frontmatter - Log locations

**Exit Criteria**:
- ✅ All logging uses Pydantic validation
- ✅ Unit tests pass with 100% coverage
- ✅ Documentation updated
- ✅ Serves as reference for other packages

---

## Sprint 3-4: sc-codex (Complex Package)

**Duration**: 4-5 days
**Target**: `packages/sc-codex/`

### Why Second?
- Has custom logging: `scripts/ai_cli/logging.py`
- Package-specific directory structure
- Good test case for complex migrations

### Current State
- Log location: `.claude/state/logs/{derived_package_name}/`
- Log files: `ai-cli-{ISO_TIMESTAMP}.json`
- Entry structure: `{ timestamp, pid, ...event }`
- Derives package name from environment

### Tasks
- [ ] Copy templates to `scripts/`
- [ ] Migrate `ai_cli/logging.py` to use sc-logging template
- [ ] Update all codex scripts to use templates
- [ ] Add unit tests for AI CLI logging
- [ ] Update sc-codex documentation

**Exit Criteria**:
- ✅ Custom logging replaced with template
- ✅ Tests pass
- ✅ Docs updated

---

## Sprint 5-7: sc_shared.py Consolidation (11 Packages)

**Duration**: 6-8 days (grouped by 3-4 packages per sprint)
**Target**: All packages with duplicated `sc_shared.py`

### Strategy
Group packages by complexity and migrate 3-4 at a time.

### Sprint 5: Simple Packages
- `sc-delay-tasks`
- `sc-roslyn-diff`
- `sc-repomix-nuget`

### Sprint 6: Medium Packages
- `sc-startup`
- `sc-kanban`
- `sc-manage`

### Sprint 7: Complex Packages
- `sc-ci-automation`
- `sc-github-issue`
- `sc-git-worktree`

### Tasks Per Package
- [ ] Copy both templates (sc-logging + sc-shared)
- [ ] Expand Jenga variables with package-specific values
- [ ] Delete duplicated `sc_shared.py` (use template copy)
- [ ] Migrate any package-specific logging
- [ ] Add unit tests using `LoggingTestCase`
- [ ] Update package documentation (README, DESIGN)

**Exit Criteria Per Sprint**:
- ✅ 3-4 packages migrated
- ✅ All tests pass
- ✅ Docs updated
- ✅ No more sc_shared.py duplicates

---

## Sprint 8: Shared Package (Canonical Source)

**Duration**: 2-3 days
**Target**: `packages/shared/`

### Why Last?
- Canonical source for sc_shared.py
- Other packages now independent (using templates)
- Can refactor or deprecate

### Tasks
- [ ] Migrate `scripts/sc_shared.py` to template-based
- [ ] Document that shared/ is NOT imported (templates used instead)
- [ ] Consider deprecating shared package if only sc_shared.py
- [ ] Update any documentation referencing shared imports

**Exit Criteria**:
- ✅ Shared package uses templates
- ✅ Clear documentation on template vs import strategy

---

## Sprint 9: Documentation Cleanup (Critical)

**Duration**: 3-4 days
**Target**: All 20+ documents mentioning logging

### Documents to Update (from Agent 1 survey)

#### High Priority (Normative)
- [ ] `docs/PLUGIN-STORAGE-CONVENTIONS.md` (✅ updated)
- [ ] `docs/PLUGIN-CONVENTIONS.md`
- [ ] `docs/agent-runner-comprehensive.md`
- [ ] `docs/agent-tool-use-best-practices.md`

#### Design Documents
- [ ] `docs/design/sc-session-start-design.md`
- [ ] `docs/design/commit-push-pr-design.md`
- [ ] `docs/design/skill-review-system.md`

#### Package Documentation
- [ ] All package `README.md` files (12+ packages)
- [ ] All package `DESIGN.md` files
- [ ] All agent frontmatter (update log locations)

#### Plans and Reports
- [ ] `plans/ci-automation-skill-plan.md`
- [ ] `plans/sc-startup-plan.md`
- [ ] All skill review reports mentioning logging

#### Other
- [ ] `docs/DOCUMENTATION-INDEX.md`
- [ ] `pm/ARCH-SKILL.md`
- [ ] `pm/PQA.md`

### Tasks
- [ ] Search and replace outdated patterns:
  - Old: `.claude/state/logs/` (flat)
  - New: `.claude/state/logs/<package>/`
  - Old: Ad-hoc JSON
  - New: Pydantic-validated via sc-logging template

- [ ] Update code examples to use templates
- [ ] Add references to `templates/sc-logging.jenga.py`
- [ ] Remove contradictory information
- [ ] Standardize terminology (JSONL, package-specific, etc.)

- [ ] Create documentation validation:
  - Script to find references to old logging patterns
  - CI check for outdated examples

**Exit Criteria**:
- ✅ All documentation consistent
- ✅ No contradictions between docs
- ✅ All examples use template pattern
- ✅ Validation script added to CI

---

## Sprint 10: Integration Testing & Polish

**Duration**: 2-3 days
**Target**: End-to-end validation

### Tasks
- [ ] Integration tests:
  - Spawn agents, verify logging
  - Hook execution with log validation
  - Multi-package log aggregation

- [ ] Performance testing:
  - Log write performance
  - Pydantic validation overhead
  - File I/O benchmarks

- [ ] Security audit:
  - Scan all logs for secrets
  - Validate no PII logged
  - Test log directory permissions

- [ ] Developer experience:
  - Template expansion workflow
  - Test helper usability
  - Documentation clarity

**Exit Criteria**:
- ✅ All integration tests pass
- ✅ Performance acceptable (< 5ms per log entry)
- ✅ Security audit clean
- ✅ Positive developer feedback

---

## Testing Strategy

### Base Test Class Pattern

```python
# tests/logging/test_base.py
class LoggingTestCase(unittest.TestCase):
    """Base class for all logging tests."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / ".claude" / "state" / "logs"

    def assert_log_entry_valid(self, entry_json: str, schema: Type[BaseModel]):
        """Validate log entry against Pydantic schema."""
        entry = schema.model_validate_json(entry_json)
        self.assertIsNotNone(entry.timestamp)
        self.assertIsNotNone(entry.event)
        self.assertIn(entry.level, ["debug", "info", "warning", "error", "critical"])

    def assert_log_file_exists(self, package: str, event_type: str):
        """Verify log file exists at expected location."""
        log_file = self.log_dir / package / f"{event_type}.jsonl"
        self.assertTrue(log_file.exists())

    def assert_no_secrets_logged(self, log_dir: Path):
        """Security check: ensure no secrets in logs."""
        patterns = [
            r"password\s*[:=]\s*[^\s]+",
            r"token\s*[:=]\s*[^\s]+",
            r"api[_-]?key\s*[:=]\s*[^\s]+",
        ]
        for log_file in log_dir.rglob("*.jsonl"):
            content = log_file.read_text()
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, content, re.IGNORECASE))

    def read_log_entries(self, package: str, event_type: str) -> list:
        """Read and parse log entries."""
        log_file = self.log_dir / package / f"{event_type}.jsonl"
        entries = []
        with log_file.open("r") as f:
            for line in f:
                entries.append(json.loads(line.strip()))
        return entries
```

### Per-Package Test Pattern

```python
# packages/sc-git-worktree/tests/test_logging.py
from tests.logging.test_base import LoggingTestCase
from scripts.sc_logging import LogEntry, log_event

class TestScGitWorktreeLogging(LoggingTestCase):
    def test_worktree_create_logging(self):
        """Test worktree create logs to correct location."""
        log_event(
            event="worktree_create",
            level="info",
            branch="feature-x",
            path="/path/to/worktree"
        )

        self.assert_log_file_exists("sc-git-worktree", "worktree-create")

        entries = self.read_log_entries("sc-git-worktree", "worktree-create")
        self.assertEqual(len(entries), 1)

        self.assert_log_entry_valid(json.dumps(entries[0]), LogEntry)
        self.assertEqual(entries[0]["event"], "worktree_create")
        self.assertEqual(entries[0]["branch"], "feature-x")
```

---

## Migration Checklist (Per Package)

- [ ] Copy `templates/sc-logging.jenga.py` → `scripts/sc_logging.py`
- [ ] Copy `templates/sc-shared.jenga.py` → `scripts/sc_shared.py` (if uses agent runner)
- [ ] Expand Jenga variables (`{{PACKAGE_NAME}}`, etc.)
- [ ] Extend `LogEntry` with package-specific fields
- [ ] Update all logging calls to use `log_event()`
- [ ] Delete old/duplicated logging code
- [ ] Add unit tests using `LoggingTestCase`
- [ ] Update README.md "Logs" section
- [ ] Update DESIGN.md (if exists)
- [ ] Update agent frontmatter with log locations
- [ ] Run security audit (`assert_no_secrets_logged`)
- [ ] Verify logs appear in correct location

---

## Risks & Mitigations

### Risk 1: Breaking Changes
**Impact**: High
**Mitigation**:
- Keep old logging code alongside new during migration
- Feature flag to toggle old/new logging
- Parallel logging during transition period

### Risk 2: Performance Degradation
**Impact**: Medium
**Mitigation**:
- Benchmark Pydantic validation overhead
- Cache schema validators
- Use JSONL append (no file rewrites)

### Risk 3: Developer Adoption
**Impact**: Medium
**Mitigation**:
- Clear documentation with examples
- Template expansion guide
- Reference implementation (sc-commit-push-pr)

### Risk 4: Test Coverage Gaps
**Impact**: Medium
**Mitigation**:
- Mandatory 100% coverage per sprint
- Base test class enforces patterns
- Security audit on every sprint

---

## Success Criteria

### Technical
- ✅ All 12+ packages use Pydantic-validated logging
- ✅ Zero code duplication (only Jenga templates)
- ✅ 100% test coverage for all logging paths
- ✅ Performance < 5ms per log entry
- ✅ Security audit clean (no secrets logged)

### Documentation
- ✅ All 20+ documents updated and consistent
- ✅ No contradictions or outdated examples
- ✅ Template expansion guide clear and tested
- ✅ CI validates documentation examples

### Developer Experience
- ✅ Template expansion takes < 10 minutes per package
- ✅ Base test class reduces boilerplate by 80%
- ✅ Clear error messages from Pydantic validation
- ✅ Logs queryable via standard tools (jq, grep)

---

## Timeline

| Sprint | Duration | Packages | Deliverables |
|--------|----------|----------|--------------|
| 0 | 3-5 days | - | Templates, base tests, docs |
| 1 | 2-3 days | Hook scripts | Structured hook logging |
| 2 | 3-4 days | sc-commit-push-pr | Reference implementation |
| 3-4 | 4-5 days | sc-codex | Complex package migration |
| 5 | 2-3 days | 3 simple packages | sc_shared consolidation |
| 6 | 2-3 days | 3 medium packages | sc_shared consolidation |
| 7 | 2-3 days | 3 complex packages | sc_shared consolidation |
| 8 | 2-3 days | shared package | Canonical source migration |
| 9 | 3-4 days | Documentation | All docs updated |
| 10 | 2-3 days | Integration | End-to-end testing |

**Total Duration**: 28-38 days (~6-8 weeks)

---

## Open Questions

1. Should we maintain backward compatibility with old log formats?
2. Do we need log rotation/archival beyond 14-day TTL?
3. Should base test class be in `tests/` or `templates/`?
4. Do we want CI to block on logging validation failures?
5. Should we add structured logging to *all* packages or only those currently logging?
6. **Environment variables**: Do frontmatter hooks in agent .md files get `CLAUDE_PROJECT_DIR`/`CLAUDE_PLUGIN_ROOT`?
7. **Pydantic validation**: Should file path validators be strict (fail on missing) or lenient (warn only)?
8. Should we create a validator registry for common patterns (paths, packages, imports)?

---

## References

- [PLUGIN-STORAGE-CONVENTIONS.md](../docs/PLUGIN-STORAGE-CONVENTIONS.md) - Logging standard
- [templates/sc-logging.jenga.py](../templates/sc-logging.jenga.py) - Jenga template
- [Agent 1 Report](../docs/PLUGIN-STORAGE-CONVENTIONS.md) - Documentation survey
- [Agent 2 Report](internal) - Implementation survey (12 packages, 3 patterns)

---

**Plan Status**: Ready for review
**Next Steps**: Sprint 0 kickoff - create sc-shared.jenga.py template
