# sc-gh-stack

Stacked-PR workflow skill for Synaptic Canvas, built on GitHub's `gh stack`
extension. Replaces the upstream `github/gh-stack` skill (a command inventory)
with a use-case router: SKILL.md holds the model, hard rules, and a
situation → playbook table; each playbook is a worked example with the expected
`gh stack view --json` state after every step.

## Skill

### managing-gh-stacks
Verify `gh` + `gh-stack` + `git`, run the read-only preflight, then follow one
playbook:

| Situation | Route |
|---|---|
| N existing PRs against trunk → one stack | `references/playbook-convert.md` (worked example) + `scripts/gh_stack_convert.py` |
| New multi-part work | upstream `stack-design.md` + `commands.md` |
| Fix a lower layer / sync after trunk moves | upstream `commands.md` + `troubleshooting.md` |
| Land the stack in one CI cycle | `gh stack merge <stack#> --yes` (upstream `commands.md`) |
| Sprint dependency graph → stacks | mapping rules in SKILL.md |

Only the convert case has a dedicated worked-example playbook in 0.1.0; further playbooks are
tracked in the CHANGELOG.

Upstream `commands.md`, `troubleshooting.md`, and `stack-design.md` ship verbatim
as deep references and are loaded only when a playbook points to them.

## Scripts

Stdlib-only Python 3; every run emits one fenced JSON envelope (`success`/`data`/`error`).

- `scripts/gh_stack_preflight.py` — read-only environment gate (gh, extension,
  auth, rerere, remotes, clean tree, no rebase in progress); each failed check
  carries its fix. Exit 0/1.
- `scripts/gh_stack_convert.py <trunk> <b1> … <bN>` — chains existing branches
  bottom-up with `git rebase --onto`, stops at the first conflict (exit 3,
  `data.conflict` names layer and files), is idempotent on re-run, then adopts
  the chain with `gh stack init`. Exit 5 on bad input.
- `scripts/gh_stack_shared.py` — git/gh wrappers and the envelope.

## Tests

```bash
python3 -m pytest packages/sc-gh-stack/tests
```

Unit tests mock `git`/`gh`; one integration test drives real `git` in a temp repo
(conflict → resume → linear chain) with a stubbed `gh` on PATH.

## Why stacks

Merging n independent PRs sequentially costs n(n+1)/2 CI runs because every
remaining branch must re-run after each merge. A stack costs n runs and lands
atomically with `gh stack merge`.

## Requirements

- `gh` (authenticated) with the `gh-stack` extension
- `git >= 2.23`, `python3 >= 3.9`
- Stacked pull requests enabled on the GitHub repository (`submit` exits 9 otherwise)

## Storage

Installs into `.claude/` only. No runtime state. `gh_stack_convert.py` sets
`rerere.enabled=true` in the target repo's local git config.
