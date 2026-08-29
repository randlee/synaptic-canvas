---
name: managing-gh-stacks
version: 0.2.0
description: >
  Orchestrate parallel development with stacked PRs via the `gh stack` CLI
  extension and background agents. Use whenever the user mentions a stack,
  stacked PRs, dependent PRs, branch layers, gh stack, or wants to: map a task
  dependency graph onto stacks and worktrees, convert several existing PRs into
  one stack, keep a stack cleanly rebased as fixes merge into middle layers, or
  land a whole stack in one CI cycle. Also use when GitHub refuses a normal
  merge because a PR is "part of a stack" — the answer is `gh stack merge`,
  never retrying `gh pr merge` or hand-rolling REST calls. Read this before
  running any `gh stack` command — the tool is new, blocks under a PTY, and
  cannot be driven from prior knowledge.
---

# Managing gh Stacks

## Scope

This skill orchestrates three workflows, each delegated to a background agent:

1. **Plan**: a sprint/task dependency graph → stacks optimized for parallel development, with
   a concrete worktree plan.
2. **Convert**: N flat PRs/branches against trunk → one clean stack, every PR mergeable and
   correctly based, CI running on every layer.
3. **Sync**: a stack whose trunk moved or whose middle layer received a fix → cleanly rebased
   and pushed again.

Do not use this skill for single-branch PRs (use `sc-commit-push-pr`), repositories where
stacked PRs are not enabled on GitHub, or reordering layers via metadata — ancestry is
rewritten with git, never with `gh stack modify`.

## The model in five lines

- A stack is a linear chain of branches on a trunk: `(main) <- L1 <- L2 <- L3`. Left is bottom.
- Each layer's PR is based on the layer below, so a reviewer sees only that layer's diff.
- Bottom merges first. `up` = away from trunk, `down` = toward it.
- Strictly linear: one parent, at most one child. Parallel work is a *separate stack*.
- Git ancestry is the truth; stack metadata only describes it. Fix ancestry first, always.

## Step 1 — Verify `gh`, the `gh-stack` extension, and `git`

Before any stack operation:

```bash
which gh && gh --version
gh extension list | grep gh-stack
which git && git --version
which python3 && python3 --version   # scripts need >= 3.9
```

If any of them is not on PATH, probe common install locations before assuming it is absent —
Claude Code's bash may not share PATH with the interactive shell (Homebrew dirs and pyenv
shims are the usual omissions):

```bash
for cli in gh git python3; do
  command -v "$cli" >/dev/null && continue
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.pyenv/shims"; do
    [ -x "$d/$cli" ] && echo "$cli found at: $d/$cli" && break
  done
done
```

If found off-PATH, `export PATH="<dir>:$PATH"` for this session. If `gh`, the extension,
`git >= 2.23`, or `python3 >= 3.9` is missing, **read
`references/installation-and-troubleshooting.md` and stop**; do not proceed with degraded
behavior.

Run scripts from the root of the repository (or worktree) being operated on. If
`.claude/scripts/gh_stack_preflight.py` is not there, locate the installed copy
(`find .claude ~/.claude -name 'gh_stack_*.py' 2>/dev/null`) and use its path with the same
arguments. If it cannot be found, stop and tell the user the sc-gh-stack scripts are not
installed — **do not reproduce the rebase chain or preflight checks by hand.**

## Hard rules

1. Never run bare `view`, `submit`, `init`, `add`, `checkout`, `switch`, or `modify` — they
   prompt or open a TUI and block forever. Use `view --json`, `submit --auto`, `init <b>...`,
   `add <b>`, `checkout <target>`, `up/down/top/bottom`. `modify` has no non-interactive form.
2. Never `gh pr merge` a stacked PR; never `git push --force`; never `git reset --hard` as
   part of a workflow (it discards commits and rerere state — recover with `git rebase
   --abort`, `git rebase --continue`, or a fast-forward instead); never merge layers into
   each other by hand. `gh stack` owns pushing (`push`, `submit`, `sync`) and merging
   (`merge --yes`).
