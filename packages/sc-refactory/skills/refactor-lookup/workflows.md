# Refactor Lookup Workflows

## Why This Skill Exists

This repo is using a strict allowlist model for multi-repo refactors. The main
session should know the concise trigger index, but the expensive graph lookup
and example discovery should stay isolated in the lookup agent.

Use this skill to answer one question:

`Does this signal map to an approved refactor rule, and if so what document and sample fixes govern it?`

Runtime convention:

- tracked docs: `.refactor/docs/`
- tracked rules: `.refactor/rules/`
- persistent Oxigraph store: `.refactor/db/`
- startup/context scripts: `.refactor/scripts/`
- temp query files and scratch stores: `.refactor/temp/`

## When To Invoke

Invoke lookup before editing when any of these show up:

- a known type or namespace
- a package or project name
- an error code
- a file name used as a policy trigger
- a string from the session-start trigger index

## Workflow

1. Extract the smallest useful set of signals from the current problem.
2. Run `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-lookup`.
3. If it prints `oxigraph v ... checks pass`, continue.
4. If it fails, read `.refactor/docs/install-and-troubleshooting.md` and run
   `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-lookup`.
5. Re-run pre-flight.
6. If pre-flight now passes, invoke `refactor-lookup-agent` through Agent
   Runner.
7. If pre-flight still fails after the scripted repair path, stop and surface a
   concise environment problem.
8. If lookup returns a match, read the approved markdown doc first.
9. Read the primary code example only if the doc alone is not enough.
10. Apply only the fix shapes authorized by the matched rule.

## Interpretation Rules

- A trigger hit is enough to surface the policy document.
- The lookup agent should reject only obvious false positives, such as hits that
  occur only inside fenced code blocks in markdown.
- The approved markdown doc is the primary authority.
- Code examples are secondary references that show shape, not permission to go
  beyond the rule.
- Some rules intentionally use one document for multiple triggers. The lookup
  result should still surface that single shared document.

## Repo Path Rules

- Sample fix paths must start at the multi-repo root:
  `RepoA/...`, `RepoB/...`, `.refactor/docs/...`
- Do not return absolute paths in fix references.

## Failure Handling

- Prefer local pre-flight failure over background-agent failure. If the
  environment is obviously broken, do not spend an agent call on it.
- The skill should attempt the documented scripted repair path itself before
  surfacing the problem to the user.
- If the agent returns unfenced JSON or malformed JSON, treat it as failure.
- If the graph is unavailable, stop and surface a concise error.
- If no rule matches, proceed without a rule only after lookup completes with a
  valid `matched: false` result.
