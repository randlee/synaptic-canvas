"""Partial response, conditional validation and cross-boot regressions; offline."""
import contextlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gh_stack_remote import GIT_ARGV_BUDGET, StackDataClient, _argv_units, _write


def response(body=None, status=200, code=None, headers=None):
    text = 'HTTP/2 %s\n' % status
    text += ''.join('%s: %s\n' % item for item in (headers or {}).items()) + '\n'
    return subprocess.CompletedProcess([], int(status >= 400) if code is None else code,
                                       text + (json.dumps(body) if body is not None else ''), '')


def pr(number, branch=None):
    return dict(number=number, state='OPEN', isDraft=False, baseRefName='main',
                headRefName=branch or 'layer/%s' % number, headRefOid='a' * 40,
                mergeable='MERGEABLE', mergeStateStatus='CLEAN',
                commits={'nodes': [{'commit': {'statusCheckRollup': {'state': 'SUCCESS'}}}]})


@pytest.fixture
def setup(tmp_path):
    repository = dict(root=str(tmp_path), common_dir=str(tmp_path / '.git'),
                      host='github.test', owner='org', name='repo', auth_identity='test',
                      cooldown_dir=str(tmp_path / 'pressure'))
    ticks = [1000.0]
    calls = []
    def client(transport, **kwargs):
        def invoke(cmd, **options):
            calls.append((cmd, options))
            return transport(cmd, **options)
        return StackDataClient(repository, run_fn=invoke, clock=lambda: ticks[0],
                               monotonic=lambda: ticks[0],
                               sleep=lambda delay: ticks.__setitem__(0, ticks[0] + delay), **kwargs)
    return client, ticks, calls


def graphql_success(cmd, **kwargs):
    numbers = re.findall(r'p(\d+):pullRequest', ' '.join(cmd))
    return response({'data': {'repository': {'p' + n: pr(int(n)) for n in numbers}}})


def test_partial_alias_keeps_119_results_and_continues_batches(setup):
    client, ticks, calls = setup
    def transport(cmd, **kwargs):
        result = graphql_success(cmd, **kwargs)
        if 'p2:pullRequest' in ' '.join(cmd):
            body = json.loads(result.stdout.split('\n\n', 1)[1])
            body['data']['repository']['p2'] = None
            body['errors'] = [dict(type='NOT_FOUND', message='Could not resolve PR 2', path=['repository', 'p2'])]
            return response(body, code=1)  # gh exits nonzero on GraphQL errors.
        return result
    reader = client(transport)
    result = reader.pr_details(list(range(1, 121)))
    assert len(result) == 119 and 2 not in result
    assert len(calls) == 3 and not reader._stopped
    assert reader.observations[1]['ci']['freshness'] == 'fresh'
    assert reader.observations[2]['ci']['freshness'] == 'unknown'
    assert len(client(transport).pr_details(list(range(1, 121)))) == 119
    assert len(calls) == 3, 'good aliases are reused and unavailable alias is retry-suppressed'


@pytest.mark.parametrize('path,missing', [
    (['repository', 'p1', 'commits', 'nodes', 0, 'commit', 'statusCheckRollup'], 'ci'),
    (['repository', 'p1', 'mergeable'], 'mergeable'),
])
def test_partial_field_keeps_unaffected_fields_without_manufacturing_none(setup, path, missing):
    client, _, _ = setup
    def transport(cmd, **kwargs):
        value = pr(1)
        value['commits']['nodes'][0]['commit']['statusCheckRollup'] = None
        return response({'data': {'repository': {'p1': value}},
                         'errors': [dict(type='INTERNAL', message='field resolver failed', path=path)]}, code=1)
    reader = client(transport)
    value = reader.pr_details([1])[1]
    assert missing not in value
    assert reader.observations[1][missing]['freshness'] == 'unknown'
    assert reader.observations[1]['state']['freshness'] == 'fresh'
    if missing == 'ci':
        assert value.get('ci') != 'NONE'


@pytest.mark.parametrize('error', [
    {'message': 'unscoped failure'},
    {'message': 'root failure', 'path': ['repository']},
    {'message': 'unknown field', 'path': ['other', 'p1']},
    {'type': 'FORBIDDEN', 'message': 'not permitted', 'path': ['repository', 'p2']},
    {'extensions': {'code': 'FORBIDDEN'}, 'message': 'not permitted', 'path': ['repository', 'p2']},
    {'extensions': {'code': 'RATE_LIMITED'}, 'message': 'limited', 'path': ['repository', 'p2']},
])
def test_global_or_unscoped_error_stops_and_does_not_certify_partial_data(setup, error):
    client, _, calls = setup
    reader = client(lambda *a, **k: response({'data': {'repository': {'p1': pr(1)}}, 'errors': [error]}, code=1))
    assert reader.pr_details(list(range(1, 121))) == {}
    assert len(calls) == 1 and reader._stopped


