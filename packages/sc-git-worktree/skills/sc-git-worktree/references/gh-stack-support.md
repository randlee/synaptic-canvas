# gh-stack support (optional)

Two independent gates — do not conflate them:

- **Stack operations** (creating, rebasing, submitting, landing stacks) apply only
  when the `gh-stack` extension is installed:

  ```bash
  gh extension list | grep -q gh-stack && echo "gh-stack installed"
  ```

- **The destructive-safety rules in "Interop rules" below apply UNCONDITIONALLY.**
  gh-stack tracking is repository state, not local toolchain: a worktree can carry
  a teammate's stack tracking on a machine where the extension was never
  installed. The probe costs one `test -e` and needs no `gh` at all.

## Authority: defer to sc-gh-stack

**This file is not an authority on stacked PRs.** The `managing-gh-stacks` skill
(package `sc-gh-stack`) is. Check for it:

```bash
ls .claude/skills/managing-gh-stacks/SKILL.md 2>/dev/null \
  || ls ~/.claude/skills/managing-gh-stacks/SKILL.md 2>/dev/null \
  || find ~/.claude .claude -path '*managing-gh-stacks/SKILL.md' -print -quit 2>/dev/null
```

- **Installed** → for anything stack-related (creating stack worktrees, converting
  flat PRs, rebasing, landing), use that skill and follow its conventions. This
  skill only supplies the generic worktree lifecycle underneath it.
- **Not installed** → **highly recommend the user install it** before doing stack
  work — it carries the playbooks, background agents, conflict rubric, and the
  failure modes learned from real incidents:

  ```bash
  /plugin marketplace add randlee/synaptic-canvas   # once per machine
  /plugin install sc-gh-stack@synaptic-canvas
  ```

  Until then, apply only the minimal rules below; do not improvise stack
  operations beyond them.

## Interop rules (unconditional — what THIS skill must respect around stacks)

1. **Stack worktrees follow sc-gh-stack's convention, not this skill's.** A stack
   lives in ONE worktree — for a stack CREATE started here, at the SAME path a
   flat worktree would use (`<repo>-worktrees/<branch>`, no `stack/` prefix) —
   not one worktree per layer. Layers within a stack are sequential by
   construction and share the stack's worktree: creating a new layer never
   creates a new worktree, it checks out the new branch inside the existing
   one. Record such worktrees in tracking with the stack shape in the purpose
   field.
2. **gh-stack tracking state is per-worktree** (`.git/worktrees/<wt>/gh-stack`).
   Deleting a worktree deletes its stack tracking. Therefore:
   - The scan and cleanup scripts report `gh_stack_tracked` per worktree, and
     **batch cleanup automatically skips any worktree carrying gh-stack
     tracking** (surfaced in the report as skipped). Removing one requires a
     single-branch cleanup with explicit user approval naming the stack; a
     merged, fully-landed stack's worktree is safe to clean.
3. **Branch deletion**: trunk ancestry is not stack truth. A bottom layer can be
   genuinely merged while the layers above it are open — and its worktree holds
   the tracking for all of them; deleting the branch or worktree orphans the
   still-open PRs above. Confirm with `gh stack view --json` before deleting any
   branch in a worktree that carries gh-stack tracking; when in doubt, keep it.
4. **Never** `gh pr merge` a stacked PR, never force-push or `git reset --hard`
   stack branches from a worktree operation — `gh stack` owns pushing and merging.
