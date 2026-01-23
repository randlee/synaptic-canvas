# Commit-Push-PR Design (sc-commit-push-pr)

Design for `/sc-commit-push-pr` and `/sc-create-pr` with explicit primary-agent vs commit-push agent execution, Python-first pipelines, and hook usage. This document must stay consistent with the CSV flow diagram.

## Scope

- Python-first implementation with Pydantic validation.
- Minimal, deterministic API calls with auto-detection and hooks.
- Commit/push pipeline is handled by a background agent (`commit-push.md`).
- PR creation is handled by a separate background agent (`create-pr.md`).
- Support GitHub and Azure DevOps; auto-detect provider from git remote (no caching needed).

## Non-Goals

- No `--dry-run` in v1.
- No rebase-based conflict handling.
- No auto-staging of unknown files; agent must stage "important files" or ask.

## Commands (Primary Agent)

### `/sc-commit-push-pr`

- Treat as a function-style slash command.
- Stages important files (ask if unclear).
- Uses Agent Runner to invoke `commit-push` agent (per registry.yaml).
- If PR already exists, return success with PR URL.
- If PR is required, request PR text from the primary agent and then invoke `create-pr` agent via Agent Runner.

### `/sc-create-pr`

- Standalone slash command.
- Accepts PR title/body from user input.
- Uses Agent Runner to invoke `create-pr` agent directly.

## Agent Roles

- **Primary agent**: CLI I/O, prompt text, and command branching based on agent returns.
- **Commit-push agent (`commit-push.md`)**: background agent that runs commit/pull/merge/push and checks PR status.
- **Create-pr agent (`create-pr.md`)**: background agent that creates a PR from title/body.

## Hook Usage

- Start hooks are defined in each agent frontmatter (SubAgentStart hook per agent).
- Hooks do preflight validation:
  - Detect protected branches from git-flow or `.sc/shared-settings.yaml`
  - Auto-populate `.sc/shared-settings.yaml` if git-flow detected
  - Fail with error if protected branches not configured
  - Validate git authentication
  - Log preflight status to `.claude/state/logs/sc-commit-push-pr/`

## Configuration

### Protected Branches

Required for workflow logic (worktree vs direct push decision).

**Auto-detection (first run):**
- Hook checks for git-flow config
- If found, creates `.sc/shared-settings.yaml` automatically

**Manual configuration:**
```yaml
# .sc/shared-settings.yaml
git:
  protected_branches:
    - main
    - develop
```

**Field name:** `git.protected_branches` (normative from storage conventions)

### Provider Detection

No configuration needed - auto-detected from git remote every run:
```python
# Parse git remote URL
remote_url = subprocess.run(["git", "remote", "get-url", "origin"], ...)

if "dev.azure.com" in remote_url:
    # Parse: https://dev.azure.com/org/project/_git/repo
    provider = "azuredevops"
    org, project, repo = parse_azure_url(remote_url)

elif "github.com" in remote_url:
    # Parse: https://github.com/org/repo
    provider = "github"
    org, repo = parse_github_url(remote_url)
```

### Credentials

Standard environment variable names (no configuration):
- GitHub: `GITHUB_TOKEN`
- Azure DevOps: `AZURE_DEVOPS_PAT`

### Settings Fallback Chain

Per storage conventions, settings are resolved in this order:
1. Package settings: `.sc/sc-commit-push-pr/settings.yaml` (optional, for package-specific prefs)
2. Shared settings: `.sc/shared-settings.yaml` (protected branches live here)
3. User settings: `~/.sc/shared-settings.yaml` (user-global fallback)
4. Defaults: Built-in defaults in scripts

## Pipeline Summary (Commit-Push Agent)

- The commit-push agent runs a **single Python tool call**:
  - `commit_pull_merge_commit_push.py`
- This Python script does:
  - resolve branches
  - check staged changes (skip commit if none, continue pipeline)
  - fetch, pull+merge
  - if merge conflicts: return `GIT.MERGE_CONFLICT`
  - if no conflicts: continue pipeline (commit merge if needed, push)
  - check existing PR and return status + URL

If merge conflicts occur, the Python script returns `GIT.MERGE_CONFLICT` and the primary agent resolves conflicts, then re-runs the commit-push agent from the start.

## Pipeline Summary (Create-PR Agent)

- The create-pr agent runs a **single Python tool call**:
  - `create_pr.py`
- This Python script creates a PR using provided title/body and returns PR info.

## Script Inventory

All scripts live in `packages/sc-commit-push-pr/.claude/scripts/`. Hook paths in agent frontmatter are relative to the package directory.

- `commit_pull_merge_commit_push.py` (commit/pull/merge/push + PR status)
- `create_pr.py` (create PR from title/body)
- `provider_detect.py` (parse git remote URL for GitHub/Azure)
- `pr_provider.py` (GitHub/Azure API abstraction)
- `commit_push_agent_start_hook.py` (preflight: protected branches + auth)
- `create_pr_agent_start_hook.py` (preflight: protected branches + permissions)

