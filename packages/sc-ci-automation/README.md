# sc-ci-automation

[![Publisher Verified](https://img.shields.io/badge/publisher-verified-brightgreen)](https://github.com/randlee/synaptic-canvas/blob/main/docs/PUBLISHER-VERIFICATION.md)
[![Security Scanned](https://img.shields.io/badge/security-scanned-blue)](https://github.com/randlee/synaptic-canvas/blob/main/SECURITY.md)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version 0.7.0](https://img.shields.io/badge/version-0.7.0-blue)](CHANGELOG.md)

Scope: Local-only
Requires: git ≥ 2.20

Run CI quality gates with optional auto-fix and PR creation. Coordinates pull from upstream, builds projects, runs tests, applies straightforward fixes, and creates PRs when all quality gates pass.

Security: See [SECURITY.md](../../../SECURITY.md) for security policy and practices.

## Summary

Automates the pre-merge workflow: pull → build → test → fix → PR. Conservative by default with optional `--yolo` mode for auto-commit/push/PR when all gates pass. Supports version bumping with `--patch` flag.

## Quick Start (Local-only)

1) Install into a repo's `.claude` directory:
   ```bash
   python3 tools/sc-install.py install sc-ci-automation --dest /path/to/your-repo/.claude
   ```

2) In your repo, run a basic test:
   ```
   /sc-ci-automation --test
   ```

3) Run full CI pipeline with PR creation:
   ```
   /sc-ci-automation --yolo
   ```

## Usage

### Basic Commands

- `/sc-ci-automation` - Full pipeline: pull → build → test → (conditional) fix → (manual) PR
- `/sc-ci-automation --build` - Pull + build only (skip tests/PR)
- `/sc-ci-automation --test` - Pull + build + test (skip commit/push/PR)
- `/sc-ci-automation --yolo` - Auto-commit/push/PR after gates pass

### Advanced Options

- `--dest <branch>` - Override target branch for PR (default: inferred from tracking)
- `--src <branch>` - Override source branch/worktree (default: current branch)
- `--allow-warnings` - Allow warnings to pass quality gates (default: block)
- `--patch` - Increment patch version number before building project
- `--help` - Show usage and examples

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

The skill will auto-detect your project stack (.NET/Python/Node) and prompt to save suggested commands if config is missing.

## Workflow

The `/sc-ci-automation` command coordinates 7 specialized agents:

1. **ci-validate-agent** - Pre-flight checks (clean repo, config present, auth available)
2. **ci-pull-agent** - Pull target branch, handle simple merge conflicts
3. **ci-build-agent** - Run build, classify failures
4. **ci-test-agent** - Run tests, classify failures/warnings
5. **ci-fix-agent** - Apply straightforward fixes for build/test issues
6. **ci-root-cause-agent** - Analyze unresolved failures, recommend actions
7. **ci-pr-agent** - Commit, push, and create PR when gates pass

## Safety Features

- **Conservative by default**: Auto-fix only; stops before commit/PR unless clean and confirmed
- **`--yolo` mode**: Enables auto-commit/push/PR after gates pass
- **No force-push**: Respects protected branches and git hooks
- **Warning gates**: Warnings block PR unless `--allow-warnings` or config override
- **Explicit confirmation**: PRs to main/master require confirmation unless `--dest main` provided
- **Audit logs**: Agent Runner logs all invocations to `.claude/state/logs/ci-automation/`

## Install / Uninstall

Install (local-only):
```bash
python3 tools/sc-install.py install sc-ci-automation --dest /path/to/your-repo/.claude
```

Uninstall:
```bash
python3 tools/sc-install.py uninstall sc-ci-automation --dest /path/to/your-repo/.claude
```

## Examples

**Build and test without PR:**
```
/sc-ci-automation --test
```

**Full pipeline with version bump:**
```
/sc-ci-automation --patch --yolo
```

**Custom target branch:**
```
/sc-ci-automation --dest develop --yolo
```

**Allow warnings to pass:**
```
/sc-ci-automation --allow-warnings --yolo
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed guidance.

**Common Issues:**

- **"Dirty repo"**: Commit or stash changes before running CI automation
- **"Config not found"**: Create `.claude/ci-automation.yaml` or provide build/test commands interactively
- **"Auth required"**: Set `GITHUB_TOKEN` environment variable for PR creation
- **Build fails repeatedly**: Check `ci-root-cause-agent` output for unresolved issues
- **Tests fail with warnings**: Use `--allow-warnings` to pass quality gates despite warnings

## Use Cases

See [USE-CASES.md](USE-CASES.md) for practical examples and workflows.

## Dependencies

- git ≥ 2.20
- GitHub CLI (`gh`) for PR creation (optional, only needed for `--yolo` or manual PR step)

## Related Packages

- **sc-git-worktree**: Manage parallel worktrees for feature development
- **sc-github-issue**: GitHub issue lifecycle management with worktree isolation

## Documentation

- [README.md](README.md) - This file
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [USE-CASES.md](USE-CASES.md) - Practical examples and workflows
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

## License

MIT License. See [LICENSE](../../../LICENSE) for details.

## Contributing

See the main [synaptic-canvas repository](https://github.com/randlee/synaptic-canvas) for contribution guidelines.
