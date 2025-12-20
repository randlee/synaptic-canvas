# sc-startup – Use Cases

## 1) Daily kickoff
- Run `/sc-startup --pr` at the start of the day.
- Reads startup prompt, syncs checklist, scans PRs, surfaces worktree hygiene recommendations.
- Output: concise status + next steps.

## 2) Pre-standup report
- Run `/sc-startup --readonly` to avoid mutations.
- Generates a status snapshot (checklist gaps, PRs, worktrees) for team sharing.

## 3) Handoff validation
- After merging a feature branch, run `/sc-startup --pull` to sync master → develop, then refresh checklist.
- Ensures checklist reflects merged state before handoff.

## 4) New contributor onboarding
- Provide `.claude/sc-startup.yaml` and run `/sc-startup --fast` to load the startup prompt and role.
- Keeps context minimal while orienting the contributor.

## 5) Repo hygiene sweep
- Set `worktree-scan: cleanup` in config and run `/sc-startup`.
- Worktree cleanup agent runs (unless `--readonly`) and reports cleaned/dirty worktrees.

## 6) PR triage with guardrails
- Run `/sc-startup --pr --readonly` when you want PR visibility without auto-fix.
- Produces PR table with suggested actions; no mutations.

## 7) CI sync before status reporting
- Run `/sc-startup --pull --readonly` to ensure develop is up to date with master before checklist reporting.
- Checklist sync uses merged view; status includes CI pull result.