## Package Dependencies (manifest.yaml)

All Python dependencies must be declared in `manifest.yaml` per Tool Use Best Practices:

```yaml
# packages/sc-commit-push-pr/manifest.yaml
name: sc-commit-push-pr
version: 0.1.0
description: Commit, push, and create PRs for GitHub and Azure DevOps

requires:
  python:
    - pydantic
    - pyyaml
  cli:
    - python3
    - git
    - gh  # GitHub CLI (optional, for GitHub provider)

tier: 2  # Runtime dependencies required
```

## Registry Schema (registry.yaml)

Agents must be registered for Agent Runner invocation per Architecture Guidelines v0.5:

```yaml
# packages/sc-commit-push-pr/.claude/agents/registry.yaml
version: "1.0"

agents:
  commit-push:
    path: .claude/agents/commit-push.md
    version: "0.1.0"
    description: Background agent for commit/pull/merge/push and PR status lookup

  create-pr:
    path: .claude/agents/create-pr.md
    version: "0.1.0"
    description: Background agent for creating PRs from title/body

skills:
  sc-commit-push-pr:
    path: .claude/skills/sc-commit-push-pr/SKILL.md
    version: "0.1.0"
    depends_on:
      - commit-push@0.1.x
      - create-pr@0.1.x
```

## SKILL.md Specification

The skill file orchestrates the two-tier pattern per Architecture Guidelines v0.5:

```yaml
# packages/sc-commit-push-pr/.claude/skills/sc-commit-push-pr/SKILL.md
---
name: sc-commit-push-pr
version: 0.1.0
description: Commit staged changes, push to remote, and create PRs
---
```

### Capabilities

| Command | Description |
|---------|-------------|
| `/sc-commit-push-pr` | Full pipeline: commit, push, and create PR if needed |
| `/sc-create-pr` | Create PR from title/body (standalone) |

### Agent Delegation

| Step | Agent | Input | Output |
|------|-------|-------|--------|
| Commit & Push | `commit-push` | source/destination branches | PR status, URL, or conflict list |
| Create PR | `create-pr` | title, body, source, destination | PR info |

### Orchestration Logic

1. **On `/sc-commit-push-pr`:**
   - Stage important files (prompt user if unclear)
   - Invoke `commit-push` agent via Agent Runner
   - Parse fenced JSON response
   - If `pr_exists: true` → return PR URL to user
   - If `needs_pr_text: true` → prompt user for title/body, then invoke `create-pr`
   - If `error.code == "GIT.MERGE_CONFLICT"` → guide user through resolution

2. **On `/sc-create-pr`:**
   - Accept title/body from user
   - Invoke `create-pr` agent via Agent Runner
   - Return PR URL to user

## Agent Frontmatter Schema

Agent markdown files must include YAML frontmatter with versioning and hook definition.

Example: `commit-push.md`

```yaml
---
name: commit-push
version: 0.1.0
description: Background agent for commit/pull/merge/push and PR status lookup.
hooks:
  SubAgentStart:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 .claude/scripts/commit_push_agent_start_hook.py"
---
```

**What the hook does:**
1. Check for protected branches in `.sc/shared-settings.yaml`
2. If not found, try git-flow detection (`gitflow.branch.master`, `gitflow.branch.develop`)
3. If found via git-flow, auto-create `.sc/shared-settings.yaml`
4. If not found anywhere, fail with error:
   ```
   ERROR: Protected branches not configured.

   Create .sc/shared-settings.yaml with:
   git:
     protected_branches: [main, develop]
   ```
5. Validate git authentication
6. Log preflight to `.claude/state/logs/sc-commit-push-pr/`
7. Exit 0 (allow) or Exit 2 (block)

Example: `create-pr.md`

```yaml
---
name: create-pr
version: 0.1.0
description: Background agent for creating PRs from title/body.
hooks:
  SubAgentStart:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 .claude/scripts/create_pr_agent_start_hook.py"
---
```

**What the hook does:**
Same as commit-push hook (checks protected branches, validates permissions).

## Output Contract

Agents return fenced JSON only.

Success (PR exists):

```json
{
  "success": true,
  "data": {
    "pr": {
      "id": "123",
      "url": "https://...",
      "source_branch": "feature-x",
      "destination_branch": "main",
      "provider": "github"
    },
    "pr_exists": true
  },
  "error": null
}
```

Needs PR text:

```json
{
  "success": true,
  "data": {
    "needs_pr_text": true,
    "context": {
      "source_branch": "feature-x",
      "destination_branch": "main",
      "diff_summary": "..."
    }
  },
  "error": null
}
```

Merge conflict:

