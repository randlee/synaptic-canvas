"""Freeze the report correction and unchanged sealed questions for one review."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'doc/plan/sc-gh-stack-api-efficiency'
RUNS = BASE / 'anchor-runs/0.5.0'
OLD = RUNS / 'development-gate-E1-r3'
OUT = RUNS / 'development-gate-E1-r4'
OUT.mkdir(exist_ok=True)

def write(name, value):
    path = OUT / name
    assert not path.exists(), f'Refuse to overwrite {path}'
    path.write_text(value)

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
report = (OLD / 'execution-report.md').read_text()
report = report.replace('**134 tests passed**', '**135 tests passed**').replace('(37.14 seconds)', '(37.62 seconds)')
report = report.replace('Development-gate status: pending. The initial account omitted a supplied\n'
    'evidence map; the corrected second run left ANC-004 and ANC-008 inconclusive.\n'
    'Independent authority-only question calibration is in progress; no gate pass\n'
    'or acceptance is claimed. Paired recipe review also added API-free catalog\n'
    'source/composition diagnostics, including when no disputed stack is accepted.',
    'Development-gate status: pending. Independent authority-only development-question\n'
    'calibration is complete for ANC-004 and ANC-008; intent, anchors and the 0.6\n'
    'threshold are unchanged. The third run satisfied nine anchors but left economical\n'
    'REST selection inconclusive. The account below now distinguishes required fields\n'
    'and deterministic request counts. Paired review added API-free catalog diagnostics\n'
    'and removed one residual mandatory post-link report while retaining affected-base\n'
    'verification. No gate pass or acceptance is claimed.')
report = report.replace('Implemented on `feature/sc-gh-stack-api-efficiency`; baseline `fc702b1`.',
    f'Implemented and pushed on `feature/sc-gh-stack-api-efficiency` at `{head}`; baseline `fc702b1`.')
write('execution-report.md', report)
evidence = (OLD / 'evidence-map.md').read_text().replace('1e0c066f835379ecba2ddb32dc10eb0f070460ad', head).replace('`134 passed in 37.14s`', '`135 passed in 37.62s`')
lines = evidence.splitlines()
for index, line in enumerate(lines):
    if line.startswith('| ANC-004 |'):
        lines[index] = ('| ANC-004 | Delivered source preference: for one or two missing PR metadata observations, '
            '`gh_stack_remote.py:_prs` uses REST instead of GraphQL because the PR response supplies all required COMMON fields '
            '(number, lifecycle, draft, base/head names and head SHA), spending zero GraphQL budget. '
            '`test_source_selection_preserves_fields_without_rest_fanout` measures two REST requests and zero GraphQL requests for two PRs. '
            'Bulk metadata uses one aliased GraphQL batch per 50 rather than one REST request per PR (120 PRs: three queries versus 120 REST requests). '
            'Status also requires CI rollup, which the metadata REST response does not supply: the same test measures one GraphQL request and zero REST requests for a one-PR status read, not a redundant REST-then-GraphQL pair. '
            '`test_metadata_rest_etag_304` verifies conditional REST reuse. These are fake-transport request counts and source equivalence checks, not measured live quota charges. |')
evidence = '\n'.join(lines) + '\n'
write('evidence-map.md', evidence)
stat = subprocess.check_output(['git', 'diff', '--stat', f'fc702b1..{head}', '--'], cwd=ROOT, text=True)
write('files-changed.md', '# Files changed\n\n```text\n' + stat + '```\n')
write('test-summary.md', (OLD / 'test-summary.md').read_text().replace('134 passed in 37.14s', '135 passed in 37.62s'))
paths = [str(OUT / name) for name in ['execution-report.md', 'evidence-map.md', 'files-changed.md', 'test-summary.md']]
wrapper = (OLD / 'execute-approved-gate.py').read_text()
start = wrapper.index('texts = ')
end = wrapper.index('assert all(text in item.read_text()', start)
wrapper = wrapper[:start] + 'texts = [Path(path).read_text().strip() for path in ' + repr(paths) + ']\n' + wrapper[end:]
write('execute-approved-gate.py', wrapper)
variables = json.loads((OLD / 'invocation-vars.json').read_text())
variables['correlation_id'] = 'sc-stack-dev-E1-4'
variables['params'].update(evidence=paths, run_dir=str(OUT), correlation_id=variables['correlation_id'],
    authorized_gate_runner=str(OUT / 'execute-approved-gate.py'),
    parent_authorization='User-requested development review after the recorded report correction and deterministic-review fix. Same sealed development overrides_file, unchanged intent/anchor versions and threshold 0.6. Assemble all four supplied evidence files verbatim. Invoke authorized_gate_runner once with composed item.txt; it supplies child-only consent. Preserve account/item, bd snapshots and final single-fenced response in run_dir. Do not tune, edit evidence, retry judge, or run deterministic checks.')
write('invocation-vars.json', json.dumps(variables, indent=2) + '\n')
write('growth-authority.json', json.dumps({'previous_run': 'development-gate-E1-r3/run.json',
    'changes': [
        {'files': ['execution-report.md', 'evidence-map.md', 'test-summary.md'], 'authority': 'ANC-004 v1 / ANC-010 v1',
         'reason': 'Replace underspecified source selection with required fields and actual routing-test counts; update passing test count.'},
        {'files': ['execution-report.md'], 'authority': 'ANC-002 v1 / ANC-007 v1',
         'reason': 'Record removal of a redundant mandatory report without removing affected-base verification.'},
        {'files': ['files-changed.md'], 'authority': 'ANC-010 v1', 'reason': 'Refresh immutable git diff-stat for the focused test and documented work fix.'}],
    'normative_authority_changed': False, 'questions_changed': False}, indent=2) + '\n')
print(OUT)
