```json
{
  "schema_version": "1.0.0",
  "runtime": {
    "agent": "anchor-sprint-review",
    "harness": "codex",
    "model": "luna",
    "path": ".codex/agents/anchor-sprint-review.md",
    "sha256": "edef191368eb10e3057344d611fc7c7f0483a2eb041d41711789c938ee23505c",
    "version": "0.5.0"
  },
  "operation": "sprint_review",
  "correlation_id": "sc-stack-dev-E1-1",
  "params": {
    "script": "/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0/skills/plan-anchoring/scripts/jev_judge.py",
    "plugin_root": "/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0",
    "workspace": "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency",
    "sprint_id": "sc-stack-review-p68",
    "anchor_ids": "all",
    "anchors_path": "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchors.json",
    "evidence": [
      "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/execution.md",
      "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1/evidence-map.md",
      "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1/files-changed.md",
      "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1/test-summary.md"
    ],
    "run_dir": "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1",
    "threshold": 0.6,
    "dry_run": false,
    "correlation_id": "sc-stack-dev-E1-1",
    "authorized_gate_runner": "/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1/execute-approved-gate.py",
    "parent_authorization": "The user explicitly requested the live development gate. After composing and validating item.txt, invoke the parent-authored authorized_gate_runner once with item.txt as its sole argument instead of invoking judge directly. The parent runner fixes the canonical script, anchors, model, threshold and output, grants consent only to that child, and refuses duplicate execution. Never set any consent environment variable yourself. Do not retry. Save the final fenced response unchanged to run_dir/agent-response.md and preserve item.txt/account snapshots in run_dir. Defaults are the initial development questions; do not use planning overrides or tune any question."
  }
}
```
