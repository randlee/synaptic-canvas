# Opus review: reviewed recommendations and fix assignments

Reviewed head: `a519358261282ef5fced298c7d491325f83f8421`.
Baseline: `fc702b179f16911bad719dd0253d75c34ad16355`.
Review: Claude Opus 5.5, session `15509b09-48c5-435a-b06b-7fe427c2669e`.

The user requested parallel recommendation passes, parent review, then assigned
fixes. Three background agents independently checked the transport, local-state,
and cache/CLI clusters without editing source. The parent reviewed their
evidence and approved the changes below before assigning implementation.
This record does not change the locked intent, anchors, recipe strategies,
or authorization requirements.

## Approved corrections

| ID | Confirmed issue | Reviewed correction and evidence required |
|---|---|---|
| OF-001 | Partial GraphQL errors discard good data and later batches | Preserve unaffected aliases/fields; error-produced null CI is unknown, not NONE; authentication/throttling still stop globally. Test partial first batch followed by later batches and warm reuse. |
| OF-002 | HTTP 304 with nonzero gh exit stops later reads | Accept only valid conditional reuse of the matching endpoint's cached body. Installed gh 2.98.0 returned exit 1 against a loopback-only 304 server; no GitHub request was made. Test later reads and pagination, missing validators, and auth failures. |
| OF-003 | Ordinary branch text can trigger shared throttling | Classify error messages/types and HTTP headers, not successful data fields. Test secondary/rate_limit/abuse branch names and real throttle signals. |
| OF-004 | Persisted monotonic completion values survive reboot | Use per-scope completion revisions for coalescing; keep monotonic clocks only for in-process deadlines and wall time for TTLs. Test reboot simulation and concurrent forced readers. |
| OF-005 | Five-second pressure wait abandons remaining acquisition time | Wait only within the shared acquisition deadline while retaining serialized requests and pacing. Test contention, real expiry, and cooldown propagation. |
| OF-006 | Stale origin heads repeatedly invalidate fresh hosted observations | Only positively fresh per-ref git observations may provide expected hosted SHAs. Preserve strict matching and new-head invalidation for qualified heads. Test stale/fresh siblings, warm clients, failed fetches, and duplicate chain acquisition. |
| OF-007 | Proven remote absence becomes unactionable unknown | Timestamp successful negative advertisements; qualify absence separately for 60 seconds, never qualify an old tracking SHA. Report an unpushed problem only for confirmed absence; transport failures remain unknown. |
| OF-008 | SSH aliases/undotted hosts break hosted identity and local verdicts | Canonicalize SSH remotes locally with bounded SSH configuration inspection; accept valid undotted hosts. Hosted identity warnings do not become structural catalog failures. No hosted discovery probe. |
| OF-009 | LANDING can be green over stale/local-only refs | Require fresh positive pushed refs for trunk and active-layer containment; keep raw local conflict predictions separate. Never use local-head fallback as pushed-head evidence. |
| OF-010 | REST-discovered bottom with unknown recorded base gets a false rebase order | Keep missing recorded state unknown; distinguish moved-trunk ancestry from upper-layer chain errors and actual conflicts. Label local computations accurately. |
| OF-011 | Broad/trunk reports abort on unrelated refs/worktree HEAD changes | Compare query-aware semantic epochs with dynamic eligible membership, relevant compositions/refs/diagnostics, and repository identity. New stacks and conflicts must still invalidate a changed query. |
| OF-012 | Missing/prunable checkouts poison unrelated scopes | Inspect validated Git worktree administration directories for legacy catalogs; separate checkout availability from attributable catalog damage. Never prune automatically or hide conflicting catalogs. |
| OF-013 | Numeric selectors collide and Unicode digit parsing raises internal errors | Add ASCII positive-number parsing and explicit branch/number/PR selectors; validate before acquisition. Preserve existing unambiguous bare-number semantics and typed errors. |
| OF-014 | Structural refresh can fail only after avoidable earlier API reads | Preflight all selected numeric stack identities before any structural acquisition; refuse incomplete scope explicitly rather than silently skipping it. |
| OF-015 | Baseline test depends on full repository history | Check in the unchanged historical source fixture with provenance/digest; preserve the 120-layer offline comparison without fetching history. |
| OF-016 | Long refspec argv risks Windows process limits | Send selected fetch refspecs through Git's supported stdin transport; bound advertisement pattern batches under the existing total deadline. Test 120 long branch names, not 500 layers. |

