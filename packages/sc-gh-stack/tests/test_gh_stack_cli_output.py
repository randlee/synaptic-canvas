"""Machine-output and bounded-output contracts; no API or repository required."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from gh_stack_shared import compact_report, guarded
from gh_stack_view import render_landing


@pytest.mark.parametrize('script', ['gh_stack_view.py', 'gh_stack_chain_check.py'])
@pytest.mark.parametrize('flag', ['--json', '--compact-json'])
@pytest.mark.parametrize('invalid', [[], ['--unknown-option'], ['--remote'],
                                   ['--no-fetch', '--refresh-git'],
                                   ['--no-pr', '--refresh-status']])
def test_parse_failures_have_json_envelopes_before_any_external_work(script, flag, invalid):
    # Chain missing arguments are independently checked below; other cases get
    # valid positionals so the failure is the option under test.
    required = ['--trunk', 'main', 'topic'] if script.startswith('gh_stack_chain') else []
    if not invalid and required:
        required = []
    if not invalid and not required and script.startswith('gh_stack_view'):
        invalid = ['--no-such-option']
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), flag, *required, *invalid],
                          text=True, capture_output=True)
    assert proc.returncode == 2
    body = json.loads(proc.stdout)
    assert body['success'] is False
    assert body['error']['code'] == 'INPUT.INVALID_ARGUMENT'
    assert 'Traceback' not in proc.stderr


@pytest.mark.parametrize('script', ['gh_stack_view.py', 'gh_stack_chain_check.py'])
@pytest.mark.parametrize('other', ['--json', '--full'])
def test_compact_conflicts_are_machine_readable(script, other):
    required = ['--trunk', 'main', 'topic'] if script.startswith('gh_stack_chain') else []
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), '--compact-json', other, *required],
                          text=True, capture_output=True)
    assert proc.returncode == 2
    assert json.loads(proc.stdout)['error']['code'] == 'INPUT.INVALID_ARGUMENT'


def snapshot(layers=120):
    rows = [dict(layer=n, branch=f'layer/{n}', pr=n, merged=False, local_merge_clean=True,
                 changed=False, hosted_stale=False, ci='SUCCESS', provenance={'state': {'freshness': 'fresh'}})
            for n in range(1, layers + 1)]
    rows[-1]['local_merge_clean'] = False
    return dict(schema_version=1, success=True, coherent=False, snapshot_id='epoch',
                git_observation={'fresh': True}, observations={str(n): {'duplicate': 'x' * 4000} for n in range(layers)},
                catalogs=[{'unbounded': 'x' * 4000}], warnings=['warning'] * 120,
                stacks=[dict(trunk='main', rows=rows, branches=[{'name': row['branch']} for row in rows],
                             coherent=False, structure_observation={'complete': True, 'freshness': 'fresh'},
                             local_mergeability={'clean': False, 'layers': rows, 'combined': {'clean': True}},
                             landing={'landable': True, 'top': 'layer/120'}, problems=['conflict'] * 120, notes=['note'] * 120)])


def test_120_layer_compact_projection_is_bounded_without_changing_source_or_verdict():
    payload = snapshot()
    full = json.dumps(payload)
    compact = compact_report(payload)
    entry = compact['stacks'][0]
    assert entry['total_layers'] == 120
    assert entry['shown_layers'] == 10
    assert entry['truncated'] is True
    assert entry['rows'][0]['branch'] == 'layer/120'
    assert entry['local_mergeability']['clean'] is False
    assert entry['local_mergeability']['conflict_count'] == 1
    assert len(entry['problems']) == len(entry['notes']) == len(compact['warnings']) == 10
    assert entry['problem_count'] == entry['note_count'] == compact['warning_count'] == 120
    assert compact['coherent'] is False
    assert 'branches' not in entry and 'observations' not in compact and 'catalogs' not in compact
    assert len(json.dumps(compact)) < len(full) // 10
    assert json.dumps(payload) == full


def test_compact_chain_contract_keeps_unknown_and_link_command():
    payload = snapshot()
    chain = dict(payload['stacks'][0], schema_version=1, success=True, linkable=None,
                 link_command=None, unknown_count=120, warnings=[], git_observation={'fresh': False})
    compact = compact_report(chain)
    assert compact['linkable'] is None and compact['link_command'] is None
    assert compact['unknown_count'] == 120
    assert compact['total_layers'] == 120 and len(compact['rows']) == 10


def test_compact_stack_count_is_also_bounded():
    payload = snapshot(1)
    payload['stacks'] *= 120
    compact = compact_report(payload)
    assert compact['total_stacks'] == 120 and compact['shown_stacks'] == 10
    assert compact['truncated'] is True and len(compact['stacks']) == 10


def test_compact_ref_observations_and_commands_cannot_restore_unbounded_output():
    payload = snapshot()
    payload['git_observation'].update(refs={str(n): {'fresh': n != 119, 'error': None} for n in range(120)},
                                      required_refs=[str(n) for n in range(120)], error='x' * 10000)
    compact = compact_report(payload)
    git = compact['git_observation']
    assert git['requested_ref_count'] == git['required_ref_count'] == 120
    assert git['shown_ref_count'] == len(git['required_refs']) == len(git['refs']) == 10
    assert list(git['refs'])[0] == '119'
    assert git['truncated'] is True
    assert compact['text_truncated'] is True
    assert len(git['error']) < 1100
    chain = dict(payload['stacks'][0], schema_version=1, success=True, link_command='gh stack link ' + 'a ' * 120)
    compact = compact_report(chain)
    assert compact['link_command'] is None and compact['link_command_omitted'] is True


def test_interrupt_keeps_json_failure_contract():
    def interrupt():
        raise KeyboardInterrupt
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
        assert guarded('fixture', interrupt, json_errors=True) == 2
    assert json.loads(output.getvalue())['error']['code'] == 'TOOL.INTERRUPTED'


def test_landing_text_explicitly_does_not_certify_whole_stack():
    text = render_landing({'landable': True, 'top': 'top', 'top_sha': 'a' * 40, 'reason': 'clean top'})
    assert 'top/trunk' in text and 'not whole-stack eligibility' in text
