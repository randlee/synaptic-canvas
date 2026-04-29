# Refactor Write Workflows

## Why This Skill Exists

New refactor rules are policy, not just notes. They need:

- a concise trigger or trigger set,
- one authoritative markdown how-to document,
- a few repo-root sample fix references,
- a Turtle source-of-truth entry that lookup can query safely.

This keeps future sessions bounded to approved fixes instead of open-ended
refactoring.

## Authoring Workflow

1. Write or update the authoritative markdown document first.
2. Keep the document scoped to one coherent fix policy.
3. Choose the minimal trigger set that should surface that document.
4. Run `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-write`.
5. If it prints `oxigraph v ... checks pass`, continue.
6. If it fails, read `.refactor/docs/install-and-troubleshooting.md` and run
   `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-write`.
7. Re-run pre-flight.
8. If pre-flight still fails after the scripted repair path, stop and surface a
   concise environment problem.
9. Pick 1-4 sample fix references from multiple repos when possible.
10. Write the TTL rule and fix entries under `.refactor/rules/`.
11. Verify lookup in a temporary Oxigraph store before relying on the rule.

## Authoring Rules

- One document may support multiple precise triggers.
- The first fix reference should normally be the markdown doc itself with
  `source: approved-doc`.
- Sample fix paths must be repo-root relative.
- Prefer one sample per repo over many samples from a single repo.
- Skip examples that appear only inside fenced code blocks in markdown.

## Verification Workflow

Use a temporary store so verification does not depend on stale local DB state.

```bash
tmpdir="$(mktemp -d)"

oxigraph load \
  --location "$tmpdir" \
  --file .refactor/rules/example-rule.ttl

cat > "$tmpdir/query.rq" <<'SPARQL'
PREFIX ref: <https://synaptic.canvas/refactor/>
SELECT ?ruleId ?fixPath ?fixLine WHERE {
  ?r a ref:Rule ;
     ref:ruleId ?ruleId ;
     ref:triggeredByString "ExampleTrigger" ;
     ref:hasFix ?f .
  ?f ref:fixPath ?fixPath ;
     ref:fixLine ?fixLine .
}
ORDER BY ?fixLine
SPARQL

oxigraph query \
  --location "$tmpdir" \
  --query-file "$tmpdir/query.rq" \
  --results-format json

rm -rf "$tmpdir"
```

## Persistent Store Note

`oxigraph load` appends triples. Rewriting an existing `.ttl` file and loading it
again can create duplicate local store state. The git-tracked `.ttl` files are
the source of truth; use a temporary store for verification whenever you are
changing a rule definition.

Persistent runtime convention:

- tracked docs: `.refactor/docs/`
- tracked rules: `.refactor/rules/`
- persistent Oxigraph store: `.refactor/db/`
- temp query files and scratch stores: `.refactor/temp/`
