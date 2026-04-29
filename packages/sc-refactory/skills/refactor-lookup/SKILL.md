---
name: refactor-lookup
version: 0.1.0
description: >
  Use this skill before editing when a known trigger appears during a refactor
  session. It delegates graph lookup to a focused agent, returns the governing
  markdown policy document plus a few repo-root fix references, and enforces the
  approved-fixes-only workflow.
---

# Refactor Lookup

Use this skill to answer one question:

`Does this signal map to an approved refactor rule, and if so what document and sample fixes govern it?`

Read [workflows.md](./workflows.md) for the full workflow and rationale.
If pre-flight fails, read
`.refactor/docs/install-and-troubleshooting.md`.

## Agent Delegation

Use Agent Runner to invoke `refactor-lookup-agent` as defined in
`.claude/agents/registry.yaml`.

The agent must be invoked with a `0.1.x` version constraint. Treat unfenced or
malformed JSON as failure.

Before invoking the agent, run the local pre-flight:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-lookup
```

If this prints `oxigraph v ... checks pass`, proceed.

If it fails, do not invoke the agent. Read
`.refactor/docs/install-and-troubleshooting.md`, run the scripted repair path,
and rerun pre-flight. The background agent should be reserved for actual rule
lookup, not basic environment diagnosis.

Runner payload:

```json
{
  "agent": "refactor-lookup-agent",
  "version_constraint": "0.1.x",
  "timeout_s": 120,
  "params": {
    "signals": [
      {
        "string": "FocusDistance",
        "kind": "type",
        "repo_relative_path": "RepoA/src/Optics/LensOperationsTests.cs",
        "line": 183
      }
    ],
    "context": "Compiler error text, CI output, or review context here"
  }
}
```

## Input to subagent

```json
{
  "signals": [
    {
      "string": "<type, namespace, assembly, error code, file name, or identifier>",
      "kind": "<type|namespace|assembly|string|error>",
      "repo_relative_path": "<repo-root-relative path>",
      "full_path": "<absolute path if already known>",
      "line": 4
    }
  ],
  "context": "<compiler errors, CI log lines, or surrounding context — may be multiline>"
}
```

- `string` — the signal value
- `kind` — optional but preferred
- `repo_relative_path` — preferred file path for policy references
- `full_path` — optional absolute path when that is what the caller has
- `line` — optional; include when known
- `context` — free text: compile output, test failure, log snippet

## Subagent returns

Match:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "matched": true,
    "rule_id": "<rule_id>",
    "confidence": "<high|medium|low>",
    "reason": "<one sentence>",
    "rule_text": "<full rule markdown from graph>",
    "fix": {
      "fix_id": "<fix_id>",
      "path": "<repo-root-relative path>",
      "line": 1
    },
    "references": [
      {
        "fix_id": "<fix_id>",
        "path": "<repo-root-relative path>",
        "line": 88
      }
    ]
  },
  "error": null,
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

No match:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "matched": false,
    "rule_id": null,
    "confidence": "low",
    "reason": "<one sentence>",
    "rule_text": null,
    "fix": null,
    "references": []
  },
  "error": null,
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

Failure:

```json
{
  "success": false,
  "canceled": false,
  "aborted_by": null,
  "data": null,
  "error": {
    "code": "EXECUTION.GRAPH_UNAVAILABLE",
    "message": "Graph store is unavailable",
    "recoverable": true,
    "suggested_action": "Verify oxigraph is installed and the graph store is readable"
  },
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```

## After receiving result

- `success: true` and `data.matched: true` — read the primary markdown doc
  first. Read code examples only if the doc alone does not answer the bounded
  fix shape.
- `success: true` and `data.matched: false` — proceed without a rule. If you
  discover a new approved pattern, invoke `refactor-write`.
- `success: false` — stop. Do not edit until graph access or JSON contract
  issues are resolved.
- When signals come from markdown or documentation files, ignore occurrences
  that appear only inside fenced code blocks. Fenced examples are documentation,
  not actionable source matches.
- A trigger hit should surface the policy document broadly. The document may
  still authorize only a narrower edit shape.
