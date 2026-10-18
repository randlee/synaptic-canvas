"""Execute the documented read-only projection, not a copy of its selection logic."""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(not shutil.which('bash') or not shutil.which('jq'),
                                reason='documented shell projection requires bash and jq')
REFERENCE = Path(__file__).resolve().parents[1] / 'skills/sc-gh-stack/references/recipe-evidence.md'
SHA = 'a' * 40


def observation():
    branches = [{'name': f'layer/{number}', 'head': SHA, 'base': SHA, 'isMerged': False,
                 'pr': {'number': number, 'state': 'OPEN'}} for number in range(1, 121)]
    return {'success': True, 'git_observation': {'fresh': True}, 'stacks': [
        {'number': 7, 'trunk': 'main', 'branches': branches,
         'structure_observation': {'complete': True, 'freshness': 'fresh'},
         'rows': [{'branch': branch['name'], 'origin': SHA} for branch in reversed(branches)]}]}


def run_documented_projection(payload, helper_exit=0):
    # Substitute the user's actual stack number for the documentation placeholder.
    block = re.search(r'```bash\n(.*?)\n```', REFERENCE.read_text(), re.S).group(1)
    script = "python3() { printf '%s\\n' \"$SC_RECIPE_TEST_PAYLOAD\"; return \"$SC_RECIPE_TEST_EXIT\"; }\n"
    script += block.replace('<stack#>', '7')
    environment = dict(os.environ, SC_RECIPE_TEST_PAYLOAD=json.dumps(payload),
                       SC_RECIPE_TEST_EXIT=str(helper_exit))
    return subprocess.run(['bash', '-c', script], env=environment, text=True,
                          capture_output=True, timeout=5)


@pytest.mark.parametrize('helper_exit', [0, 1])
def test_documented_top_uses_complete_order_not_reversed_or_truncated_summary(helper_exit):
    payload = observation()
    # Exit 1 may describe another layer's problem, not an invalid read result.
    payload['coherent'] = helper_exit == 0
    result = run_documented_projection(payload, helper_exit)
    assert result.returncode == 0, result.stderr
    compact = json.loads(result.stdout)
    assert compact['top'] == {'name': 'layer/120', 'head': SHA}
    assert len(compact['branches']) == 120
    assert 'rows' not in compact and 'observations' not in compact


def test_documented_top_excludes_merged_tail():
    payload = observation()
    tail = payload['stacks'][0]['branches'][-1]
    tail['isMerged'], tail['pr']['state'] = True, 'MERGED'
    result = run_documented_projection(payload)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['top']['name'] == 'layer/119'


@pytest.mark.parametrize('missing', ['structure', 'freshness', 'git', 'lifecycle', 'top_row',
                                   'short_sha', 'empty_sha', 'success', 'ambiguous_scope', 'active_layers'])
def test_documented_projection_refuses_unknown_or_incomplete_evidence(missing):
    payload = observation()
    stack = payload['stacks'][0]
    if missing == 'structure':
        stack['structure_observation']['complete'] = False
    elif missing == 'freshness':
        stack['structure_observation']['freshness'] = 'stale'
    elif missing == 'git':
        payload['git_observation']['fresh'] = False
    elif missing == 'lifecycle':
        stack['branches'][-1]['pr']['state'] = 'UNKNOWN'
    elif missing == 'top_row':
        stack['rows'] = stack['rows'][1:]
    elif missing in ('short_sha', 'empty_sha'):
        stack['rows'][0]['origin'] = SHA[:9] if missing == 'short_sha' else ''
    elif missing == 'success':
        payload['success'] = False
    elif missing == 'ambiguous_scope':
        payload['stacks'].append(copy.deepcopy(stack))
    elif missing == 'active_layers':
        for branch in stack['branches']:
            branch['isMerged'], branch['pr']['state'] = True, 'MERGED'
    result = run_documented_projection(payload)
    assert result.returncode != 0
    assert not result.stdout.strip(), 'Unknown evidence must not emit a usable top/composition'


@pytest.mark.parametrize('helper_exit', [2, 3, 130])
def test_documented_projection_never_accepts_fatal_helper_exit(helper_exit):
    result = run_documented_projection(observation(), helper_exit)
    assert result.returncode != 0
    assert not result.stdout.strip()