5. **Create is a factory: every request resolves to exactly one product** - A
   (flat worktree), B (a new stack), or C (a layer added to an existing
   stack). Precedence is **Intent > Dependency > Policy > default A**,
   evaluated lazily (see DESIGN.md "Worktree factory decision model" in the
   sc-git-worktree package for the full decision function):
   - **Intent**: explicit `flat: true` always wins → product A, nothing else
     is evaluated. Never pass it merely to silence a refusal without that
     judgment call.
   - **Stack-activity gate**: a repo that is not stack-active (no
     `git.always_stack`, and no worktree anywhere carries gh-stack tracking)
     never evaluates dependency or policy at all - every create is product A.
     This is the **positive-signal rule** and the **auto-upgrade for legacy
     prompts**: existing "create a worktree off develop"-style prompts are
     completely unaffected until the repo actually starts using stacks.
   - **Dependency** (stack-active repos only): work based on trunk (a
     protected/merged branch) is independent - a flat worktree (or, under
     `always_stack`, product B) is correct regardless of where the request
     came from. Work based on an **unmerged branch** depends on unmerged
     work - that is the definition of a stack layer:
     - **Base is a layer of an existing tracked stack** → product **C**: NO
       new worktree. The new branch is checked out in that stack's own
       worktree and adopted with `gh stack add` (with sc-gh-stack installed,
       use its skill for anything beyond the checkout itself).
     - **Base is an untracked unmerged branch** (no gh-stack tracking
       anywhere for it) → refused with `CREATE.NEEDS_STACK`: creating one is
       a strictly bigger operation (a new 2-layer stack) than `create`
       performs. The refusal names the exact `gh stack init --base
       <trunk-of-base> <base> <new-branch>` command and points at the
       managing-gh-stacks skill for the full workflow.
     - **Base's stack worktree has a rebase in progress** → also refused with
       `CREATE.NEEDS_STACK`; resolve the rebase first.
     - **Base genuinely independent despite being unmerged** (rare — e.g. a
       long-lived integration branch; explicit user intent only) → pass the
       explicit `flat: true` override.
     Fail direction: a squash-merged base can look unmerged to ancestry
     checks - the refusal errs toward stacking, and the override exists for
     the human call.

6. **Repo policy: `always_stack`** (one of the two stack-activity signals).
   A repo can declare stacking the norm in its checked-in
   `.sc/shared-settings.yaml`:

   ```yaml
   git:
     always_stack: true
     stack_root: develop   # optional; default: develop if it exists, else the default branch
   ```

   When set (or when any worktree already carries gh-stack tracking - either
   signal makes the repo stack-active), **the create script enforces
   prerequisites for every collaborator** before resolving dependency at all:
   missing `gh`, the `gh-stack` extension, or the sc-gh-stack skill refuses
   with `CREATE.STACK_PREREQS_MISSING` listing the exact installs - this is
   the mandatory collaborator gate and the only refusal that fires before
   product resolution, and it runs before any mutation (including `git
   fetch`). Scan surfaces `always_stack` / `stack_prereqs_ok` in its summary.

   With prerequisites satisfied, an independent base (protected or merged
   into trunk) resolves to product **B**: identical to a flat worktree - same
   path, no `stack/` prefix anywhere - plus `git config rerere.enabled true`
   and `gh stack init --base <stack_root> <branch>` in that same worktree. A
   stack-from-birth is nearly free (local tracking only until submit) while
   retrofitting flat branches into a stack is a full conversion - that
   asymmetry is why the default errs stacked when the policy is on.
   `flat: true` remains the explicit escape (Intent still wins over Policy).

## Minimal command reference (fallback when sc-gh-stack is absent)

**This table is a survival kit for reading and landing an existing stack, not a
substitute for the skill. Do not use it to create or restructure a stack —
install sc-gh-stack first.** Non-interactive forms only — bare
`view`/`submit`/`init`/`checkout` prompt or open a TUI:

| Task | Command |
|---|---|
| Inspect the stack (machine-readable) | `gh stack view --json` |
| Open/update PRs for every layer | `gh stack submit --auto` |
| Rebase + push after trunk moved / layer merged | `gh stack sync` (conflict: all branches restored, exit 3) |
| Rebase from current layer upward | `gh stack rebase --upstack` |
| Land PR N and every tracked PR below it | `gh stack merge <pr#> --squash --yes` — verify membership in `view --json` FIRST; all-or-nothing, and a merge queue on the base branch overrides the method flag |

These four incidents repeat in the field; the sc-gh-stack skill exists to prevent
them: merging a subset because a PR was never linked into the stack (always check
`view --json` before `merge`); denying a rebase that `needsRebase: true` reported
(believe the report); rebasing when the drift is a merge-forward situation; and
falling back to `gh pr merge --admin` or raw REST when the stack path fails.