def test_partial_mapping_connection_never_certifies_absence(setup):
    client, _, calls = setup
    def transport(*args, **kwargs):
        return response({'data': {'repository': {
            'b0': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
            'b1': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
            'b2': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
        }}, 'errors': [dict(type='NOT_FOUND', message='mapping unavailable', path=['repository', 'b0', 'nodes'])]}, code=1)
    reader = client(transport)
    assert reader.resolve_branches(['a', 'b', 'c']) == {}
    assert reader.branch_observations['a']['exists'] is None
    assert reader.branch_observations['b']['exists'] is False
    assert reader.branch_observations['c']['exists'] is False
    assert not reader._stopped
    client(transport).resolve_branches(['a', 'b', 'c'])
    assert len(calls) == 1


@pytest.mark.parametrize('branch', ['fix/secondary-parser', 'fix/rate_limit', 'fix/abuse-detection'])
def test_response_data_cannot_trigger_shared_throttle(setup, branch):
    client, _, _ = setup
    reader = client(lambda *a, **k: response({
        'data': {'repository': {'p1': pr(1, branch), 'p2': None}},
        'errors': [dict(type='NOT_FOUND', message='Could not resolve PR 2', path=['repository', 'p2'])]}, code=1))
    assert 1 in reader.pr_details([1, 2])
    assert not reader._stopped
    assert 'until' not in json.loads(reader.pressure_path.read_text())


def test_not_found_reference_name_is_not_a_rate_limit_code(setup):
    client, _, _ = setup
    reader = client(lambda *a, **k: response({
        'data': {'repository': {'p1': pr(1), 'p2': None}},
        'errors': [dict(type='NOT_FOUND', message='Could not resolve fix/rate_limit', path=['repository', 'p2'])]}, code=1))
    assert 1 in reader.pr_details([1, 2])
    assert 'until' not in json.loads(reader.pressure_path.read_text())


def test_not_found_branch_named_permission_is_not_authentication_failure(setup):
    client, _, _ = setup
    reader = client(lambda *a, **k: response({
        'data': {'repository': {'p1': pr(1), 'p2': None}},
        'errors': [dict(type='NOT_FOUND', message='Could not resolve fix/permission-parser', path=['repository', 'p2'])]}, code=1))
    assert 1 in reader.pr_details([1, 2])
    assert not reader._stopped


def test_nonzero_304_revalidates_and_allows_next_rest_request(setup):
    client, ticks, calls = setup
    def rest(cmd, **kwargs):
        number = int(cmd[cmd.index('-i') + 1].rsplit('/', 1)[1])
        return response(dict(number=number, state='open', draft=False,
                             head={'ref': 'branch', 'sha': 'a' * 40}, base={'ref': 'main'}), headers={'ETag': 'tag'})
    client(rest).pr_metadata([1])
    ticks[0] += 121
    def conditional(cmd, **kwargs):
        if cmd[cmd.index('-i') + 1].endswith('/1'):
            assert 'If-None-Match: tag' in cmd
            return response(status=304, code=1, headers={'ETag': 'tag'})
        return rest(cmd, **kwargs)
    reader = client(conditional)
    assert set(reader.pr_metadata([1, 2])) == {1, 2}
    assert reader.observations[1]['state']['freshness'] == 'fresh'
    assert len(calls) == 3 and not reader._stopped


def test_nonzero_304_keeps_pagination_and_allows_later_page(setup):
    client, ticks, calls = setup
    def pages(cmd, **kwargs):
        endpoint = cmd[cmd.index('-i') + 1]
        return response({'number': 42, 'pull_requests': [{'number': 2 if '?' in endpoint else 1}]},
                        headers={'ETag': 'tag', **({'Link': '<https://api.github.test/repos/org/repo/stacks/42?page=2>; rel="next"'} if '?' not in endpoint else {})})
    assert len(client(pages).refresh_stack(42)['pull_requests']) == 2
    ticks[0] += 121
    reader = client(lambda *a, **k: response(status=304, code=1, headers={'ETag': 'tag'}))
    assert len(reader.refresh_stack(42)['pull_requests']) == 2
    assert len(calls) == 4 and not reader._stopped


