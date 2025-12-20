# sc-startup – Troubleshooting

## DEPENDENCY.MISSING
- **Symptom:** Startup fails with message naming a missing feature/agent (e.g., `ci-pr-agent`).
- **Fix:** Install the required package (e.g., `sc-ci-automation`, `sc-git-worktree`) or set `pr-enabled: false` / `worktree-enabled: false` in `.claude/sc-startup.yaml`.

## Missing config or paths
- **Symptom:** Error about missing `.claude/sc-startup.yaml` or prompt/checklist paths.
- **Fix:** Copy `.claude/sc-startup.yaml.example` into `.claude/`, adjust paths to repo-root-relative, and rerun.

## Checklist not updating
- **Symptom:** Checklist remains unchanged after run.
- **Fix:** Ensure you are not using `--readonly`. Verify file permissions and that `check-list` points to the correct file.

## Worktree cleanup skipped
- **Symptom:** Cleanup requests report-only.
- **Fix:** Remove `--readonly` and set `worktree-scan: cleanup` in config. Confirm `sc-git-worktree` package is installed.

## PR triage does nothing
- **Symptom:** `/sc-startup --pr` reports missing agent.
- **Fix:** Install `sc-ci-automation` package; ensure `pr-enabled: true`. Use `--readonly` if you only want list/report.

## CI pull not reflected
- **Symptom:** Checklist updates don’t reflect merged master → develop.
- **Fix:** Run with `--pull`; the skill waits for pull completion before checklist sync. Check CI/pull output for errors/timeouts.

## Unfenced or malformed JSON
- **Symptom:** Agent results rejected.
- **Fix:** Ensure agents return fenced JSON minimal envelope; rerun or update agent if malformed output persists.