Implementation ownership is disjoint: one agent owns the remote adapter and its
transport/git tests; one owns local discovery/view and their tests; one owns
chain handling, shared selector helpers, and the historical fixture. The parent
owns integration, the subprocess input seam, documentation, verification, and
the new stack layer. Agents do not commit, push, or call GitHub independently.

## Non-blocking observations and rejected claims

- Merge-semantics scans repeated per stack are a local performance concern.
  Share a qualified epoch per report and revalidate it if the optimization can
  preserve config/attribute/index/environment invalidation; otherwise document
  the limitation rather than weakening correctness.
- `merge-tree --write-tree` can create Git objects. Reporting does not mutate
  refs, the index, or worktree files; it is not a promise of zero object writes.
  No cleanup of user objects is authorized.
- This repository already ignores `.sc/`. Cache placement may need explicit
  ignore configuration in consuming repositories; reporting must not edit a
  consumer's ignore files as an incidental "fix".
- Arbitrary three-segment enterprise clone paths were not established as a
  supported GitHub URL form. Do not guess a host/repository by stripping paths.
- `--no-pr` is a strict no-API option, not proof that PRs do not exist. Unknown
  hosted evidence must not produce LINKABLE; sufficiently fresh cached evidence
  can already support the verdict. Keep that contract.
- The review's claim that both packages are 0.1.1 was incorrect:
  `sc-git-worktree` is 0.14.0. No package release was requested in this fix round.
- The review's claim of no 100+ layer coverage was too broad: 120-layer local
  and fake-transport fixtures exist. Real large-stack GitHub integration was
  deliberately not exercised because of the user's quota constraint.

## Verification boundary

All OF-001 through OF-016 corrections were implemented after recommendation
review. Cross-review also found and closed two additional regressions:

- An explicit empty `--stack ''` could expand to an unscoped acquisition.
  Both entrypoints now reject it before local discovery or hosted acquisition.
- A forced refresh unable to acquire its lock could leave old cached green
  fields fresh. An invocation-local error overlay now de-qualifies those fields
  without writing shared cache state without a lock. A genuinely completed
  coalesced refresh remains reusable.

The parent reviewed the integrated diff, and each agent independently reviewed
another agent's cluster. No confirmed medium/high findings remain after the
corrections above. The repeated local merge-epoch scan remains a documented,
non-blocking performance limitation, not an API-quota regression.

Final local verification (2026-10-17):

- `python3 -m pytest packages/sc-gh-stack/tests packages/sc-git-worktree/tests -q`:
  **580 passed in 53.41 seconds**, including the final lock/deadline regressions.
- All five scripts compile; `git diff --check` passes.
- Manifest artifact validation passes; frontmatter validation passes (98 files).
- A fresh temporary package installation succeeds; both installed entrypoints
  load and return `--help` successfully. No user installation was changed.

No live GitHub API test, new HTTP client, recipe redesign, or 500-layer test is
part of these assignments. Historical anchor-gate results remain historical;
they are not a rerun against this follow-up.

Public contract changes are additive explicit selector forms, typed selector
errors, qualified negative-ref provenance, and pushed/absence row fields. Bare
ASCII numbers retain their documented stack-number/PR-number meanings; numeric
branch names require explicit selection and a qualified PR mapping before a
safe link command can be generated. LANDING is intentionally unknown rather
than green when pushed-ref evidence is stale or missing. Documentation updates
followed skill-creator guidance to keep these conditions close to usage; recipe
strategies and authorization rules were not changed.
