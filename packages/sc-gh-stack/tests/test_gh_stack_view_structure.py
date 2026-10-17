"""Composition authority and epoch regressions; all hosted transport is fake."""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gh_stack_view as view
from gh_stack_remote import StackDataClient


SHAS = {'main': 'a' * 40, 'one': 'b' * 40, 'two': 'c' * 40, 'three': 'd' * 40}
NUMBERS = {'one': 11, 'two': 12, 'three': 13}


def local_snapshot():
    return {'repository': {}, 'warnings': [], 'fingerprint': 'initial',
            'catalogs': [{'source_path': '/git/gh-stack', 'digest': 'catalog-v1'}],
            'refs': {f'refs/{kind}/{name}': sha for kind in ('heads', 'remotes/origin') for name, sha in SHAS.items()},
            'stacks': [{'number': 42, 'id': 'S_42', 'trunk': 'main', 'worktree': '/worktree',
                        'branches': [{'name': name, 'head': SHAS[name], 'recorded_head': SHAS[name],
                                      'base': SHAS[parent], 'pr': {'number': NUMBERS[name]},
                                      'isMerged': False, 'isQueued': None}
                                     for name, parent in [('one', 'main'), ('two', 'one')]]}]}


def remote_stack(names=('one', 'two')):
    return {'number': 42, 'node_id': 'S_42', 'base': {'ref': 'main'},
            'pull_requests': [{'number': NUMBERS[name], 'state': 'open',
                               'head': {'ref': name, 'sha': SHAS[name]}} for name in names]}


@pytest.fixture
def harness(tmp_path):
    snapshot = local_snapshot()
    client = Mock()
    client.cache_dir, client.path = tmp_path, tmp_path / 'remote.json'
    client.snapshot_id, client.metrics, client.warnings = 'hosted', {}, []
    client.observations, client.branch_observations = {}, {}
    client.stack_observations = {42: {'source': 'REST', 'freshness': 'fresh', 'complete': True, 'observed_at': 100}}
    client.refresh_stack.return_value = remote_stack()
    client.refresh_git.return_value = {'fresh': True, 'source': 'fetched', 'observed_at': 100}

    def details(numbers, **kwargs):
        result = {}
        for name, parent in [('one', 'main'), ('two', 'one'), ('three', 'two')]:
            number = NUMBERS[name]
            if number in numbers:
                result[number] = {'number': number, 'state': 'OPEN', 'isDraft': False,
                                  'headRefName': name, 'headRefOid': SHAS[name], 'baseRefName': parent,
                                  'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN', 'ci': 'SUCCESS'}
                client.observations[number] = {key: {'freshness': 'fresh'} for key in result[number]}
        return result
    client.pr_details.side_effect = details

    def conflicts(stack, refs, *args, **kwargs):
        layers = [{'branch': branch['name'], 'clean': True, 'reason': 'clean'} for branch in stack['branches']]
        return {'layers': layers, 'clean': True,
                'combined': {'clean': True, 'reason': 'clean', 'head': SHAS[stack['branches'][-1]['name']]}}

    def run(*, snapshots=None, trunk_filter=None, guard_errors=False, **flags):
        args = argparse.Namespace(all=False, no_pr=False, no_fetch=False, json=True, stack='42',
                                  refresh=False, refresh_git=False, refresh_status=False)
        vars(args).update(flags)
        sequence = snapshots or [snapshot, snapshot, snapshot]
        output = io.StringIO()
        with patch.object(view, 'preflight'), \
             patch.object(view, 'read_local_snapshot', side_effect=[copy.deepcopy(item) for item in sequence]), \
             patch.object(view, 'StackDataClient', return_value=client), \
             patch.object(view, 'evaluate_stack_conflicts', side_effect=conflicts), \
             patch.object(view, 'is_ancestor', return_value=True), contextlib.redirect_stdout(output):
            body = lambda: view.run_report(args, trunk_filter)
            code = view.guarded('gh-stack-view', body, json_errors=True) if guard_errors else body()
        return code, json.loads(output.getvalue())
    return snapshot, client, run


