# Agent Runner

Agent Runner is a thin wrapper around Claude's Task tool. It adds policy enforcement and observability with zero prompt/token overhead.

- Validates agent name/path/version against `.claude/agents/registry.yaml`
- Reads YAML frontmatter from the agent file (expects `version:`)
- Computes SHA-256 of the agent file for runtime attestation
- Prepares a `task_prompt` for the Task tool
- Writes a redacted audit record to `.claude/state/logs/`

It does not run the Task tool itself; it prepares the prompt and records an audit.

## Repo layout

- `src/agent_runner/` — Python library module (`agent_runner.runner`)
- `tools/agent-runner.py` — CLI wrapper
- `.claude/agents/registry.yaml` — source of truth for agents and (optionally) skill constraints
- `scripts/validate-agents.py` — CI/pre-commit validator for registry ↔ frontmatter

## Getting started

1) Populate registry.yaml

```yaml
# .claude/agents/registry.yaml
agents:
  sc-worktree-create:
    version: 1.0.0
    path: .claude/agents/sc-worktree-create.md
skills:
  sc-managing-worktrees:
    depends_on:
      sc-worktree-create: "1.x"
```

Note: Path format
- Registry paths are relative to the project root (e.g., `.claude/agents/sc-worktree-create.md`).

2) Validate versions (frontmatter vs registry)

```bash
python3 scripts/validate-agents.py
```

3) Prepare a Task tool prompt (no execution yet)

```bash
python3 tools/agent-runner.py invoke --agent sc-worktree-create \
  --param branch=feature-x --param base=main --timeout 120
```

Example output (trimmed):

```json
{
  "ok": true,
  "agent": {
    "name": "sc-worktree-create",
    "path": "/abs/path/.claude/agents/sc-worktree-create.md",
    "version": "1.0.0",
    "sha256": "1f3a...c9"
  },
  "task_prompt": "Load ... and execute with parameters...",
  "timeout_s": 120,
  "audit_path": ".claude/state/logs/agent-runner-sc-worktree-create-...json"
}
```

4) Use in SKILL.md

Prefer this phrasing:

```markdown
Use the Agent Runner to invoke `sc-worktree-create` per `.claude/agents/registry.yaml` with parameters ...
Then run the Task tool with the provided task_prompt and return the agent's fenced JSON.
```

This keeps the skill readable while ensuring policy compliance and audit logs.

## Parallel guardrails

If a skill launches agents in parallel, recommend:
- Concurrency cap: default 3–4
- Per-task timeout: default 120s
- correlation_id per invocation; aggregate deterministically
- On timeout, map to:
  ```json
  {
    "success": false,
    "error": {
      "code": "EXECUTION.TIMEOUT",
      "message": "Agent exceeded per-task timeout",
      "recoverable": false,
      "suggested_action": "Increase timeout parameter or split agent into smaller tasks"
    }
  }
  ```

## Security notes

- Read secrets from environment variables (e.g., `NUGET_API_KEY`); never echo or serialize them.
- Keep audit records redacted (no secrets, no raw tool output).

## FAQ

- Does Agent Runner replace the Task tool?
  - No. It wraps the Task tool and adds policy checks + audit.

- Did this change any agent prompts?
  - No. This scaffold adds optional tooling only; existing agents and prompts are unchanged.
