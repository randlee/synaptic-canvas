# Recipe evidence substitutions

These substitutions change acquisition, not stacking strategy, ownership or
authorization. Reuse observations only when scope, exact heads, completeness
and freshness answer the operation. Unknown evidence never authorizes success.

| Recipe / original goal | Replacement evidence/action | Success and challenging-condition recovery preserved |
|---|---|---|
| Cut: status plus fetch establishes the pushed top containing every lower head | Reuse exact current remote refs and ancestry; fetch relevant refs once if stale | Cut from the pushed top with `--no-track`; missing ancestry stops the cut; siblings merge forward |
| Link/restack: repeated before/after/finish reports establish ordered bases and heads | Reuse mutation responses, then scoped helper JSON for missing affected facts | Full ordered link with explicit trunk; inspect every affected base; stale tracking imports remain available; frozen layers stay frozen |
| Scoped collapse: extension view supplies complete membership to avoid sweeping an empty upper layer | Sufficient verified remote composition or scoped `--refresh`; inspect upper commits | Bottom must be green independently; red-with-fix-above is removed first; changed child head is fetched and tree-checked before reset |
| Tracking recovery: per-worktree extension views find stale lists | Read common/legacy catalogs locally; inspect source/conflict diagnostics | Clear only stale local tracking, then checkout/import the actual stack; never sync stale heads over another writer |
| Land: full status and recent-merged list verify exact target and outcome | Reuse sufficient head/CI/QA evidence and executor preflight; verify affected range and known in-flight PRs | One atomic merge, expected full SHA, frozen trunk and server policy enforcement; out-of-date/nonlinear stacks use existing fallbacks, never frozen-layer rewrites |
| Async fallback: repeated reads wait for merge | Poll only returned operation UUID with backoff/deadline | Terminal success verifies outcome; failure/auth/throttle stops; deadline reports outstanding operation without resubmitting |

Local content conflicts are evaluated for every intended layer pair and the
top/trunk pair. A clean top/trunk result cannot hide an intermediate conflict
or unknown, and never substitutes for hosted checks, reviews or policy.

## Compact verified composition and top

Reuse sufficient verified complete composition; do not refresh as a ritual.
When missing, scope `--refresh` to the known stack number or a branch whose
local catalog records that number. Ordinary local JSON and `--refresh-status`
cannot certify remote membership. Keep full JSON in the shell and emit only
the needed fields; never infer the top from summary row order:

```bash
stack_status=0
snapshot=$(python3 .claude/scripts/gh_stack_view.py --stack <stack#> --refresh --json) || stack_status=$?
if [ "$stack_status" -le 1 ]; then
  printf '%s\n' "$snapshot" | jq -e '
    select(.success == true and (.stacks | length) == 1 and .git_observation.fresh == true)
    | .stacks[0]
    | select(.structure_observation.complete == true and .structure_observation.freshness == "fresh")
    | select(all(.branches[]; .isMerged == true or .pr.state == "MERGED" or .pr.state == "OPEN" or .pr.state == "CLOSED"))
    | . as $stack
    | [.branches[] | select(.isMerged != true and .pr.state == "OPEN")] as $active
    | select(($active | length) > 0)
    | $active[-1].name as $top
    | {number, trunk, branches: [.branches[] | {name, head, base, isMerged, pr}],
       top: ([$stack.rows[] | select(.branch == $top) | {name: .branch, head: .origin}][0])}
    | select((.top.name | type) == "string" and (.top.name | length) > 0)
    | select((.top.head | type) == "string")
    | select(.top.head | test("^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$"))'
else
  printf '%s\n' 'Stack observation refused; stop and inspect helper diagnostics.' >&2
  false
fi
```

Helper exit 1 permits inspection of a report containing problems, not a merge
or cut; exit 2+ stops. Stop if the projection fails or emits nothing. Unknown
structure, lifecycle, ref freshness or pushed top head never becomes success.
This projection is not authorization: inspect every upper layer before a
scoped merge and retain the recipe's QA/CI, pushed-head and ancestry checks.