@pytest.mark.parametrize('old', [{}, {'etag': 'tag', 'body': None, 'time': 1000}, {'body': {'number': 1}, 'time': 1000}])
def test_304_without_matching_usable_cached_validator_is_not_fresh(setup, old):
    client, _, calls = setup
    reader = client(lambda *a, **k: response(status=304, code=1))
    data = reader._load()
    endpoint = 'repos/org/repo/pulls/1'
    data['rest'][endpoint] = old
    assert reader._rest(data, endpoint, force=True) is None
    assert reader._stopped
    assert all('If-None-Match: tag' not in cmd for cmd, _ in calls)


@pytest.mark.parametrize('body', ['null', 'malformed'])
def test_304_with_unexpected_entity_cannot_revalidate_cached_body(setup, body):
    client, _, _ = setup
    reader = client(lambda *a, **k: subprocess.CompletedProcess([], 1, 'HTTP/2 304\n\n' + body, ''))
    data = reader._load()
    endpoint = 'repos/org/repo/pulls/1'
    data['rest'][endpoint] = {'etag': 'tag', 'body': {'number': 1}, 'time': 900}
    assert reader._rest(data, endpoint, force=True) is None
    assert reader._stopped and data['rest'][endpoint]['time'] == 900


@pytest.mark.parametrize('code', [2, 130, -9])
@pytest.mark.parametrize('kind', ['304', 'partial'])
def test_non_graphql_failure_or_interruption_is_never_tolerated(setup, code, kind):
    client, _, calls = setup
    body = {'data': {'repository': {'p1': pr(1), 'p2': None}},
            'errors': [dict(type='NOT_FOUND', message='Could not resolve PR 2', path=['repository', 'p2'])]}
    reader = client(lambda *a, **k: response(body if kind == 'partial' else None, status=200 if kind == 'partial' else 304, code=code))
    if kind == 'partial':
        assert reader.pr_details(list(range(1, 121))) == {}
    else:
        data = reader._load()
        endpoint = 'repos/org/repo/pulls/1'
        data['rest'][endpoint] = {'etag': 'tag', 'body': {'number': 1}, 'time': 900}
        assert reader._rest(data, endpoint, force=True) is None
        assert data['rest'][endpoint]['time'] == 900
    assert reader._stopped and len(calls) == 1


def test_reboot_monotonic_cache_cannot_suppress_forced_pr_refresh(setup):
    client, _, calls = setup
    reader = client(graphql_success)
    reader.pr_details([1])
    data = reader._load()
    data['refreshes'] = {scope: 1e20 for scope in data['refreshes']}
    _write(reader.path, data)
    forced = client(graphql_success)
    forced.pr_details([1], force=True)
    assert len(calls) == 2
    assert all(isinstance(value, str) for value in forced._load()['refreshes'].values())


def test_reboot_monotonic_cache_cannot_suppress_forced_git_refresh(setup):
    client, _, calls = setup
    reader = client(lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, '', ''))
    reader.refresh_git(refs=['main'])
    path = next(reader.cache_dir.glob('git-*.json'))
    data = json.loads(path.read_text())
    data['refs']['main'].pop('revision')
    data['refs']['main']['completed_monotonic'] = 1e20
    _write(path, data)
    reader.refresh_git(refs=['main'], force=True)
    assert len(calls) == 2
    assert 'completed_monotonic' not in json.loads(path.read_text())['refs']['main']


def test_host_pressure_lock_can_use_remaining_deadline_beyond_five_seconds(setup):
    client, ticks, calls = setup
    reader = client(graphql_success)
    original = reader._lock
    @contextlib.contextmanager
    def simulated_wait(path, seconds=5):
        if path == reader.pressure_path.with_suffix('.lock'):
            assert seconds == 30
            ticks[0] += 6
        with original(path, seconds=seconds) as acquired:
            yield acquired
    reader._lock = simulated_wait
    assert reader.pr_details([1])[1]['number'] == 1
    assert calls[0][1]['timeout'] == 24


def test_repository_lock_wait_counts_toward_lazy_hosted_deadline(setup):
    client, ticks, calls = setup
    reader = client(graphql_success)
    original = reader._lock
    @contextlib.contextmanager
    def simulated_wait(path, seconds=5):
        if path == reader.lock_path:
            assert seconds == 30
            ticks[0] += 6
        with original(path, seconds=seconds) as acquired:
            yield acquired
    reader._lock = simulated_wait
    assert reader.pr_details([1])[1]['number'] == 1
    assert calls[0][1]['timeout'] == 24


