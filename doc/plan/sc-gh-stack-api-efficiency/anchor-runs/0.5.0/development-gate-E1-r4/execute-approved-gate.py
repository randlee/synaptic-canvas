"""One child-process-only consent grant for the user-requested E1 dev gate."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency')
SKILL = Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0/skills/plan-anchoring')
BASE = ROOT / 'doc/plan/sc-gh-stack-api-efficiency'
OUTPUT = Path(__file__).resolve().parent / 'run.json'
item = Path(sys.argv[1]).resolve(strict=True)
assert item.is_file() and item.name == 'item.txt'
texts = [Path(path).read_text().strip() for path in ['/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1-r4/execution-report.md', '/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1-r4/evidence-map.md', '/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1-r4/files-changed.md', '/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency/doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0/development-gate-E1-r4/test-summary.md']]
assert all(text in item.read_text() for text in texts), 'Incomplete supplied evidence; no request sent'
assert OUTPUT.exists() is False, 'Reuse the existing run; never repeat the gate implicitly'
environment = os.environ.copy()
# User explicitly requested this live development gate on 2026-10-17.
# Consent is restricted to this one child; no shell/app configuration changes.
environment['PLAN_ANCHOR_ALLOW_REMOTE_JUDGE'] = '1'
environment['SSL_CERT_FILE'] = '/etc/ssl/cert.pem'
command = ['python3', str(SKILL / 'scripts/jev_judge.py'), 'judge',
           '--anchors', str(BASE / 'anchors.json'), '--gate', 'dev', '--all',
           '--item-id', 'sc-stack-review-p68', '--item-title', 'E1 — Economical stack state development review',
           '--item-file', str(item), '--overrides-file', str(BASE / 'development-overrides.json'), '--model', 'jev-1.13.0', '--threshold', '0.6', '--out', str(OUTPUT)]
completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
response = json.loads(completed.stdout)
print(json.dumps(response))
raise SystemExit(completed.returncode)