@pytest.mark.parametrize('names', [('one', 'two', 'three'), ('one',)])
def test_explicit_refresh_replaces_membership_before_ref_and_status_work(harness, names):
    _, client, run = harness
    client.refresh_stack.return_value = remote_stack(names)
    _, report = run(refresh=True)
    entry = report['stacks'][0]
    assert [branch['name'] for branch in entry['branches']] == list(names)
    assert client.refresh_git.call_args.kwargs['refs'] == sorted({'main', *names})
    assert client.pr_details.call_args.args[0] == [NUMBERS[name] for name in names]
    assert entry['structure_observation']['complete'] is True
    assert entry['structure_observation']['freshness'] == 'fresh'
    calls = [call[0] for call in client.mock_calls]
    assert calls.index('refresh_stack') < calls.index('refresh_git') < calls.index('pr_details')


def test_unchanged_refresh_preserves_qualified_local_tracking(harness):
    _, client, run = harness
    code, report = run(refresh=True)
    assert code == 0
    assert report['coherent'] is True
    assert [branch['base'] for branch in report['stacks'][0]['branches']] == [SHAS['main'], SHAS['one']]
    assert all(branch['base_source'] == 'local_catalog' for branch in report['stacks'][0]['branches'])
    client.refresh_stack.assert_called_once_with(42, force=True)


def test_remote_shape_keeps_existing_public_id_contract(harness):
    _, client, run = harness
    body = remote_stack()
    body['id'] = 6154
    client.refresh_stack.return_value = body
    _, report = run(refresh=True)
    assert report['stacks'][0]['id'] == 6154


def test_explicit_numeric_discovery_refreshes_structure_only_once(harness):
    snapshot, client, run = harness
    snapshot['stacks'] = []
    snapshot['warnings'] = ['No local gh-stack catalog; remote-only stacks may still exist']
    _, report = run(refresh=True)
    client.refresh_stack.assert_called_once_with(42, force=True)
    assert [branch['name'] for branch in report['stacks'][0]['branches']] == ['one', 'two']
    assert report['stacks'][0]['structure_observation']['complete'] is True
    assert report['skipped_worktrees'] == []


def test_remote_order_is_authoritative_even_when_local_tracking_disagrees(harness):
    _, client, run = harness
    client.refresh_stack.return_value = remote_stack(('two', 'one'))
    code, report = run(refresh=True)
    assert [branch['name'] for branch in report['stacks'][0]['branches']] == ['two', 'one']
    assert report['stacks'][0]['structure_observation']['complete'] is True
    assert code == 1  # The old recorded bases must not validate the reordered chain.


@pytest.mark.parametrize('rest_state,cached_state', [('OPEN', 'CLOSED'), ('CLOSED', 'OPEN'), ('OPEN', 'MERGED')])
@pytest.mark.parametrize('freshness', ['stale', 'unknown', None])
def test_stale_detail_state_cannot_retire_or_reactivate_fresh_rest_layer(harness, rest_state, cached_state, freshness):
    _, client, run = harness
    body = remote_stack()
    body['pull_requests'][-1]['state'] = rest_state.lower()
    client.refresh_stack.return_value = body
    original_details = client.pr_details.side_effect
    def stale_details(numbers, **kwargs):
        result = original_details(numbers, **kwargs)
        result[12]['state'] = cached_state
        if freshness is None:
            client.observations[12].pop('state')
        else:
            client.observations[12]['state'] = {'source': 'GraphQL', 'freshness': freshness, 'observed_at': 50}
        return result
    client.pr_details.side_effect = stale_details
    _, report = run(refresh=True)
    branch = report['stacks'][0]['branches'][-1]
    row = report['stacks'][0]['rows'][-1]
    assert branch['pr']['state'] == rest_state
    assert branch['isMerged'] is False
    assert row['merged'] is False
    assert branch['lifecycle_observation'] == client.stack_observations[42]
    assert any('PR #12 is CLOSED' in problem for problem in report['stacks'][0]['problems']) == (rest_state == 'CLOSED')
    assert report['stacks'][0]['structure_observation']['complete'] is True
    client.refresh_stack.assert_called_once_with(42, force=True)
    assert client.pr_details.call_count == 1


