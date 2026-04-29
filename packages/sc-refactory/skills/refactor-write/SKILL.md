---
name: refactor-write
version: 0.1.0
description: >
  Use this skill to author or update approved refactor rules. The workflow is:
  write the authoritative markdown doc, capture a minimal trigger set, add a
  few repo-root sample fix references, write the Turtle source of truth under
  `.refactor/rules/`, and verify lookup in Oxigraph using `.refactor/db/` or a
  temporary store.
---

# Refactor Write

Read [workflows.md](./workflows.md) for the full authoring workflow and the
temporary-store verification pattern.
If pre-flight fails, read
`.refactor/docs/install-and-troubleshooting.md`.

## Agent Delegation

Use Agent Runner to invoke `refactor-write-agent` as defined in
`.claude/agents/registry.yaml`.

The agent must be invoked with a `0.1.x` version constraint. Treat unfenced or
malformed JSON as failure.

Before invoking the agent, run the local pre-flight:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-write
```

If this prints `oxigraph v ... checks pass`, proceed.

If it fails, do not invoke the agent. Read
`.refactor/docs/install-and-troubleshooting.md`, run the scripted repair path,
and rerun pre-flight first.

## /rule-write

```json
{
  "operation": "rule",
  "rule_id": "<kebab-case identifier>",
  "severity": "<breaking|warning|info>",
  "doc_path": ".refactor/docs/<doc-name>.md",
  "triggers": [
    { "signal": "FocusDistance", "kind": "type" },
    { "signal": "Legacy.Imaging.ExposureTime", "kind": "string" }
  ],
  "summary": "<short policy summary>",
  "allowed_fixes": [
    "<bounded fix shape 1>",
    "<bounded fix shape 2>"
  ],
  "notes": "<optional extra operator notes>",
  "derived_from": null
}
```

Valid `kind` values: `namespace`, `type`, `error`, `string`, `assembly`

## /fix-write

Multiple fixes may be written in one call. Each fix is a pointer to where the
rule is documented or already applied in the codebase. Use repo-root-relative
paths only.

```json
{
  "operation": "fix",
  "rule_id": "<rule this fix belongs to>",
  "fixes": [
    {
      "fix_id": "fix-001",
      "path": ".refactor/docs/example-rule.md",
      "line": 1,
      "confidence": "high",
      "source": "approved-doc"
    },
    {
      "fix_id": "fix-002",
      "path": "RepoA/Path/Example.cs",
      "line": 177,
      "confidence": "high",
      "source": "recent-git-example"
    }
  ]
}
```

- `path` — repo-root-relative path to the file containing the approved example
- `line` — line number where the fix is visible
- `confidence` — `high`, `medium`, or `low`
- `source` — use values such as `approved-doc`, `canonical-example`,
  `recent-git-example`, or another concise descriptive label

## Agent returns

Success:

```json
{
  "success": true,
  "canceled": false,
  "aborted_by": null,
  "data": {
    "operation": "<rule|fix>",
    "ids": ["<id1>", "<id2>"],
    "ttl_paths": [".refactor/rules/<id>.ttl"],
    "loaded_to_store": true
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
    "code": "VALIDATION.INPUT",
    "message": "Fix path must be repo-root-relative",
    "recoverable": true,
    "suggested_action": "Replace the absolute path with a repo-root-relative path"
  },
  "metadata": {
    "duration_ms": 0,
    "tool_calls": 0,
    "retry_count": 0
  }
}
```
