"""Render authority-only development question requests, never a target report."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

SKILL = Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0/skills/plan-anchoring')
ROOT = Path('/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/sc-gh-stack-api-efficiency')
BASE = ROOT / 'doc/plan/sc-gh-stack-api-efficiency/anchor-runs/0.5.0'
sys.path.insert(0, str(SKILL / 'scripts'))
from anchor_tuning_contract import validate_request

template = SKILL / 'templates/anchor-tuning-tune-request.md.j2'
for anchor in ('ANC-004', 'ANC-008'):
    original = (BASE / 'plan-tuning' / anchor / 'request.md').read_text()
    packet = json.loads(re.search(r'```json\s*(.*?)\s*```', original, re.S).group(1))
    packet['gate'] = 'development'
    packet['correlation_id'] = 'sc-stack-dev-' + anchor.lower()
    packet['current_questions'] = json.loads((SKILL / 'assets/questions/dev.json').read_text())['questions']
    packet['tuning_history'] = {'schema': 'plan-anchor/tuning-history/2', 'history_id': packet['correlation_id'], 'events': []}
    packet['diagnostic_plan'] = None
    packet['runtime']['script'] = str(SKILL / 'scripts/jev_judge.py')
    packet['runtime']['sha256'] = hashlib.sha256((SKILL / 'scripts/jev_judge.py').read_bytes()).hexdigest()
    packet['runtime']['contract_sha256'] = hashlib.sha256((SKILL / 'scripts/anchor_tuning_contract.py').read_bytes()).hexdigest()
    packet['template']['sha256'] = hashlib.sha256(template.read_bytes()).hexdigest()
    validate_request(packet)
    directory = BASE / 'development-question-tuning' / anchor
    directory.mkdir(parents=True, exist_ok=True)
    variables = dict(packet)
    variables['template'] = packet['template']
    variable_file = directory / 'vars.json'
    variable_file.write_text(json.dumps(variables, indent=2))
    subprocess.run(['sc-compose', 'render', '--root', '/Users/randlee', '--file', str(template), '--var-file', str(variable_file),
                    '--strict', '--check-render', '--output', str(directory / 'request.md')], check=True, capture_output=True)
    print(str(directory / 'request.md'))
