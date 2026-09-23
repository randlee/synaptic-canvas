# Designing a stack

Read this before cutting the first layer of a stack. It covers how to decide what goes in each layer so the stack does not need restructuring later (there is no non-interactive in-place reorder). In this model each layer is its own worktree cut from the pushed top (`recipe-cut-layer.md`); where the upstream text below says `gh stack add`, read "cut the next layer".

## Dependency chain

Stacked branches form a dependency chain: each branch builds on the one below it. Foundational changes (models, APIs, shared utilities) belong in lower branches; dependent changes (UI, consumers) belong in higher branches. If code in one layer depends on code in another, the dependency must live in the same branch or a lower one.

## Plan layers before code

Decide the layers first, then write into them:

```
main (trunk)
 └── data-models    ← shared types, database schema
  └── api-endpoints ← API routes that use the models
   └── frontend-ui  ← UI components that call the APIs
    └── integration ← tests exercising the full stack
```

This is illustrative — infer the actual topic and layer names from the task at hand, never reuse generic names literally. The failure mode to avoid is writing everything on one branch and trying to split it afterward; if a task is large enough to warrant a stack, create the stack at the start.

## Branch naming

Names are used exactly as given to `init`/`add` — nothing is prepended or transformed, and slashes are kept as part of the name (`gh stack add refactor/foo` creates a branch literally named `refactor/foo`). Prefer a shared topic prefix plus the layer's concern, e.g. `billing/schema`, `billing/api`, `billing/ui` — this keeps related branches recognizable without generic names that could belong to any stack. User and repository branch-naming conventions take precedence over this default; follow them instead. If `-m` is passed to `add` without a branch name, the name is auto-generated from the commit message in date+slug form (e.g. `03-24-add_api_routes`) — prefer naming the branch yourself.

## Staging changes deliberately

Use `git add`/`git commit` directly rather than `add -Am` as the default, to control exactly which changes land in which branch:

```bash
git add internal/models/user.go internal/models/session.go
git commit -m "Add user and session models"

gh stack add api-routes
git add internal/api/routes.go internal/api/handlers.go
git commit -m "Add user API routes"
```

Multiple commits per branch are fine — what matters is that every commit in a branch serves the same concern, and a change belonging to a different concern goes in a different branch. Note that `add <branch>` without `-Am` never touches the working tree, so uncommitted changes carry onto the new branch; commit or stash first if you want a clean start.

## When to create a new branch

Create a new branch (`gh stack add`) when starting a different concern that depends on what's already built. Signals:

- Switching from backend to frontend work
- Moving from core logic to tests or documentation
- The next changes have a different reviewer audience
- The current branch's PR is already large enough to review on its own

A layer that can't be described in one sentence is usually two layers.

## One stack, one story

Think of a stack from the reviewer's perspective: it should tell a cohesive story about a feature, and a reviewer should be able to read the PRs in sequence and understand the progression.

**Use a single stack** when every branch serves the same feature or project, even if it spans multiple concerns (models, API, frontend).

**Use a separate stack** for work that's unrelated to the current effort — a different feature, an unrelated bug fix, an independent refactor. Don't mix unrelated work into one stack just because you happen to be touching both. Start a new stack with `gh stack init`, or switch with `gh stack checkout` for each distinct effort. A trivial incidental fix (e.g. a typo you noticed) can ride along in the current stack; once it grows into its own project, it deserves its own stack.

## Field-verified

- **Cut layers on crate/module boundaries** — e.g. storage → runtime → CLI → docs — not on vertical slices that touch every module in every layer. A vertical-slice cut is what makes every layer conflict with its neighbor on rebase and forces constant merge-forwards; a module-boundary cut keeps each layer's diff isolated to the files that layer owns.
- **A re-export facade lands on the layer of its first consumer**, not on the frozen-types layer below it. Putting a facade on the types layer just because it re-exports types creates a false dependency and drags unrelated consumer churn into that PR.
- **Treat a blown budget as a signal to stop and re-cut, not push through.** A stack planned at N layers that reaches 2N with nothing merged, or any single layer that needs a third fix round, has failed its plan — stop appending new layers and restructure (`unstack` + re-`init`) instead of continuing to pile on.
- **Small fixes don't need a stack.** One owner, well under a few hundred lines, fix and its tests together — that's one ordinary PR off trunk, no stack at all.