@pytest.mark.parametrize('new_state', ['CLOSED', 'MERGED'])
def test_fresh_detail_lifecycle_still_overrides_earlier_rest_state(harness, new_state):
    _, client, run = harness
    original_details = client.pr_details.side_effect
    def fresh_details(numbers, **kwargs):
        result = original_details(numbers, **kwargs)
        result[12]['state'] = new_state
        client.observations[12]['state'] = {'source': 'GraphQL', 'freshness': 'fresh', 'observed_at': 101}
        return result
    client.pr_details.side_effect = fresh_details
    _, report = run(refresh=True)
    branch = report['stacks'][0]['branches'][-1]
    assert branch['pr']['state'] == new_state
    assert branch['isMerged'] == (new_state == 'MERGED')
    assert branch['lifecycle_observation']['source'] == 'GraphQL'


@pytest.mark.parametrize('flags', [{}, {'refresh_status': True}, {'refresh_git': True}, {'no_pr': True}])
def test_ordinary_and_field_only_requests_do_not_scan_structure(harness, flags):
    _, client, run = harness
    _, report = run(**flags)
    client.refresh_stack.assert_not_called()
    observation = report['stacks'][0]['structure_observation']
    assert observation == {'source': 'local_catalog', 'freshness': 'unknown', 'complete': False, 'observed_at': None}


@pytest.mark.parametrize('body,observation', [
    (None, {'freshness': 'unknown', 'complete': False}),
    (None, {'freshness': 'stale', 'complete': False, 'reason': 'Stack structural response incomplete'}),
    (remote_stack(), {'freshness': 'stale', 'complete': True}),
    (remote_stack(), {'freshness': 'fresh', 'complete': False}),
    ({**remote_stack(), 'number': 43}, {'freshness': 'fresh', 'complete': True}),
    ({**remote_stack(), 'pull_requests': []}, {'freshness': 'fresh', 'complete': True}),
])
def test_failed_or_incomplete_refresh_never_falls_back(harness, body, observation):
    _, client, run = harness
    client.refresh_stack.return_value = body
    client.stack_observations = {42: observation}
    with pytest.raises(view.ToolError) as error:
        run(refresh=True)
    assert error.value.code == 'STATE.STACK_STRUCTURE_UNKNOWN'
    client.refresh_git.assert_not_called()
    client.pr_details.assert_not_called()


def test_known_stack_without_number_fails_actionably(harness):
    snapshot, client, run = harness
    snapshot['stacks'][0].pop('number')
    with pytest.raises(view.ToolError) as error:
        run(refresh=True, stack='one')
    assert error.value.code == 'STATE.STACK_NUMBER_UNKNOWN'
    client.refresh_stack.assert_not_called()
    client.refresh_git.assert_not_called()


def test_full_refresh_rejects_remote_trunk_change_outside_filter(harness):
    _, client, run = harness
    body = remote_stack()
    body['base']['ref'] = 'develop'
    client.refresh_stack.return_value = body
    with pytest.raises(view.ToolError) as error:
        run(refresh=True, trunk_filter='main')
    assert error.value.code == 'STATE.SNAPSHOT_CHANGED'
    client.refresh_git.assert_not_called()


def test_refresh_help_does_not_claim_structure_support_for_chain():
    chain_parser, view_parser = argparse.ArgumentParser(), argparse.ArgumentParser()
    view.add_refresh_options(chain_parser)
    view.add_refresh_options(view_parser, include_structure=True)
    assert 'membership' not in chain_parser.format_help()
    assert 'membership' in view_parser.format_help()


@pytest.mark.parametrize('change', ['membership', 'number', 'trunk', 'recorded_base', 'digest'])
def test_catalog_changes_across_fetch_are_not_hidden_by_new_epoch(harness, change):
    snapshot, client, run = harness
    refreshed = copy.deepcopy(snapshot)
    refreshed['fingerprint'] = 'new'
    if change == 'membership':
        refreshed['stacks'][0]['branches'].pop()
    elif change == 'number':
        refreshed['stacks'][0]['number'] = 99
    elif change == 'trunk':
        refreshed['stacks'][0]['trunk'] = 'develop'
    elif change == 'recorded_base':
        refreshed['stacks'][0]['branches'][0]['base'] = 'e' * 40
    else:
        refreshed['catalogs'][0]['digest'] = 'changed'
    with pytest.raises(view.ToolError) as error:
        run(snapshots=[snapshot, refreshed, refreshed])
    assert error.value.code == 'STATE.SNAPSHOT_CHANGED'
    client.pr_details.assert_not_called()


