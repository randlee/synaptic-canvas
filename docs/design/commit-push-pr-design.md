# Commit-Push-PR Design (sc-commit-push-pr)

Design for `/sc-commit-push-pr` and `/sc-create-pr` with explicit primary-agent vs commit-push agent execution, Python-first pipelines, and hook usage. This document must stay consistent with the CSV flow diagram.

## Scope

- Python-first implementation with Pydantic validation.
- Minimal, deterministic API calls with caching and hooks.
- Commit/push pipeline is handled by a background agent (`commit-push.md`).
- PR creation is handled by a separate background agent (`create-pr.md`).
- Support GitHub and Azure DevOps; detect provider and cache settings in `.sc/shared-settings.yml` (Azure only).

## Non-Goals

- No `--dry-run` in v1.
- No rebase-based conflict handling.
- No auto-staging of unknown files; agent must stage "important files" or ask.

## Commands (Primary Agent)

### `/sc-commit-push-pr`

- Treat as a function-style slash command.
- Stages important files (ask if unclear).
- Invokes `commit-push.md` agent.
- If PR already exists, return success with PR URL.
- If PR is required, request PR text from the primary agent and then invoke `create-pr.md` agent.

### `/sc-create-pr`

- Standalone slash command.
- Accepts PR title/body from user input.
- Invokes `create-pr.md` agent directly.

## Agent Roles

- **Primary agent**: CLI I/O, prompt text, and command branching based on agent returns.
- **Commit-push agent (`commit-push.md`)**: background agent that runs commit/pull/merge/push and checks PR status.
- **Create-pr agent (`create-pr.md`)**: background agent that creates a PR from title/body.

## Hook Usage

- Start hooks are defined in each agent frontmatter (same hook file per agent).
- Hooks do preflight only:
  - Provider detection from remotes.
  - Azure settings cache in `.sc/shared-settings.yml`.
- Preflight state write (no pipeline execution).

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

## Script Inventory (plugin/scripts/)

All scripts live in `plugin/scripts/` and are flattened to `.claude/scripts/` on deploy.

- `commit_pull_merge_commit_push.py` (commit/pull/merge/push + PR status)
- `create_pr.py` (create PR from title/body)
- `repo_detect.py` (provider detection + Azure cache)
- `pr_provider.py` (GitHub/Azure abstraction)

## Agent Frontmatter Schema

Agent markdown files must include YAML frontmatter with versioning and hook definition.
Hooks are defined in frontmatter and call Python scripts (flattened to `.claude/scripts/`).

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

## Notes

- No changes should be made under `.claude/`; plugin agents/commands/skills live under `packages/`.
- The commit-push agent should return PR status + URL in its fenced JSON.
