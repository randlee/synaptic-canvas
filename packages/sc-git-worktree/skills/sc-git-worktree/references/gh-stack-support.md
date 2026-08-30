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
   lives in ONE worktree at `<repo>-worktrees/stack/<bottom-slug>` (bottom branch
   name, `/` → `-`) — not one worktree per layer. Layers within a stack are
   sequential by construction and share the stack's worktree. Record such
   worktrees in tracking with the stack shape in the purpose field.
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
