"""Freeze current development evidence and deploy independently sealed questions."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'doc/plan/sc-gh-stack-api-efficiency'
RUNS = BASE / 'anchor-runs/0.5.0'
OUT = RUNS / 'development-gate-E1-r3'
OUT.mkdir(exist_ok=True)

def write(path, value):
    assert not path.exists(), f'Refuse to overwrite {path}'
    path.write_text(value)

overrides = {}
calibration = []
for aid in ['ANC-004', 'ANC-008']:
    source = RUNS / 'development-question-tuning' / aid / 'result.json'
    data = json.loads(source.read_text())['data']
    assert data['accepted'] and data['production_confidence_threshold'] == 0.6
    sealed = data['sealed_question_set']
    digest = hashlib.sha256(json.dumps({'questions': sealed['questions']}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert digest == sealed['digest']
    overrides[aid] = {'questions': sealed['questions']}
    calibration.append({'anchor_id': aid, 'question_sha256': digest,
                        'oracle_sha256': data['oracle_sha256'],
                        'semantic_score': data['semantic_score'],
                        'source': str(source.relative_to(ROOT))})
write(BASE / 'development-overrides.json', json.dumps(overrides, indent=2) + '\n')
write(OUT / 'calibration-summary.json', json.dumps({'threshold': 0.6, 'independent_of_implementation': True,
      'authority_unchanged': True, 'selected': calibration}, indent=2) + '\n')
write(OUT / 'execution-report.md', (BASE / 'execution.md').read_text())
evidence = (RUNS / 'development-gate-E1/evidence-map.md').read_text()
evidence = evidence.replace('the reviewed feature worktree is not yet committed.',
    'reviewed implementation is pushed at commit `1e0c066f835379ecba2ddb32dc10eb0f070460ad`.')
evidence = evidence.replace('`133 passed in 35.62s`', '`134 passed in 37.14s`')
evidence = evidence.replace('Only equivalent information-gathering calls and cadence change.',
    'Only equivalent information-gathering calls and cadence change. Local catalog source/composition diagnostics are exposed in successful JSON and `error.details.catalogs` when every candidate is conflicting; `test_gh_stack_local.py` verifies both worktree paths/compositions remain inspectable without accepting disputed definitions or calling an API.')
write(OUT / 'evidence-map.md', evidence)
stat = subprocess.check_output(['git', 'diff', '--stat', 'fc702b1..1e0c066f835379ecba2ddb32dc10eb0f070460ad', '--'], cwd=ROOT, text=True)
write(OUT / 'files-changed.md', '# Files changed\n\n```text\n' + stat + '```\n')
write(OUT / 'test-summary.md', '# Tests\n\nCommand: `python3 -m pytest -q packages/sc-gh-stack/tests`\n\n'
      'Result on 2026-10-17: **134 passed in 37.14s** (Python 3.11.9).\n\n'
      'Git fixtures and fake API transports only; no live GitHub requests. '
      'Compilation, temporary installed-entrypoint smoke checks and `git diff --check` passed. '
      'Hosted Linux CI is configured but has not run. No 500-layer experiment.\n')
evidence_paths = [str(OUT / name) for name in ['execution-report.md', 'evidence-map.md', 'files-changed.md', 'test-summary.md']]
wrapper = (RUNS / 'development-gate-E1-r2/execute-approved-gate.py').read_text()
start = wrapper.index('texts = ')
end = wrapper.index("assert all(text in item.read_text()", start)
wrapper = wrapper[:start] + 'texts = [Path(path).read_text().strip() for path in ' + repr(evidence_paths) + ']\n' + wrapper[end:]
wrapper = wrapper.replace("'--item-file', str(item),", "'--item-file', str(item), '--overrides-file', str(BASE / 'development-overrides.json'),")
write(OUT / 'execute-approved-gate.py', wrapper)
variables = json.loads((RUNS / 'development-gate-E1-r2/invocation-vars.json').read_text())
variables['correlation_id'] = 'sc-stack-dev-E1-3'
p = variables['params']
p.update(evidence=evidence_paths, run_dir=str(OUT), correlation_id=variables['correlation_id'],
         overrides_file=str(BASE / 'development-overrides.json'),
         authorized_gate_runner=str(OUT / 'execute-approved-gate.py'),
         parent_authorization='User-requested development review with independently calibrated, schema/contract-validated ANC-004 and ANC-008 development overrides. Authority, scope and 0.6 production threshold unchanged. Assemble ALL FOUR supplied evidence files verbatim; wrapper refuses omissions. Use supplied overrides_file rather than default questions for those two anchors. Invoke authorized_gate_runner once with composed item.txt; child-only consent is supplied there, never set consent yourself. Preserve account, item, bd snapshots and final single-fenced response in run_dir. Do not tune, edit evidence, retry judge, or run deterministic checks.')
write(OUT / 'invocation-vars.json', json.dumps(variables, indent=2) + '\n')
print(OUT)
