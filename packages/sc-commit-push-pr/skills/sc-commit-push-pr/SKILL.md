---
name: sc-commit-push-pr
version: 0.13.0
description: Commit staged changes, push to remote, and create PRs for GitHub and Azure DevOps
---

# sc-commit-push-pr Skill

Orchestrates the commit, push, and PR creation workflow using background agents.

## Capabilities

| Command | Description |
|---------|-------------|
| `/sc-commit-push-pr` | Full pipeline: commit, push, and create PR if needed |
| `/sc-create-pr` | Create PR from title/body (standalone) |

## Agent Delegation

| Step | Agent | Input | Output |
|------|-------|-------|--------|
| Commit & Push | `commit-push` | source/destination branches | PR status, URL, or conflict list |
| Create PR | `create-pr` | title, body, source, destination | PR info |

## Orchestration Logic

### `/sc-commit-push-pr` Flow

1. **Stage important files**
   - Prompt user if unclear which files to stage
   - Skip if no changes detected

2. **Invoke `commit-push` agent via Agent Runner**
   - Pass source/destination branch parameters
   - Parse fenced JSON response

3. **Handle response:**
   - If `pr_exists: true` → Return PR URL to user
   - If `needs_pr_text: true` → Prompt user for title/body, then invoke `create-pr`
   - If `error.code == "GIT.MERGE_CONFLICT"` → Guide user through conflict resolution

### `/sc-create-pr` Flow

1. **Accept title/body from user**
   - May be provided as arguments or prompted

2. **Invoke `create-pr` agent via Agent Runner**
   - Pass title, body, source, destination

3. **Return PR URL to user**

## Provider Support

- **GitHub** - Uses `gh` CLI for PR operations
- **Azure DevOps** - Uses REST API with `AZURE_DEVOPS_PAT`

Provider is auto-detected from git remote on each run.

## Stacked Branches

sc-commit-push-pr is the general-purpose commit/push/PR package, but it is
also the critical junction where a stack-unaware pull-merge-push or PR
creation can corrupt a gh-stack's linearity. Stack ownership belongs to
`gh stack` and the **managing-gh-stacks skill (package `sc-gh-stack`)** —
this package defers to it rather than working around it.

**Hard prerequisite (unconditional, every run, every branch, every
provider — including Azure DevOps-hosted repos):** the `gh` CLI, the
`gh-stack` extension, and the managing-gh-stacks skill must all be
installed. If any is missing, every script (and the SubAgentStart preflight
hooks for both agents) refuses immediately with
`PREFLIGHT.STACK_PREREQS_MISSING`, listing the exact install command for
whichever piece is missing. This makes installing sc-commit-push-pr the
enforcement point — a repo can't end up running this package without the
stack-safety toolchain in place, whether or not any branch in it happens to
be a stack layer.

**Stack-layer detection (state-based, once prerequisites pass):** each
script checks whether the *current* worktree carries gh-stack tracking (a
`gh-stack` marker under the worktree's git-dir — the same signal `gh stack`
itself uses). On a plain branch, nothing changes: byte-identical behavior,
no extra steps in the output. On a stack layer:

- Commit stays normal — fixing a bug on the layer that owns it is correct.
- Pull/merge-from-destination is **skipped** — syncing a layer with its
  base is `gh stack sync`'s job, never a plain merge.
- Push and PR creation are **refused** with `STACK.USE_GH_STACK`
  (recoverable) — a layer's PR base (the layer below it, with stack object
  linkage) and its push are owned exclusively by `gh stack submit --auto`.

If you see `STACK.USE_GH_STACK` or `PREFLIGHT.STACK_PREREQS_MISSING`: do
not work around it with a direct `git push` or `gh pr create` — follow the
`suggested_action`, install whatever is missing, and use the
**managing-gh-stacks skill** for the stacked-branch operation instead.

## Configuration

### Required: Protected Branches

Create `.sc/shared-settings.yaml`:

```yaml
git:
  protected_branches:
    - main
    - develop
```

Or let the skill auto-detect from git-flow configuration.

### Credentials

Set environment variables:
- GitHub: `GITHUB_TOKEN` (or `gh auth login`)
- Azure DevOps: `AZURE_DEVOPS_PAT`

## Error Handling

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `GIT.MERGE_CONFLICT` | Merge conflicts detected | Resolve conflicts, re-run |
| `GIT.AUTH` | Authentication failure | Check credentials |
| `PR.CREATE_FAILED` | API error creating PR | Check permissions |
| `CONFIG.PROTECTED_BRANCH_NOT_SET` | Missing config | Create shared-settings.yaml |
| `STACK.USE_GH_STACK` | Branch is a gh-stack layer | Use the managing-gh-stacks skill (`gh stack sync` / `gh stack submit --auto`); never work around with direct `git push`/`gh pr create` |
| `PREFLIGHT.STACK_PREREQS_MISSING` | gh-stack toolchain not installed | Install whatever `suggested_action` lists (gh CLI, `gh extension install github/gh-stack`, or the sc-gh-stack plugin) |

## Storage

| Type | Path | Purpose |
|------|------|---------|
| Logs | `.claude/state/logs/sc-commit-push-pr/` | Runtime events, preflight results |
| Shared Settings | `.sc/shared-settings.yaml` | Protected branch configuration |
| Package Settings | `.sc/sc-commit-push-pr/settings.yaml` | Optional preferences |

## Related

- [Design Document](../../../../docs/design/commit-push-pr-design.md)
- [commit-push Agent](../../agents/commit-push.md)
- [create-pr Agent](../../agents/create-pr.md)
