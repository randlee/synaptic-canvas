# Playbook: map a task dependency graph onto stacks and worktrees

**Situation.** Sprint planning produced a set of tasks with dependencies. You want a plan that
maximizes parallel development: which stacks exist, the exact branch order in each, and the
worktrees to create so independent lines of work never touch each other's checkout.

## Route — delegate to `sc-stack-plan`

Invoke the agent via the Agent tool (formerly Task) (read-only; safe to run without preflight):

```json
{
  "tasks": [
    { "id": "T1", "title": "db schema",        "depends_on": [],          "size": "M" },
    { "id": "T2", "title": "auth middleware",  "depends_on": [],          "size": "S" },
    { "id": "T3", "title": "api endpoints",    "depends_on": ["T1"],      "size": "L" },
    { "id": "T4", "title": "ui pages",         "depends_on": ["T3"],      "size": "M" },
    { "id": "T5", "title": "rate limiting",    "depends_on": ["T2"],      "size": "S" },
    { "id": "T6", "title": "audit log",        "depends_on": ["T1","T2"], "size": "S" }
  ],
  "trunk": "main",
  "repo_root": "/path/repo"
}
```

Expected report shape (two independent subgraphs → two parallel stacks; T6 is a fan-in and
must serialize onto one of them — the agent states which rule it applied):

```json
{
  "success": true,
  "data": {
    "stacks": [
      { "name": "schema-api-ui",
        "shape": "(main) <- feat/schema <- feat/api <- feat/ui <- feat/audit-log",
        "branches": ["feat/schema", "feat/api", "feat/ui", "feat/audit-log"],
        "tasks": ["T1", "T3", "T4", "T6"],
        "worktree": "/path/repo-worktrees/feat/schema",
        "create": ["git fetch origin",
                   "git worktree add /path/repo-worktrees/feat/schema -b feat/schema origin/main"],
        "rationale": "chain T1->T3->T4; T6 fan-in (needs T1+T2) serialized on top — see questions",
        "blocked": false },
      { "name": "auth-ratelimit",
        "shape": "(main) <- feat/auth <- feat/rate-limit",
        "branches": ["feat/auth", "feat/rate-limit"],
        "tasks": ["T2", "T5"],
        "worktree": "/path/repo-worktrees/feat/auth",
        "create": ["git worktree add /path/repo-worktrees/feat/auth -b feat/auth origin/main"],
        "rationale": "independent subgraph",
        "blocked": false }
    ],
    "parallelism": "2 stacks develop concurrently",
    "questions": ["T6 needs T2, which lives in the other stack: hold T6 until feat/auth merges to trunk, or accept cross-stack wait?"]
  },
  "error": null
}
```

## Executing the plan

1. Present `questions` to the user before creating anything — a fan-in across stacks is a
   real scheduling decision, not a default.
2. Run each stack's `create` commands. One worktree per stack; layers are created inside it
   as work reaches them: `git -C <worktree> checkout -b <layer> <layer-below>`.
3. In each worktree, adopt the stack before writing code — non-interactive forms only (bare
   `gh stack init` prompts and blocks):

   ```bash
   git -C <worktree> config rerere.enabled true
   git -C <worktree> config rerere.autoUpdate true
   gh stack init --base <trunk> <bottom>       # init checks out the LAST branch listed
   gh stack add <layer>                        # per new layer, from the current top
   ```

   (`references/stack-design.md` for layer sizing/naming; `references/commands.md`
   "init"/"add"/"submit" for preconditions.)
4. gh-stack tracking is per-worktree, so the stacks never interfere; development, CI, and
   review proceed in parallel per stack.

## Rules reference (what the agent applies)

- Independent subgraphs → separate stacks (this is where parallelism comes from).
- A dependency chain → one stack, dependency order bottom-up.
- Fan-in (C needs A and B) → serialize A, B below C in one stack; no other option.
- Fan-out (A needed by B and C) → serialize B, C above A when they need parallel QA against
  each other; otherwise hold C until A merges to trunk and start C as its own stack.
- Ties: smaller/riskier-to-conflict first. Ambiguous consequential order → ask, never guess.