3. Never restructure with metadata. Rechain with `git rebase --onto`, then `unstack` + `init`
   (`references/troubleshooting.md`, "Restructuring a stack").
4. A change belongs to the layer that owns the concern: check out that layer, commit, then
   `gh stack rebase --upstack`. Never commit a lower layer's fix on the top branch.
5. Parse only `view --json` on stdout and exit codes. Never parse stderr.
6. If you have not been given layer order and it is not obvious from the diffs, ask. Do not guess.

## Worktree policy

All stack execution happens in dedicated worktrees, never in the user's checkout:

- One worktree per stack at `<repo_root>-worktrees/stack/<bottom-slug>`, where
  `<bottom-slug>` is the bottom branch name with every `/` replaced by `-`
  (`feat/schema` → `stack/feat-schema`). Both agents and callers must compute the path with
  this rule so re-invocations land in the same worktree.
- gh-stack tracking state (`.git/worktrees/<wt>/gh-stack`) is **per-worktree**, so parallel
  stacks never interfere with each other or with the main checkout.
- Worktrees are kept after agent runs — they are the review surface: any conflict an agent
  surfaces is sitting checked-out in its worktree, mid-rebase, ready to inspect and resolve.

## Agent Delegation

Delegate convert and sync via the Task tool with `run_in_background: true`; the plan agent is
read-only and fast, so it may run in the foreground. Background agents complete
asynchronously — wait for the completion notification rather than assuming a timeout (a
deliberate departure from the spec's per-task timeouts: background Task agents signal
completion themselves). Never start a second agent on the same worktree while one is
running. Cap 3–4 concurrent; one agent per stack, each invocation tagged with a
`correlation_id` (use the stack's bottom-branch slug). When running agents over several
stacks, aggregate per the spec: `{ "parallel": true, "concurrency": N, "results": [...],
"summary": { "all_successful", "failed", "succeeded" } }`, results ordered by
`correlation_id`, and surface `summary.failed` to the user — never silently drop a failed
stack:

| Situation | Agent | Input (as `<input_json>`) | Returns |
|---|---|---|---|
| Task graph → parallel dev plan | `sc-stack-plan` | tasks, trunk, repo_root | stacks + worktree creation commands + open questions |
| Flat PRs → one stack | `sc-stack-convert` | trunk, layers (bottom→top), repo_root | decision log: branches before/after/pushed, resolutions, surfaced conflicts |
| Trunk moved / mid-stack fix merged | `sc-stack-sync` | worktree, fix_branch? | decision log: same contract |
| `gh pr merge` refused: PR is "part of a stack" | none — run `gh stack merge <pr#> --yes` | — | merges that PR and every unmerged PR below it, atomically; PRs above retarget automatically. Never hand-roll REST calls. (GitHub's web UI stack merge is the same native flow — fine for humans, not agent-drivable.) |

Inputs travel as a tagged JSON block inside the Task prompt — the agent's `## Inputs`
section is the field contract:

```
Follow your agent instructions with these inputs:
<input_json>
{ "trunk": "main", "layers": ["101", "102"], "repo_root": "/path/repo" }
</input_json>
```

Read `references/playbook-graph-to-stacks.md`, `references/playbook-convert.md`, or
`references/playbook-sync.md` first — each is a worked example including the agent prompt and
the expected report. Simple one-command situations (land a green stack:
`gh stack merge --yes`; inspect: `gh stack view --json`) need no agent.

### Conflict rubric (used by convert and sync agents)

- **Trivial — agent resolves, reports as a low-risk decision** with file, layers, kind, and a
  one-sentence summary so the caller never needs to investigate: rerere already staged it;
  interleaved pure additions (imports, registry/list entries, changelog lines); identical
  change on both sides; whitespace/format-only overlap.
- **Risky — agent stops and surfaces**: overlapping semantic edits, delete-vs-modify, binary
  files, anything not explainable in one sentence. The rebase stays paused in the worktree;
  the report names the file, the owning layer, the worktree path, why it is risky, and a
  suggested resolution.

### Report and state contract (what every agent/script must guarantee)

- **Success = minimal decision log**: stack shape, per-branch `before`/`after` SHA and
  `pushed` flag, resolutions made, next step. Nothing else.
- **Failure = forensic**: the exact command that failed, its stderr, per-branch state, and
  one concrete recovery action — replaying the tool calls must show what happened without
  further investigation.
- **Envelope levels**: convert and sync agents use the Standard envelope (`canceled`,
  `aborted_by`, `metadata.duration_ms`/`tool_calls`/`retry_count` added); a risky-conflict
  stop is `canceled: true, aborted_by: "policy"` with error code `*_RISKY` and
  `recoverable: false` — a deliberate hold for human review, not an operation failure. The
  plan agent and the scripts use the Basic envelope.
- **Validation surface**: `gh_stack_preflight.py` (environment) plus
  `gh_stack_convert.py --dry-run` (per-layer plan preview, nothing mutated) are this
  package's `--validate` mode; `--auto-fix` is deliberately absent — its bounded-fix role is
  filled by the trivial-conflict rubric above.
- **State guarantees**: scripts never push, never force, never delete refs; conversion stops
  at the first conflict with finished layers skipped on re-run; `gh stack sync` restores
  every branch on conflict (all-or-nothing); agents push only via `gh stack submit --auto` /
  `sync`, and only when the chain completed with zero risky conflicts. Push state is reported
  per branch, every time.

## Output Expectations

When using this skill, report to the user:

- which playbook/agent ran and the stack shape as `(trunk) <- L1 <- … <- Ln`
- per-branch pushed state and the final `gh stack view --json` summary (branches,
  `needsRebase`, PR states)
- every trivial resolution made (from the agent's `resolutions`) and every surfaced conflict
  with its worktree path
- which commands were not run and why (e.g. exit 9 — stacked PRs not enabled)
- for planning: the stacks as ordered branch lists, the worktree plan, and any serialization
  decisions or open questions at fan-in/fan-out points

## Deep references (load only when a playbook points to them)

- `references/playbook-graph-to-stacks.md` — plan a graph onto stacks + worktrees (worked example)
- `references/playbook-convert.md` — flat PRs → stack (worked example, agent + manual path)
- `references/playbook-sync.md` — rebase after trunk/middle-layer changes (worked example)
- `references/commands.md` — preconditions, atomicity, side effects per command (upstream, verbatim)
- `references/troubleshooting.md` — conflicts, squash merges, divergence, restructuring, exit codes (upstream, verbatim)
- `references/stack-design.md` — choosing layers and names for new work (upstream, verbatim)
- `references/installation-and-troubleshooting.md` — CLI install, PATH, version floors
- `.claude/scripts/gh_stack_preflight.py`, `gh_stack_convert.py`, `gh_stack_sync.py` — `--help` for usage and exit codes

`gh stack <command> --help` is authoritative for flags. `gh stack help <command>` does not work.
Where an upstream reference says the `view --json` schema "is in SKILL.md", the authoritative
shape is the example in `references/playbook-convert.md` plus `gh stack view --help`.

## Storage

This skill runs `git` and `gh stack` in the target repository and its stack worktrees only.
It writes no state under `.claude/`. `gh_stack_convert.py` sets `rerere.enabled=true` and
`rerere.autoUpdate=true` in the local git config so conflict resolutions replay — and are
staged — on later rebases, and keeps two pieces of
bookkeeping in the target repo: each layer's pre-rebase tip under `refs/sc-gh-stack/orig/`,
and the conversion's identity in the local git config key `sc-gh-stack.conversion`. Both
persist until a conversion with a different trunk/layer list starts, which clears them; they
are what makes re-runs idempotent. Scripts are stdlib-only Python 3 and emit fenced JSON
(`success`/`data`/`error`); parse that, never their stderr.
