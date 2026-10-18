"""Head qualification, negative observations and selector contract; offline only."""
import contextlib
import json
import subprocess
from unittest import mock

import pytest

import test_gh_stack_efficiency as efficiency
from gh_stack_shared import ToolError, parse_selector

chain = efficiency.chain


@pytest.mark.parametrize('kind', ['stack', 'layer'])
@pytest.mark.parametrize('value', ['0', '00', '²', '１２', 'number:²', 'pr:0', 'unknown:x', 'branch:'])
def test_invalid_selectors_are_typed(kind, value):
    with pytest.raises(ToolError) as error:
        parse_selector(value, kind=kind)
    assert error.value.code == 'INPUT.INVALID_SELECTOR'


@pytest.mark.parametrize('value,kind,expected', [
    ('123', 'layer', ('number', 123)), ('pr:123', 'layer', ('number', 123)),
    ('number:123', 'stack', ('number', 123)), ('branch:123', 'layer', ('branch', '123')),
    ('branch:１２', 'layer', ('branch', '１２')), ('id:S_42', 'stack', ('id', 'S_42')),
    ('topic/a', 'stack', ('auto', 'topic/a')), ('topic/a', 'layer', ('branch', 'topic/a')),
])
def test_selector_disambiguation(value, kind, expected):
    assert parse_selector(value, kind=kind) == expected


def test_layer_ids_are_not_stack_ids():
    with pytest.raises(ToolError):
        parse_selector('id:S_42', kind='layer')


@pytest.mark.parametrize('value,kind', [('pr:125', 'stack'), ('number:125', 'layer')])
def test_numeric_prefixes_cannot_cross_identifier_namespaces(value, kind):
    with pytest.raises(ToolError) as error:
        parse_selector(value, kind=kind)
    assert error.value.code == 'INPUT.INVALID_SELECTOR'


@contextlib.contextmanager
def fixture():
    instance = efficiency.EfficiencyIntegrationTests()
    instance.setUp()
    try:
        yield instance
    finally:
        instance.doCleanups()


def test_stale_tracking_heads_do_not_invalidate_current_hosted_metadata():
    with fixture() as f:
        f.sha = 'b' * 40  # Hosted heads move, but local tracking refs stay old.
        _, text, _ = f.cli(chain, ['--trunk', 'main', '1', '2', '3', '--no-fetch', '--json'])
        first = json.loads(text)
        assert len(f.gh_calls()) == 1
        assert all(pr['headRefOid']['freshness'] == 'fresh' for pr in first['observations'].values())
        assert all(row['pushed'] is None and row['pr_head_ok'] is None for row in first['rows'])
        _, text, _ = f.cli(chain, ['--trunk', 'main', '1', '2', '3', '--no-fetch', '--json'])
        assert len(f.gh_calls()) == 1
        assert json.loads(text)['linkable'] is None


def test_unmapped_branch_does_not_reread_metadata_against_stale_tracking_head():
    with fixture() as f:
        f.catalog.unlink()
        f.sha = 'b' * 40
        original = f.transport
        def transport(command, **kwargs):
            if command[0] != 'gh':
                return original(command, **kwargs)
            f.commands.append(command)
            assert any('/pulls?' in value for value in command), 'Mapping already supplied required metadata'
            pr = dict(number=1, state='open', draft=False, head={
                'ref': 'layer/1', 'sha': f.sha, 'repo': {'full_name': 'org/repo'}}, base={'ref': 'main'})
            return subprocess.CompletedProcess(command, 0, 'HTTP/2 200\n\n' + json.dumps([pr]), '')
        with mock.patch.object(chain, 'run', side_effect=transport):
            _, text, _ = f.cli(chain, ['--trunk', 'main', 'layer/1', '--no-fetch', '--json'])
        assert len(f.gh_calls()) == 1
        assert json.loads(text)['observations']['1']['headRefOid']['freshness'] == 'fresh'


def test_fresh_positive_ref_heads_still_invalidate_old_hosted_metadata():
    with fixture() as f:
        arguments = ['--trunk', 'main', '1', '2', '3', '--json']
        f.cli(chain, arguments)
        assert len(f.gh_calls()) == 1
        # Keep real refs on commits; a second commit supplies a genuine new head.
        (f.root / 'file').write_text('new head\n')
        f.git('add', 'file')
        f.git('commit', '-m', 'new head')
        f.sha = f.git('rev-parse', 'HEAD').strip()
        for number in (1, 2, 3):
            f.git('update-ref', 'refs/remotes/origin/layer/' + str(number), f.sha)
        _, text, _ = f.cli(chain, [*arguments, '--no-fetch'])
        report = json.loads(text)
        assert len(f.gh_calls()) == 2
        assert all(pr['headRefOid']['freshness'] == 'fresh' for pr in report['observations'].values())
        assert all(row['pr_head_ok'] is True for row in report['rows'])


def test_chain_negative_git_observation_survives_final_row_override():
    with fixture() as f:
        observation = {'fresh': False, 'source': 'cached', 'observed_at': 1, 'refs': {
            'main': {'fresh': True, 'exists': True},
            'layer/1': {'fresh': False, 'exists': False, 'absence_fresh': True, 'observed_at': 1}}}
        with mock.patch.object(efficiency.StackDataClient, 'refresh_git', return_value=observation):
            code, text, _ = f.cli(chain, ['--trunk', 'main', '1', '--no-fetch', '--no-pr', '--json'])
        report = json.loads(text)
        assert code == 1
        assert report['rows'][0]['pushed'] is False
        assert report['rows'][0]['origin'] is None
        assert any('unpushed' in problem for problem in report['problems'])
        assert report['linkable'] is False


def test_chain_numeric_branch_and_explicit_pr_selectors():
    with fixture() as f:
        f.git('update-ref', 'refs/heads/123', f.sha)
        f.git('update-ref', 'refs/remotes/origin/123', f.sha)
        catalog = json.loads(f.catalog.read_text())
        catalog['stacks'][0]['branches'][0]['branch'] = '123'
        f.catalog.write_text(json.dumps(catalog))
        for selector in ('branch:123', 'pr:1'):
            _, text, _ = f.cli(chain, ['--trunk', 'main', selector, '--no-fetch', '--no-pr', '--json'])
            assert json.loads(text)['rows'][0]['branch'] == '123'
        assert not f.gh_calls()


def test_chain_invalid_numeric_selector_refused_before_acquisition():
    with fixture() as f:
        code, text, _ = f.cli(chain, ['--trunk', 'main', '²', '--json'])
        assert code == 2
        assert json.loads(text)['error']['code'] == 'INPUT.INVALID_SELECTOR'
        assert not f.gh_calls()
        assert not any(cmd[:2] == ['git', 'fetch'] for cmd in f.commands)


@pytest.mark.parametrize('selector', ['', 'branch:bad..ref', 'pr:125'])
def test_chain_invalid_stack_selector_refused_before_empty_catalog_discovery(selector):
    with fixture() as f:
        f.catalog.unlink()
        with mock.patch.object(chain, 'read_local_snapshot') as discover, \
             mock.patch.object(chain, 'StackDataClient') as client:
            code, text, _ = f.cli(chain, ['--trunk', 'main', 'layer/1', '--stack', selector, '--json'])
        assert code == 2
        assert json.loads(text)['error']['code'] == 'INPUT.INVALID_SELECTOR'
        discover.assert_not_called()
        client.assert_not_called()
        assert not f.gh_calls()
