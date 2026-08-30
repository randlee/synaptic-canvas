# sc-commit-push-pr

Commit, push, and create pull requests for GitHub and Azure DevOps repositories.

## Installation

```bash
# From Synaptic Canvas marketplace
/marketplace install sc-commit-push-pr
```

## Quick Start

```bash
# Stage, commit, push, and create PR in one command
/sc-commit-push-pr

# Create PR with specific title/body
/sc-create-pr --title "feat: Add feature" --body "Description here"
```

## Features

- **Multi-provider support** - GitHub and Azure DevOps
- **Auto-detection** - Provider detected from git remote
- **Protected branch awareness** - Respects branch protection rules
- **Conflict handling** - Guides through merge conflict resolution
- **Git-flow integration** - Auto-detects protected branches from git-flow config

## Stacked Branches (Hard Dependency)

sc-commit-push-pr is the critical junction where a stack-unaware
commit/pull/merge/push or PR creation can corrupt a `gh stack`'s linearity.
For that reason it now **requires the full gh-stack toolchain
unconditionally** -- the `gh` CLI, the `gh-stack` extension
(`gh extension install github/gh-stack`), and the **managing-gh-stacks
skill** (package `sc-gh-stack`) must all be installed before this package
will run *any* commit/pull/merge/push or PR-creation flow, on every branch
and regardless of provider. This applies even in Azure DevOps-hosted repos:
a mixed-provider org still gets one uniform prerequisite set. If any piece
is missing, every script call (and the SubAgentStart preflight hook for
both agents) refuses immediately with `PREFLIGHT.STACK_PREREQS_MISSING` and
tells you exactly what to install.

Once prerequisites are met, sc-commit-push-pr detects (state-based, no
config needed) whether the *current* worktree is itself a gh-stack layer.
Plain branches are unaffected -- same commit/push/PR flow as always. On a
stack layer:
- Commit still happens normally.
- Pulling and merging the destination branch is skipped (that's
  `gh stack sync`'s job).
- Push and PR creation are refused with `STACK.USE_GH_STACK`, deferring to
  `gh stack submit --auto` via the managing-gh-stacks skill.

Never work around either refusal with a direct `git push` or
`gh pr create` -- install what's missing, or run the stacked-branch
operation through the managing-gh-stacks skill.

## Configuration

### Protected Branches (Required)

Create `.sc/shared-settings.yaml` in your repository root:

```yaml
git:
  protected_branches:
    - main
    - develop
```

**Auto-detection:** If you use git-flow, protected branches are detected automatically from your git config.

### Credentials

Set environment variables for your provider:

| Provider | Variable | Description |
|----------|----------|-------------|
| GitHub | `GITHUB_TOKEN` | Personal access token (or use `gh auth login`) |
| Azure DevOps | `AZURE_DEVOPS_PAT` | Personal access token with Code (Read & Write) scope |

## Commands

### `/sc-commit-push-pr`

Full pipeline command that:
1. Stages important files (prompts if unclear)
2. Commits changes with your message
3. Pulls and merges from destination branch
4. Pushes to remote
5. Creates PR if one doesn't exist

### `/sc-create-pr`

Standalone PR creation:
1. Accepts title and body
2. Creates PR for current branch
3. Returns PR URL

## Logs

Runtime logs are written to `.claude/state/logs/sc-commit-push-pr/`.

- **Format:** JSON (newline-delimited)
- **Retention:** 14 days
- **Contains:** Operation outcomes, branch info, PR IDs
- **Never contains:** Credentials, tokens, secrets

Example log entry:
```json
{
  "timestamp": "2026-01-22T15:30:00Z",
  "level": "info",
  "message": "Commit and push completed successfully",
  "context": {
    "operation": "commit-push",
    "provider": "github",
    "source_branch": "feature-x",
    "destination_branch": "main"
  }
}
```

## Storage Locations

| Type | Path | Purpose |
|------|------|---------|
| Logs | `.claude/state/logs/sc-commit-push-pr/` | Runtime events |
| Shared Settings | `.sc/shared-settings.yaml` | Protected branches |
| Package Settings | `.sc/sc-commit-push-pr/settings.yaml` | Optional preferences |

## Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `GIT.MERGE_CONFLICT` | Merge conflicts detected | Resolve conflicts, stage files, re-run |
| `GIT.AUTH` | Git authentication failure | Check credentials/tokens |
| `GIT.REMOTE` | Remote fetch/push failure | Check network, remote URL |
| `PR.CREATE_FAILED` | PR API error | Check permissions, branch names |
| `PROVIDER.DETECT_FAILED` | Unknown provider | Check git remote URL |
| `CONFIG.PROTECTED_BRANCH_NOT_SET` | Missing config | Create `.sc/shared-settings.yaml` |
| `STACK.USE_GH_STACK` | Branch is a gh-stack layer | Use the managing-gh-stacks skill (`gh stack sync` / `gh stack submit --auto`) |
| `PREFLIGHT.STACK_PREREQS_MISSING` | gh-stack toolchain not installed | Install what `suggested_action` lists |

## Requirements

- Python 3.8+
- git
- `gh` CLI -- **required unconditionally**, not just for GitHub PRs
- `gh-stack` extension (`gh extension install github/gh-stack`) -- **required unconditionally**
- managing-gh-stacks skill, from the `sc-gh-stack` package -- **required unconditionally**
- `pydantic` and `pyyaml` Python packages

## Security

This package uses your existing GitHub or Azure DevOps credentials to create
commits, push branches, and create pull requests. Review the staged changes,
target branch, and generated commands before execution; grant the minimum token
permissions needed and never place credentials or secrets in prompts,
configuration, or generated artifacts.

## License

MIT