def test_rest_composition_survives_ref_epoch_refresh(harness):
    snapshot, client, run = harness
    refreshed = copy.deepcopy(snapshot)
    refreshed['refs']['refs/heads/one'] = 'e' * 40
    refreshed['stacks'][0]['branches'][0]['head'] = 'e' * 40
    refreshed['fingerprint'] = 'new-refs-only'
    client.refresh_stack.return_value = remote_stack(('one', 'two', 'three'))
    _, report = run(refresh=True, snapshots=[snapshot, refreshed, refreshed])
    assert [branch['name'] for branch in report['stacks'][0]['branches']] == ['one', 'two', 'three']
    assert report['stacks'][0]['branches'][0]['head'] == 'e' * 40
    assert report['stacks'][0]['structure_observation']['complete'] is True


def test_final_catalog_change_cannot_be_projected_as_fresh_composition(harness):
    snapshot, client, run = harness
    final = copy.deepcopy(snapshot)
    final['fingerprint'] = 'catalog-changed-after-hosted-response'
    final['catalogs'][0]['digest'] = 'catalog-v2'
    final['stacks'][0]['branches'].pop()
    code, report = run(refresh=True, snapshots=[snapshot, snapshot, final], guard_errors=True)
    assert code == 2
    assert report['success'] is False
    assert report['error']['code'] == 'STATE.SNAPSHOT_CHANGED'
    assert 'stacks' not in report
    assert not list(client.cache_dir.glob('*-view-*.json'))
    if not shutil.which('jq'):
        return  # The shell projection is optional; the core CLI assertions above always run.
    # Exercise the actual documented projection, which also independently refuses
    # this error envelope even if a caller accidentally ignores the exit-2 guard.
    recipe = Path(__file__).resolve().parents[1] / 'skills/sc-gh-stack/references/recipe-evidence.md'
    projection = re.search(r"jq -e '\n(.*?)'\nelse", recipe.read_text(), re.S).group(1)
    result = subprocess.run(['jq', '-e', projection], input=json.dumps(report), text=True, capture_output=True)
    assert result.returncode == 4
    assert result.stdout == ''


@pytest.mark.parametrize('mutate', [
    lambda body: body.update(base={'ref': '--bad'}),
    lambda body: body['pull_requests'][0].update(number=0),
    lambda body: body['pull_requests'][0].update(number=True),
    lambda body: body['pull_requests'].append(copy.deepcopy(body['pull_requests'][0])),
    lambda body: body['pull_requests'][0]['head'].update(ref='main'),
    lambda body: body['pull_requests'][0]['head'].update(ref='bad..branch'),
    lambda body: body['pull_requests'][0].update(head=None),
    lambda body: body['pull_requests'][0].update(state=1),
    lambda body: body['pull_requests'][0].update(merged='false'),
    lambda body: body['pull_requests'][0].update(merged_at=123),
])
def test_invalid_remote_compositions_cannot_be_complete(harness, mutate):
    _, client, run = harness
    body = remote_stack()
    mutate(body)
    client.refresh_stack.return_value = body
    with pytest.raises(view.ToolError) as error:
        run(refresh=True)
    assert error.value.code == 'STATE.STACK_STRUCTURE_UNKNOWN'


def test_paginated_structural_failure_cannot_reuse_first_page(tmp_path):
    calls = []
    def transport(command, **kwargs):
        calls.append(command)
        endpoint = command[command.index('-i') + 1]
        assert command[:2] == ['gh', 'api']
        if endpoint.endswith('?page=2'):
            return subprocess.CompletedProcess(command, 1, 'HTTP/2 503\n\n{"message":"unavailable"}', '')
        body = json.dumps(remote_stack(('one',)))
        return subprocess.CompletedProcess(command, 0,
                                           'HTTP/2 200\nlink: <https://api.github.test/repos/org/repo/stacks/42?page=2>; rel="next"\n\n' + body, '')
    repository = {'root': str(tmp_path), 'common_dir': str(tmp_path / '.git'), 'host': 'github.test',
                  'owner': 'org', 'name': 'repo', 'auth_identity': 'test', 'cooldown_dir': str(tmp_path / 'pressure')}
    client = StackDataClient(repository, run_fn=transport)
    with pytest.raises(view.ToolError) as error:
        view._refresh_structure(client, 42, {}, force=True, require_fresh=True)
    assert error.value.code == 'STATE.STACK_STRUCTURE_UNKNOWN'
    assert len(calls) == 2
    assert client.stack_observations[42]['complete'] is False
