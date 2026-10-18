"""Validate and retain review artifacts without making remote judge calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'doc/plan/sc-gh-stack-api-efficiency'
RUNS = BASE / 'anchor-runs/0.5.0'
SCRIPTS = Path('/Users/randlee/.codex/plugins/cache/plan-anchor/sc-plan-anchor/0.5.0/skills/plan-anchoring/scripts')
sys.path.insert(0, str(SCRIPTS))
from anchor_runner_contract import atomic_write_json, build_attestation, parse_result

def generate(args):
    return subprocess.check_output(['python3', str(SCRIPTS / 'jev_judge.py'), *args], cwd=ROOT, text=True).rstrip() + '\n'

directories = ['development-gate-E1', 'development-gate-E1-r2', 'development-gate-E1-r3', 'development-gate-E1-r4']
for number, name in enumerate(directories, 1):
    path = RUNS / name
    variables = json.loads((path / 'invocation-vars.json').read_text())
    result = parse_result((path / 'agent-response.md').read_text(), variables['correlation_id'])
    assert result['success']
    (path / 'report.md').write_text(generate(['report', '--run', str(path / 'run.json'), '--format', 'md', '--all']))
    atomic_write_json(path / 'parent-attestation.json', build_attestation(
        variables['runtime'], 'sprint_review', variables['correlation_id'],
        started_at_ms=(path / 'invocation-vars.json').stat().st_mtime_ns // 1000000,
        finished_at_ms=(path / 'agent-response.md').stat().st_mtime_ns // 1000000,
        outcome='success', source_sha256=hashlib.sha256((path / 'item.txt').read_bytes()).hexdigest()))
    if number > 1:
        (path / 'diff.json').write_text(generate(['diff', '--prev', str(RUNS / directories[number - 2] / 'run.json'), '--next', str(path / 'run.json')]))

runtime = {'agent': 'anchor-tuning', 'harness': 'codex', 'model': 'sol',
           'path': '.codex/agents/anchor-tuning.md', 'version': '0.5.0',
           'sha256': '36e6a333ac291710a238c5c668bf48e191deb4c1e629e3147b85660f16f5ca26'}
for aid in ['ANC-004', 'ANC-008']:
    path = RUNS / 'development-question-tuning' / aid
    correlation = 'sc-stack-dev-' + aid.lower()
    result = parse_result((path / 'response.md').read_text(), correlation)
    assert result['success'] and result['data']['accepted']
    subprocess.run(['python3', str(SCRIPTS / 'anchor_tuning_contract.py'), 'result', str(path / 'result.json')], check=True)
    atomic_write_json(path / 'parent-attestation.json', build_attestation(
        runtime, 'tune', correlation,
        started_at_ms=(path / 'request.json').stat().st_mtime_ns // 1000000,
        finished_at_ms=(path / 'response.md').stat().st_mtime_ns // 1000000,
        outcome='success', source_sha256=hashlib.sha256((path / 'request.json').read_bytes()).hexdigest()))

final = RUNS / directories[-1]
run = json.loads((final / 'run.json').read_text())
assert run['threshold'] == 0.6 and run['summary']['pass']
checks = []
overrides = json.loads((BASE / 'development-overrides.json').read_text())
for row in run['results']:
    assert row['verdict'] == 'satisfied'
    if row['anchor_id'] in overrides:
        assert row['questions'] == overrides[row['anchor_id']]['questions']
    for role, answer in row['answers'].items():
        assert answer['choice'] == ('no' if role == 'violated' else 'yes') and answer['confidence'] >= 0.6
        checks.append({'anchor_id': row['anchor_id'], 'role': role, 'choice': answer['choice'], 'confidence': answer['confidence']})
atomic_write_json(final / 'strict-role-check.json', {'passed': True, 'threshold': 0.6, 'roles': checks})
(final / 'coverage.md').write_text(generate(['coverage', '--runs', str(final / 'run.json'), '--gate', 'dev', '--format', 'md']))
(final / 'posted-report.md').write_text((final / 'report.md').read_text() + '\n' + (final / 'paired-checks.md').read_text())
atomic_write_json(final / 'attestation-timing.json', {
    'basis': 'Outer invocation timing is bracketed by the parent-authored invocation/request file mtime and the saved response file mtime, not the narrower judge-only duration.',
    'gate_pass': True, 'paired_checks_completed': True,
    'reviewed_commit': 'dc526cc', 'live_github_api_tests': False})
atomic_write_json(final / 'tracker-snapshot.json', {
    'show': json.loads(subprocess.check_output(['bd', 'show', 'sc-stack-review-p68', '--json'], cwd=ROOT, text=True)),
    'comments': json.loads(subprocess.check_output(['bd', 'comments', 'sc-stack-review-p68', '--json'], cwd=ROOT, text=True))})
print('Validated four development results, two tuning results, attestations, final strict role checks, reports, diffs and coverage.')