def test_forced_partial_refresh_retains_old_ci_as_stale_not_fresh(setup):
    client, _, _ = setup
    client(graphql_success).pr_details([1])
    def broken_ci(*args, **kwargs):
        value = pr(1)
        value['commits'] = None
        return response({'data': {'repository': {'p1': value}},
                         'errors': [dict(message='resolver failed', path=['repository', 'p1', 'commits'])]}, code=1)
    reader = client(broken_ci)
    value = reader.pr_details([1], force=True)[1]
    assert value['ci'] == 'SUCCESS'
    assert reader.observations[1]['ci']['freshness'] == 'stale'
    assert reader.observations[1]['state']['freshness'] == 'fresh'


def test_successful_304_at_primary_exhaustion_keeps_current_result_but_stops_next_read(setup):
    client, ticks, calls = setup
    client(lambda *a, **k: response(dict(number=1, state='open', head={'sha': 'a', 'ref': 'a'}, base={'ref': 'main'}), headers={'ETag': 'tag'})).pr_metadata([1])
    ticks[0] += 121
    reader = client(lambda *a, **k: response(status=304, code=1, headers={'X-RateLimit-Remaining': '0'}))
    result = reader.pr_metadata([1, 2])
    assert set(result) == {1}
    assert reader.observations[1]['state']['freshness'] == 'fresh'
    assert reader._stopped and len(calls) == 2


def test_negative_git_observation_expires_and_failed_revalidation_is_not_absence(setup):
    client, ticks, calls = setup
    def missing(cmd, **kwargs):
        if cmd[1] == 'ls-remote':
            return subprocess.CompletedProcess(cmd, 0, '', '')
        return subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref gone")
    first = client(missing).refresh_git(refs=['gone'])['refs']['gone']
    assert first['exists'] is False and first['absence_fresh'] is True
    assert first['fresh'] is False and first['observed_at'] == ticks[0]
    cached = client(missing).refresh_git(refs=['gone'], offline=True)['refs']['gone']
    assert cached['absence_fresh'] is True and len(calls) == 2
    ticks[0] += 60
    expired = client(missing).refresh_git(refs=['gone'], offline=True)['refs']['gone']
    assert expired['absence_fresh'] is False
    failed = client(lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, '', 'network unavailable'))
    entry = failed.refresh_git(refs=['gone'])['refs']['gone']
    assert entry['exists'] is False and entry['absence_fresh'] is False and entry['fresh'] is False
    assert entry['observed_at'] == first['observed_at'] and entry['absence_error']
    assert len(calls) == 3
    failed.refresh_git(refs=['gone'], force=True)
    assert len(calls) == 3, 'ordinary transport failures retain 15s retry suppression'


def test_old_tracking_epoch_is_not_qualified_by_fresh_absence(setup):
    client, ticks, _ = setup
    reader = client(lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, '', ''))
    reader.refresh_git(refs=['gone'])
    ticks[0] += 61
    def missing(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, '', '') if cmd[1] == 'ls-remote' else subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref gone")
    entry = client(missing).refresh_git(refs=['gone'])['refs']['gone']
    assert entry['exists'] is False and entry['absence_fresh'] is True and entry['fresh'] is False


@pytest.mark.parametrize('kind', ['branches', 'stack'])
def test_reboot_monotonic_cache_cannot_suppress_other_forced_scopes(setup, kind):
    client, _, calls = setup
    reader = client(lambda *a, **k: response([] if kind == 'branches' else {'number': 42, 'pull_requests': []}))
    invoke = (lambda force=False: reader.resolve_branches(['a'], force=force)) if kind == 'branches' else (lambda force=False: reader.refresh_stack(42, force=force))
    invoke()
    data = reader._load()
    data['refreshes'] = {scope: 1e20 for scope in data['refreshes']}
    _write(reader.path, data)
    invoke(force=True)
    assert len(calls) == 2


def test_removed_revision_is_not_a_completed_forced_refresh(setup):
    client, _, calls = setup
    reader = client(graphql_success)
    reader.pr_details([1])
    original = reader._lock
    @contextlib.contextmanager
    def invalidated_while_waiting(path, seconds=5):
        with original(path, seconds=seconds) as acquired:
            if path == reader.lock_path:
                data = reader._load()
                data['refreshes'] = {}
                _write(reader.path, data)
            yield acquired
    reader._lock = invalidated_while_waiting
    reader.pr_details([1], force=True)
    assert len(calls) == 2


