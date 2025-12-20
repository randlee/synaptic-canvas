# Use Cases

Practical examples and workflows for sc-ci-automation.

## Table of Contents

1. [Quick Test Before Commit](#quick-test-before-commit)
2. [Full CI Pipeline with Auto-PR](#full-ci-pipeline-with-auto-pr)
3. [Version Bump and Release](#version-bump-and-release)
4. [Custom Target Branch](#custom-target-branch)
5. [Build-Only Validation](#build-only-validation)
6. [Allow Warnings Mode](#allow-warnings-mode)
7. [Parallel Worktree Development](#parallel-worktree-development)
8. [Hotfix Workflow](#hotfix-workflow)

---

## Quick Test Before Commit

**Scenario:** You've made changes and want to verify they build and pass tests before committing.

**Command:**
```
/sc-ci-automation --test
```

**What happens:**
1. Pulls latest from upstream
2. Runs build (auto-fixes simple issues)
3. Runs tests (auto-fixes simple failures)
4. Reports status
5. Stops before commit/push/PR

**Result:** You get confidence that your changes are safe to commit.

---

## Full CI Pipeline with Auto-PR

**Scenario:** You're ready to merge your feature branch and want automated PR creation.

**Command:**
```
/sc-ci-automation --yolo
```

**What happens:**
1. Validates repo is clean
2. Pulls latest from upstream
3. Runs build (auto-fixes simple issues)
4. Runs tests (auto-fixes simple failures)
5. If all gates pass:
   - Commits any auto-fixes
   - Pushes to remote
   - Creates PR to upstream branch

**Safety:** Only proceeds with commit/push/PR if all quality gates pass cleanly.

---

## Version Bump and Release

**Scenario:** You're preparing a patch release and want to bump version, build, test, and create PR.

**Command:**
```
/sc-ci-automation --patch --yolo
```

**What happens:**
1. Increments patch version (e.g., 1.2.3 → 1.2.4)
2. Runs full CI pipeline
3. If all gates pass, creates PR with version bump included

**Configuration Required:**
```yaml
# .claude/ci-automation.yaml
version_file: version.txt  # or package.json, setup.py, etc.
```

---

## Custom Target Branch

**Scenario:** You want to create PR to `develop` instead of default `main`.

**Command:**
```
/sc-ci-automation --dest develop --yolo
```

**What happens:**
1. Pulls from `develop` branch
2. Runs build + tests
3. Creates PR targeting `develop`

**Use case:** Multi-branch workflows (gitflow, github-flow with develop branch)

---

## Build-Only Validation

**Scenario:** You want to verify code compiles before running time-consuming tests.

**Command:**
```
/sc-ci-automation --build
```

**What happens:**
1. Pulls latest from upstream
2. Runs build only
3. Auto-fixes simple build errors
4. Stops after build (skips tests and PR)

**Use case:** Quick validation during development, especially for large test suites.

---

## Allow Warnings Mode

**Scenario:** Your project has non-critical warnings you want to ignore for this PR.

**Command:**
```
/sc-ci-automation --allow-warnings --yolo
```

**What happens:**
1. Runs full pipeline
2. Allows warnings to pass quality gates
3. Creates PR even with warnings present

**Warning:** Use sparingly. Better to fix warnings than suppress them.

**Alternative:** Configure globally:
```yaml
# .claude/ci-automation.yaml
allow_warnings: true
```

---

## Parallel Worktree Development

**Scenario:** You're working on multiple features in parallel worktrees and want to test each independently.

**Setup:**
```
# Create worktrees using sc-git-worktree
/sc-git-worktree --create feature-a main
/sc-git-worktree --create feature-b main
```

**Commands:**
```bash
# In worktree-feature-a
cd ../myrepo-worktrees/feature-a
/sc-ci-automation --test

# In worktree-feature-b
cd ../myrepo-worktrees/feature-b
/sc-ci-automation --test
```

**What happens:**
- Each worktree runs CI independently
- No interference between feature branches
- Can merge when both pass quality gates

**Use case:** Developing multiple features simultaneously without branch-switching overhead.

---

## Hotfix Workflow

**Scenario:** Production bug requires immediate fix. You need fast validation and deployment.

**Commands:**
```bash
# Create hotfix branch (or worktree)
git checkout -b hotfix/critical-bug main

# Make fix
# ... edit code ...

# Fast validation
/sc-ci-automation --test

# If passes, create PR
/sc-ci-automation --dest main --yolo
```

**What happens:**
1. Validates fix builds and passes tests
2. Creates PR directly to `main` (or production branch)
3. Explicit confirmation required for PR to main/master

**Safety:** Confirmation step prevents accidental pushes to protected branches.

---

## Advanced: Multi-Stage Pipeline

**Scenario:** Complex project with multiple build/test stages.

**Config:**
```yaml
# .claude/ci-automation.yaml
upstream_branch: main
build_command: |
  dotnet restore &&
  dotnet build --no-restore &&
  dotnet pack --no-build
test_command: |
  dotnet test --no-build --verbosity normal &&
  dotnet test IntegrationTests/ --no-build
warn_patterns:
  - "warning CS\\d+"
  - "WARN:"
  - "deprecated"
allow_warnings: false
auto_fix_enabled: true
```

**Command:**
```
/sc-ci-automation --yolo
```

**What happens:**
1. Runs multi-stage build (restore → build → pack)
2. Runs unit tests + integration tests
3. Detects and blocks on warnings
4. Auto-fixes straightforward issues
5. Creates PR only if all stages pass

---

## Tips and Best Practices

### 1. Start Conservative
Use `--test` flag initially to understand what CI automation will do before enabling `--yolo`.

### 2. Configure Once, Run Anywhere
Create `.claude/ci-automation.yaml` and commit it. All team members benefit from consistent CI.

### 3. Use Worktrees for Risky Changes
Combine with `sc-git-worktree` for experimental work that might break CI.

### 4. Leverage Auto-Fix Carefully
The `ci-fix-agent` only applies straightforward fixes. Complex issues require manual intervention.

### 5. Monitor Audit Logs
Check `.claude/state/logs/ci-automation/` to understand what agents did during pipeline runs.

### 6. Version Bumping
Use `--patch` for bug fixes, manually bump minor/major versions for features/breaking changes.

---

## Related Workflows

- **sc-git-worktree**: For parallel feature development
- **sc-github-issue**: For issue-driven development with CI validation

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed guidance on common issues.
