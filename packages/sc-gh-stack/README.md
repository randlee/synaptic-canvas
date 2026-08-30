# sc-gh-stack

Stacked-PR **orchestration** for Synaptic Canvas, built on GitHub's `gh stack`
extension. Three background agents do the work in isolated worktrees and return
compact decision logs; deterministic stdlib-Python scripts underneath guarantee
the unhappy path is forensic (exact failing command, stderr, per-branch state,
one recovery action) and the happy path is minimal.

## Skill

### managing-gh-stacks
Verify `gh` + `gh-stack` + `git` + `python3`, then orchestrate:

| Situation | Route |
|---|---|
| Task dependency graph → parallel dev plan | `sc-stack-plan` agent → stacks + worktree plan (`references/playbook-graph-to-stacks.md`) |
| N flat PRs against trunk → one stack | `sc-stack-convert` agent in a dedicated worktree (`references/playbook-convert.md`) |
| Trunk moved / fix merged mid-stack | `sc-stack-sync` agent (`references/playbook-sync.md`) |
| GitHub reports a rebase needed | believe it — `references/playbook-rebase.md` |
| Land the stack in one CI cycle | `gh stack merge --yes` after the membership check (`references/playbook-merge.md`) |

Upstream `commands.md`, `troubleshooting.md`, and `stack-design.md` ship verbatim
as deep references and are loaded only when a playbook points to them.

## Agents

Invoked by the skill via the Task tool (`run_in_background: true`), one per stack:

- `sc-stack-plan` — read-only: dependency graph → stacks optimized for
  parallelism + exact worktree creation commands; ambiguous order comes back as
  questions, never guesses.
- `sc-stack-convert` — chains flat PRs bottom-up in `<repo>-worktrees/stack/<bottom>`,
  resolves **trivial** conflicts (reported as low-risk decisions), surfaces
  **risky** ones paused in the worktree for review, pushes via
  `gh stack submit --auto` only when fully clean.
- `sc-stack-sync` — post-merge/mid-stack-fix rebase via `gh stack sync`
  (all-or-nothing: conflicts restore every branch), same conflict rubric,
  verifies layers above a fix contain it.

Convert and sync report with the Standard envelope (`canceled`/`aborted_by`/
`metadata`): every report carries per-branch `before`/`after` SHAs and a
`pushed` flag, and a risky-conflict stop comes back as `canceled: true,
aborted_by: "policy"` (`*_RISKY` error codes) — a hold for review, not a failure.

## Scripts

Stdlib-only Python 3; every run emits one fenced JSON envelope (`success`/`data`/`error`).

- `scripts/gh_stack_preflight.py` — read-only environment gate; each failed
  check carries its fix. Exit 0/1.
- `scripts/gh_stack_convert.py <trunk> <b1> … <bN>` — chains existing branches
  bottom-up with `git rebase --onto`, stops at the first conflict (exit 3),
  idempotent on re-run; refuses dirty trees, in-progress rebases, and diverged
  branches; fast-forwards branches merely behind; linearises trunk-merge
  layers; then `gh stack init`. Exit 5 on bad input or refused state.
  `--dry-run` (alias `--validate`) previews the per-layer plan, mutating nothing.
- `scripts/gh_stack_sync.py` — wraps `gh stack sync` with the same guards and
  envelope; exit 3 on conflict (all branches restored).
- `scripts/gh_stack_shared.py` — git/gh wrappers and the envelope.

## Tests

```bash
python3 -m pytest packages/sc-gh-stack/tests
```

Unit tests mock `git`/`gh`; the integration tests drive real `git` in temp repos
(conflict → resume, abort → re-run, dependent layers, divergence guards) with a
stubbed `gh` on PATH.

## Why stacks

Merging n independent PRs sequentially costs n(n+1)/2 CI runs because every
remaining branch must re-run after each merge. A stack costs n runs and lands
atomically with `gh stack merge`.

## Requirements

- `gh` (authenticated) with the `gh-stack` extension
- `git >= 2.23`, `python3 >= 3.9`
- Stacked pull requests enabled on the GitHub repository (`submit` exits 9 otherwise)

## Storage

Installs into `.claude/` only. No runtime state under `.claude/`. Stack work
runs in per-stack worktrees (`<repo>-worktrees/stack/<bottom>`); gh-stack
tracking state is per-worktree, so parallel stacks never interfere.
`gh_stack_convert.py` sets `rerere.enabled=true` in the target repo's local git
config and keeps per-conversion bookkeeping in the target repo
(`refs/sc-gh-stack/orig/*` pre-rebase tips and the `sc-gh-stack.conversion`
config key), cleared when a different conversion starts.

## Security

This package invokes local `git` and authenticated `gh` commands that can
rebase, push, and merge branches. Use it only in trusted repositories, review
the stack plan and target branches before execution, use least-privilege GitHub
credentials, and never include secrets in prompts, branch metadata, or reports.
