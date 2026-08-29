---
name: managing-gh-stacks
version: 0.1.0
description: >
  Use-case playbooks for stacked branches and PRs with the `gh stack` CLI
  extension. Use whenever the user mentions a stack, stacked PRs, dependent PRs,
  branch layers, gh stack, or wants to: convert several existing PRs into one
  stack, start multi-part work as a stack, fix a lower layer, sync or rebase a
  stack, land a whole stack in one CI cycle, or map a sprint dependency graph
  onto stacks. Read this before running any `gh stack` command — the tool is
  new, blocks under a PTY, and cannot be driven from prior knowledge.
---

# Managing gh Stacks

## Scope

Use this skill for:
- converting N parallel PRs/branches against trunk into one stack
- starting new multi-part work as a stack
- editing a lower layer and propagating the change upstack
- syncing a stack after trunk moves or a layer merges
- landing a complete stack atomically
- mapping a sprint dependency graph onto one or more stacks

Do not use this skill for:
- single-branch PRs (use `sc-commit-push-pr`)
- repositories where stacked PRs are not enabled on GitHub
- reordering layers via metadata — ancestry is rewritten with git, never with `gh stack modify`

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

If `gh` is not on PATH, probe common install locations before assuming it is absent —
Claude Code's bash may not share PATH with the interactive shell:

```bash
for p in "/opt/homebrew/bin/gh" "/usr/local/bin/gh" "$HOME/.local/bin/gh"; do
  [ -x "$p" ] && echo "Found at: $p" && break
done
```

If found off-PATH, `export PATH="<dir>:$PATH"` for this session. If `gh`, the extension,
`git >= 2.23`, or `python3 >= 3.9` is missing, **read
`references/installation-and-troubleshooting.md` and stop**; do not proceed with degraded
behavior.

Then run the environment gate. It is read-only and returns fenced JSON with a `fix` for every
failed check:

```bash
python3 .claude/scripts/gh_stack_preflight.py    # exit 0 = go; data.failed lists what to fix
```

Run scripts from the root of the repository being converted. If
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

## Step 2 — Pick the playbook

| Situation | Read | Then |
|---|---|---|
| N existing PRs/branches against trunk → one stack | `references/playbook-convert.md` | `python3 .claude/scripts/gh_stack_convert.py main b1 … bN` |
| Starting new multi-part work | `references/stack-design.md`, then `references/commands.md` ("init", "add", "submit") | `gh stack init` before writing code |
| Lower layer needs a fix / review changes | `references/commands.md` ("rebase", "push") | checkout owner → commit → `rebase --upstack` → `push` |
| Trunk moved, a layer merged, stack is stale | `references/commands.md` ("sync"); `references/troubleshooting.md` on conflict | `gh stack sync` → `view --json` |
| Land the whole stack in one CI cycle | `references/commands.md` ("merge") | `gh stack merge --yes` on the current stack (or pass a PR/stack number) |
| Sprint plan has a dependency graph | Graph mapping rules below | emit ordered branch lists per stack |
| Command returned non-zero | `references/troubleshooting.md` (per-code sections) and the failing command's section in `references/commands.md` | recover, re-run the same command |

Dedicated worked-example playbooks exist only for the convert case in this version; the other rows
route to the upstream references until their playbooks ship (see CHANGELOG).

### Graph → stacks mapping rules

Sprint planning owns the dependency graph; this skill owns the mapping. Because a stack is strictly
linear and its only allowed external dependency is trunk:
- a dependency chain → one stack, dependency order bottom-up
- fan-in (C needs A and B) → serialize A, B below C in one stack; no other option
- fan-out (A needed by B and C) → either serialize B, C above A in one stack, or hold C until A
  merges to trunk and start C as its own stack — choose by whether B and C need parallel QA
- independent subgraphs → separate stacks; this is where parallelism comes from

Emit each stack as an ordered branch list `(trunk) <- L1 <- … <- Ln`; that list is the exact
argument order for `gh stack init --base <trunk> L1 … Ln`.

Read exactly the reference that matches. The convert playbook is a worked example with the
expected `view --json` state after every step; compare your state to it before moving on.

## Output Expectations

When using this skill, report:
- which playbook was followed and the stack shape as `(trunk) <- L1 <- … <- Ln`
- the final `gh stack view --json` (or its summary: branches, `needsRebase`, PR states)
- every conflict encountered, the layer it belonged to, and how it was resolved
- which commands were not run and why (e.g. exit 9 — stacked PRs not enabled)
- for graph mapping: the resulting stacks as ordered branch lists and any serialization
  decisions made at fan-in/fan-out points

## Deep references (load only when a playbook points to them)

- `references/commands.md` — preconditions, atomicity, side effects per command (upstream, verbatim)
- `references/troubleshooting.md` — conflicts, squash merges, divergence, restructuring, exit codes (upstream, verbatim)
- `references/stack-design.md` — choosing layers and names for new work (upstream, verbatim)
- `references/installation-and-troubleshooting.md` — CLI install, PATH, version floors
- `.claude/scripts/gh_stack_preflight.py`, `.claude/scripts/gh_stack_convert.py` — `--help` for usage and exit codes

`gh stack <command> --help` is authoritative for flags. `gh stack help <command>` does not work.
Where an upstream reference says the `view --json` schema "is in SKILL.md", the authoritative
shape is the example in `references/playbook-convert.md` plus `gh stack view --help`.

## Storage

This skill runs `git` and `gh stack` in the current repository only. It writes no state under
`.claude/`. `gh_stack_convert.py` sets `rerere.enabled=true` in the local git config so conflict
resolutions replay on later rebases, and keeps two pieces of bookkeeping in the target repo:
each layer's pre-rebase tip under `refs/sc-gh-stack/orig/`, and the conversion's identity in
the local git config key `sc-gh-stack.conversion`. Both persist until a conversion with a
different trunk/layer list starts, which clears them; they are what makes re-runs idempotent. Both scripts are stdlib-only Python 3 and emit fenced JSON
(`success`/`data`/`error`); parse that, never their stderr.

## Agent Delegation

This skill operates directly in the main session. It does not require background agents or
Task-tool delegation: every step is either a deterministic script or a single `gh stack`
command whose `--json` output the session must inspect before choosing the next step.