```json
{
  "success": false,
  "data": {
    "conflicts": ["path/file1", "path/file2"]
  },
  "error": {
    "code": "GIT.MERGE_CONFLICT",
    "message": "Merge conflict detected when pulling destination branch.",
    "recoverable": true,
    "suggested_action": "Resolve conflicts, stage important files, then re-run."
  }
}
```

## Script Input/Output Schemas (Exact)

All scripts use Pydantic for validation and return the standard envelope.

### Common Envelope

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorPayload(BaseModel):
    code: str
    message: str
    recoverable: bool = False
    suggested_action: Optional[str] = None

class Envelope(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorPayload] = None
```

### `commit_pull_merge_commit_push.py` Input

```python
from pydantic import BaseModel
from typing import Optional

class CommitPushInput(BaseModel):
    source: Optional[str] = None
    destination: Optional[str] = None
```

### `commit_pull_merge_commit_push.py` Output (data payload)

```python
from pydantic import BaseModel
from typing import Optional, List

class PullRequestInfo(BaseModel):
    id: str
    url: str
    source_branch: str
    destination_branch: str
    provider: str

class CommitPushData(BaseModel):
    pr_exists: bool
    pr: Optional[PullRequestInfo] = None
    needs_pr_text: bool = False
    context: Optional[dict] = None  # diff summary, branch info
    conflicts: Optional[List[str]] = None
```

### `create_pr.py` Input

```python
from pydantic import BaseModel

class CreatePrInput(BaseModel):
    title: str
    body: str
    source: str
    destination: str
```

### `create_pr.py` Output (data payload)

```python
from pydantic import BaseModel

class CreatePrData(BaseModel):
    pr: PullRequestInfo
```

## Error Codes and Retry Policy

Use structured error codes and conservative retries.

### Codes

- `GIT.MERGE_CONFLICT`: merge conflicts detected during pull/merge.
- `GIT.AUTH`: git auth failure.
- `GIT.REMOTE`: remote fetch/push failure.
- `PR.CREATE_FAILED`: provider API failed to create PR.
- `PR.NOT_FOUND`: expected PR missing after push.
- `PROVIDER.DETECT_FAILED`: provider could not be detected from remotes.

### Retry Guidance

- No automatic retries by default.
- Only retry if `error.recoverable == true`, and at most once.
- Merge conflicts are not recoverable by automation; require user/agent resolution.

## CSV Sequence Diagram (Authoritative)

This project’s authoritative flow diagram is a CSV for easy editing:

`/Users/randlee/Documents/github/synaptic-canvas/.temp/commit-push-pr.csv`

If changes are made to flow logic, update that CSV first, then sync this document.

## Logs

Runtime events, hook executions, and audit trails:
- **Location:** `.claude/state/logs/sc-commit-push-pr/`
- **Format:** JSON (one file per operation or newline-delimited)
- **Retention:** 14 days (per storage conventions)
- **Never log:** Git credentials, API tokens, PR bodies with secrets
- **Gitignore:** `.claude/state/logs/` should be excluded from version control

Example log entry (includes standard fields per storage conventions):
```json
{
  "timestamp": "2026-01-22T15:30:00Z",
  "level": "info",
  "message": "Commit and push completed successfully",
  "context": {
    "operation": "commit-push",
    "provider": "azuredevops",
    "source_branch": "feature-x",
    "destination_branch": "main",
    "protected": true
  },
  "outcome": "success",
  "pr_id": "123"
}
```

## README Requirements

Per Plugin Storage Conventions verification checklist, the package README.md must include:

### Required Sections

1. **Logs Section:**
   ```markdown
   ## Logs

   Runtime logs are written to `.claude/state/logs/sc-commit-push-pr/`.
   - Format: JSON (newline-delimited)
   - Retention: 14 days
   - Contains: Operation outcomes, branch info, PR IDs
   - Never contains: Credentials, tokens, secrets
   ```

2. **Configuration Section:**
   ```markdown
   ## Configuration

   ### Protected Branches (Required)
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
   - GitHub: `GITHUB_TOKEN`
   - Azure DevOps: `AZURE_DEVOPS_PAT`
   ```

3. **Storage Locations Summary:**
   | Type | Path | Purpose |
   |------|------|---------|
   | Logs | `.claude/state/logs/sc-commit-push-pr/` | Runtime events |
   | Shared Settings | `.sc/shared-settings.yaml` | Protected branches |
   | Package Settings | `.sc/sc-commit-push-pr/settings.yaml` | Optional preferences |

## Notes

- Package lives in `packages/sc-commit-push-pr/` with standard structure
- Provider info (Azure org/project, GitHub org) auto-detected from git remote (not stored)
- Protected branches in `.sc/shared-settings.yaml` (auto-detected from git-flow or manual)
- The commit-push agent should return PR status + URL in its fenced JSON
- Hooks check protected branches at SubAgentStart, fail fast if not configured
- Agent Runner is used for all agent invocations (registry validation, audit logging)
- All agents return fenced JSON only (no prose outside code blocks)