def test_local_invalidation_remains_available_after_hosted_deadline(setup):
    client, ticks, _ = setup
    reader = client(graphql_success)
    reader.pr_details([1])
    ticks[0] += 31
    reader.invalidate([1])
    assert reader.pr_details([1], offline=True) == {}


@pytest.mark.parametrize('failure', ['lock', 'deadline'])
def test_failed_forced_lock_never_certifies_prior_green_or_mutates_shared_cache(setup, failure):
    client, ticks, calls = setup
    seeded = client(graphql_success)
    seeded.pr_details([1])
    prior = seeded.path.read_bytes()
    reader = client(graphql_success)
    if failure == 'lock':
        @contextlib.contextmanager
        def unavailable():
            yield False
        reader._cache_lock = unavailable
    else:
        reader.deadline = ticks[0] - 1
    result = reader.pr_details([1], force=True)
    assert result[1]['ci'] == 'SUCCESS', 'retain the useful old value'
    assert reader.observations[1]['ci']['freshness'] == 'stale'
    assert 'lock' in reader.observations[1]['ci']['reason']
    assert seeded.path.read_bytes() == prior and len(calls) == 1
    ordinary = client(graphql_success)
    assert ordinary.pr_details([1])[1]['ci'] == 'SUCCESS'
    assert ordinary.observations[1]['ci']['freshness'] == 'fresh'
    assert len(calls) == 1


def test_completed_coalesced_refresh_can_remain_fresh_after_waiter_loses_lock(setup):
    client, _, calls = setup
    seeded = client(graphql_success)
    seeded.pr_details([1])
    reader = client(graphql_success)
    @contextlib.contextmanager
    def another_caller_completed():
        with seeded._lock(seeded.lock_path) as acquired:
            assert acquired
            data = seeded._load()
            for scope in list(data['refreshes']):
                seeded._complete_refresh(data, scope)
            seeded._save(data)
        yield False
    reader._cache_lock = another_caller_completed
    assert reader.pr_details([1], force=True)[1]['ci'] == 'SUCCESS'
    assert reader.observations[1]['ci']['freshness'] == 'fresh'
    assert len(calls) == 1


@pytest.mark.parametrize('stem', ['x' * 230, 'a"' * 110])
def test_long_git_scope_uses_stdin_and_bounded_advertisement_chunks(setup, stem):
    client, _, calls = setup
    branches = ['feature/' + stem + str(number) for number in range(120)]
    fetch_count = [0]
    def transport(cmd, **kwargs):
        if cmd[1] == 'fetch':
            fetch_count[0] += 1
            assert len(cmd) == 8 and '--stdin' in cmd
            assert kwargs['input'].count('\n') == 120
            if fetch_count[0] == 1:
                return subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref missing")
            return subprocess.CompletedProcess(cmd, 0, '', '')
        assert _argv_units(cmd) <= GIT_ARGV_BUDGET
        return subprocess.CompletedProcess(cmd, 0, ''.join('a' * 40 + '\t' + pattern + '\n' for pattern in cmd[5:]), '')
    reader = client(transport)
    assert reader.refresh_git(refs=branches)['fresh'] is True
    advertisements = [cmd for cmd, _ in calls if cmd[1] == 'ls-remote']
    assert len(advertisements) == 2
    assert sum(len(cmd) - 5 for cmd in advertisements) == 120
    assert reader.metrics['git_ref_discoveries'] == 2


def test_later_advertisement_failure_does_not_certify_earlier_chunk_absence(setup):
    client, _, _ = setup
    branches = ['feature/' + ('x' * 230) + str(number) for number in range(120)]
    advertisements = [0]
    def transport(cmd, **kwargs):
        if cmd[1] == 'fetch':
            return subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref missing")
        advertisements[0] += 1
        return subprocess.CompletedProcess(cmd, int(advertisements[0] == 2), '', 'network failure' if advertisements[0] == 2 else '')
    result = client(transport).refresh_git(refs=branches)
    assert advertisements[0] == 2
    assert all(not entry['absence_fresh'] and not entry['fresh'] for entry in result['refs'].values())
    assert all(entry.get('exists') is not False for entry in result['refs'].values())
