# Testing Plan (Draft)

This document describes the initial testing plan for Synaptic Canvas plugins. The goal is to test deterministically without
publishing to a marketplace or relying on whatever plugins are already installed on a developer machine.

## Scope (Phase 1)

- **Unit tests**: run agent Python scripts directly with fixture repos.
- **Package integrity**: build a temporary plugin bundle from `plugin.json` and verify all listed files are present.
- **Isolation**: ensure tests run against a temp `HOME` and do not read or write global plugin state.
- **Package-mapped tests**: keep package-specific tests under `test-packages/<pkg>/...` to mirror package layout.
- **Shared fixtures**: keep shared helpers under `test-packages/test_fixtures/`.

## What We Will Build

1) **Plugin bundle builder** (script)
   - Read `.claude-plugin/plugin.json` for a package.
   - Copy only listed files into a temporary plugin directory.
   - Always include `.claude-plugin/plugin.json`.
   - Script: `test-packages/test_fixtures/plugin_test_harness.py`.

2) **Pytest checks**
   - Verify bundle contains all files listed in `plugin.json`.
   - Run agent Python scripts against a temp repo with `HOME` set to a temp directory.
   - Isolation test skips if dependencies (e.g., PyYAML) are only available from user site-packages.
   - Local install simulation: build a bundle into a temp workspace-relative directory and assert only manifest-listed files are present.

## What We Will Not Build Yet

- Full CLI integration tests that invoke `claude` (optional later if CLI is available in CI).
- Marketplace publish/install workflows.

## How To Run (Local)

```bash
python3 test-packages/run_local_tests.py
python3 test-packages/run_local_tests.py --package sc-startup
python3 test-packages/run_local_tests.py --package sc-startup --integration
python3 test-packages/run_local_tests.py --package sc-startup --k checklist
python3 test-packages/run_local_tests.py --package sc-startup --report test-packages/reports/sc-startup.txt
python3 test-packages/run_local_tests.py --package sc-startup --report-md test-packages/reports/sc-startup.md
python3 test-packages/run_local_tests.py --package sc-startup --integration --test-repo /Users/randlee/Documents/github/sc-test-harness
pytest -q
```

Notes:
- Integration tests are marked with `@pytest.mark.integration` and skipped by default via `pytest.ini`.
- Use `--integration` in `run_local_tests.py` or `pytest -m integration` to run them.

## CI Expectations

- GitHub Actions already runs `pytest -q` for all tests under `tests/`.

## Known Gaps

- We do not yet assert that all runtime dependencies are bundled for `/plugin install`.
- We do not yet verify that Claude Code’s plugin installer copies only manifest-listed files.

## Next Steps (Phase 2)

- Add optional integration tests that use `claude --plugin-dir` (skips if CLI is unavailable, `ANTHROPIC_API_KEY` is missing, or CLI times out).
- Add a packaging validation check to enforce runtime files (e.g., agent `.py`) are bundled.

---

## Documentation & Resources

**For comprehensive testing and plugin validation guidance:**
- **[Documentation Index](docs/DOCUMENTATION-INDEX.md)** - Central hub for all development, testing, and deployment guides
- **[Plugin Quality Assurance (PQA)](pm/PQA.md)** - Test harness maintenance, plugin validation, and observability
- **[Plugin Test Creation Guidelines](test-packages/docs/plugin-test-creation-guidelines.md)** - How to create valid test fixtures

**For plugin development:**
- **[Architecture Guidelines](docs/claude-code-skills-agents-guidelines-0.4.md)** - Design patterns and best practices
- **[Storage Conventions](docs/PLUGIN-STORAGE-CONVENTIONS.md)** - Where logs, settings, and outputs go
