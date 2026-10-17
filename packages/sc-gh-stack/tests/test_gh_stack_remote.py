"""Deterministic request-budget and observation tests; never contacts GitHub."""
import concurrent.futures
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from gh_stack_remote import StackDataClient


def response(body, status=200, headers=None):
    text = 'HTTP/2 %s\n' % status
    text += ''.join('%s: %s\n' % pair for pair in (headers or {}).items())
    return subprocess.CompletedProcess([], 0 if status < 400 else 1, text + '\n' + (json.dumps(body) if body is not None else ''), '')


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = dict(root=str(self.root), common_dir=str(self.root / '.git'), host='github.test', owner='org', name='repo', auth_identity='tester', cooldown_dir=str(self.root / 'pressure'))
        self.now = [1000]
        self.calls = []
        self.sha = 'abc'
        self.state = 'SUCCESS'

    def transport(self, cmd, **kwargs):
        self.calls.append(cmd)
        self.assertEqual(cmd[:2], ['gh', 'api'])
        self.assertNotIn('reviewDecision', ' '.join(cmd))
        if 'graphql' in cmd:
            numbers = re.findall(r'p(\d+):pullRequest', ' '.join(cmd))
            return response({'data': {'repository': {'p' + n: dict(number=int(n), state='OPEN', isDraft=False, baseRefName='main', headRefName='branch' + n, baseRefOid='base', headRefOid=self.sha, mergeable='MERGEABLE', mergeStateStatus='CLEAN', commits={'nodes': [{'commit': {'statusCheckRollup': {'state': self.state}}}]}) for n in numbers}, 'rateLimit': {'cost': 1}}})
        number = int(cmd[cmd.index('-i') + 1].split('/')[-1])
        return response(dict(number=number, state='open', draft=False, head={'ref': 'branch' + str(number), 'sha': self.sha}, base={'ref': 'main', 'sha': 'base'}), headers={'etag': 'etag1'})

    def client(self, fn=None, repo=None):
        return StackDataClient(repo or self.repo, run_fn=fn or self.transport, clock=lambda: self.now[0])

    def test_120_prs_three_serial_batches_warm_offline(self):
        client = self.client()
        self.assertEqual(len(client.pr_details(list(range(1, 121)))), 120)
        self.assertEqual(client.metrics['graphql_requests'], 3)
        self.assertTrue(all(len(re.findall('pullRequest', ' '.join(c))) <= 50 for c in self.calls))
        warm = self.client()
        self.assertEqual(len(warm.pr_details(list(range(1, 121)))), 120)
        self.assertEqual(warm.metrics['requests'], 0)
        self.assertEqual(self.client().pr_metadata([999], offline=True), {})
        self.assertEqual(len(self.calls), 3)

    def test_same_sha_expires_and_changed_head_invalidates(self):
        self.client().pr_details([1])
        self.now[0] += 121
        self.state = 'FAILURE'
        self.assertEqual(self.client().pr_details([1])[1]['ci'], 'FAILURE')
        self.sha = 'new'
        self.assertEqual(self.client().pr_details([1], head_map={1: 'new'})[1]['headRefOid'], 'new')
        self.assertEqual(len(self.calls), 3)

    def test_running_ttl_60(self):
        self.state = 'PENDING'
        self.client().pr_details([1])
        self.now[0] += 61
        self.client().pr_details([1])
        self.assertEqual(len(self.calls), 2)

    def test_one_deadline_bounds_entire_request_sequence(self):
        ticks = [0.0]
        timeouts = []
        def slow(cmd, **kwargs):
            timeouts.append(kwargs['timeout'])
            result = self.transport(cmd, **kwargs)
            ticks[0] += 31
            return result
        client = StackDataClient(self.repo, run_fn=slow, clock=lambda: self.now[0],
                                 deadline_seconds=30, monotonic=lambda: ticks[0])
        result = client.pr_details(list(range(1, 121)))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(result), 50)
        self.assertEqual(timeouts, [30])
        self.assertTrue(any('deadline' in warning for warning in client.warnings))
        client.resolve_branches(['missing'])
        self.assertEqual(len(self.calls), 1, 'deadline stops later acquisition methods too')

    def test_clock_regression_does_not_make_future_observations_fresh(self):
        self.client().pr_details([1])
        self.now[0] -= 10
        client = self.client()
        client.pr_details([1], offline=True)
        self.assertEqual(client.observations[1]['ci']['freshness'], 'stale')

    def test_failed_forced_refresh_never_reuses_old_green_as_fresh(self):
        self.client().pr_details([1])
        client = self.client(lambda *args, **kwargs: response({'message': 'Bad credentials'}, 401))
        result = client.pr_details([1], force=True)
        self.assertEqual(result[1]['ci'], 'SUCCESS', 'retain useful prior value')
        self.assertEqual(client.observations[1]['ci']['freshness'], 'stale')
        self.assertIn('refresh', client.observations[1]['ci']['reason'])
        offline = self.client()
        offline.pr_details([1], offline=True)
        self.assertEqual(offline.observations[1]['ci']['freshness'], 'stale')

    def test_unresolved_nodes_are_unknown_without_hot_looping(self):
        def unresolved(cmd, **kwargs):
            self.calls.append(cmd)
            return response({'data': {'repository': {'p1': None}, 'rateLimit': {'cost': 1}}})
        self.assertEqual(self.client(unresolved).pr_details([1]), {})
        cached = self.client(unresolved)
        self.assertEqual(cached.pr_details([1]), {})
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(cached.observations[1]['ci']['freshness'], 'unknown')
        self.now[0] += 61
        self.client(unresolved).pr_details([1])
        self.assertEqual(len(self.calls), 2)

    def test_metadata_rest_etag_304(self):
        self.client().pr_metadata([1])
        self.now[0] += 121
        def cached(cmd, **kwargs):
            self.calls.append(cmd)
            self.assertIn('If-None-Match: etag1', cmd)
            return response(None, 304)
        client = self.client(cached)
        self.assertEqual(client.pr_metadata([1])[1]['number'], 1)
        self.assertEqual(client.observations[1]['state']['freshness'], 'fresh')

    def test_errors_stop_batches_no_fallback(self):
        for status, body in ((200, {'data': {'repository': {}}, 'errors': [{'message': 'partial failure'}]}), (401, {'message': 'Bad credentials'}), (403, {'message': 'Forbidden'}), (429, {'message': 'limited'})):
            with self.subTest(status=status):
                repo = dict(self.repo, auth_identity=str(status), cooldown_dir=str(self.root / ('pressure' + str(status))))
                client = self.client(lambda *a, **kw: response(body, status), repo)
                self.assertEqual(client.pr_details(list(range(1, 121))), {})
                self.assertEqual(client.metrics['requests'], 1)
                self.assertTrue(client.warnings)

    def test_shared_cooldown_across_repositories(self):
        first = self.client(lambda *a, **kw: response({'message': 'secondary rate limit'}, 403, {'Retry-After': '180'}))
        first.pr_details([1])
        second = self.client(repo=dict(self.repo, name='other'))
        second.pr_metadata([1])
        self.assertEqual(second.metrics['requests'], 0)
        self.assertTrue(any('cooldown' in w for w in second.warnings))

    def test_ten_concurrent_readers_one_sequence(self):
        guard = threading.Lock()
        def slow(cmd, **kwargs):
            time.sleep(.02)
            with guard:
                return self.transport(cmd, **kwargs)
        def read(_):
            return self.client(slow).pr_details(list(range(1, 121)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(read, range(10)))
        self.assertTrue(all(len(r) == 120 for r in results))
        self.assertEqual(len(self.calls), 3)
        def forced(_):
            return self.client(slow).pr_details(list(range(1, 121)), force=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(forced, range(10)))
        self.assertTrue(all(len(r) == 120 for r in results))
        self.assertEqual(len(self.calls), 6)

    def test_disjoint_scope_and_auth(self):
        self.client().pr_details([1])
        self.client().pr_details([2])
        self.client(repo=dict(self.repo, auth_identity='other')).pr_details([1])
        self.assertEqual(len(self.calls), 3)

    def test_missing_ci_not_green_and_offline_old_head(self):
        def incomplete(cmd, **kwargs):
            return response({'data': {'repository': {'p1': {'number': 1, 'headRefOid': 'old'}}}})
        client = self.client(incomplete)
        self.assertNotIn('ci', client.pr_details([1])[1])
        self.assertEqual(client.observations[1]['ci']['freshness'], 'unknown')
        result = self.client().pr_details([1], offline=True, head_map={1: 'new'})
        self.assertIsNone(result[1]['ci'])

    def test_targeted_branch_and_invalidation(self):
        def branch(cmd, **kwargs):
            self.calls.append(cmd)
            self.assertIn('head=org%3Atopic', ' '.join(cmd))
            return response([dict(number=1, state='open', head={'ref': 'topic', 'sha': 'a', 'repo': {'full_name': 'org/repo'}}, base={'ref': 'main', 'sha': 'b'})])
        client = self.client(branch)
        self.assertEqual(client.resolve_branches(['topic'])['topic']['number'], 1)
        self.assertEqual(self.client().pr_metadata([1], offline=True)[1]['number'], 1)
        client.invalidate([1])
        self.assertEqual(client.pr_metadata([1], offline=True), {})

    def test_stack_pagination(self):
        calls = []
        def pages(cmd, **kwargs):
            calls.append(cmd)
            return response({'number': 42, 'pull_requests': [{'number': len(calls)}]}, headers={'link': '<https://api.github.test/repos/org/repo/stacks/42?page=2>; rel="next"'} if len(calls) == 1 else {})
        result = self.client(pages).refresh_stack(42)
        self.assertEqual(len(result['pull_requests']), 2)
        self.assertEqual(len(calls), 2)

    def test_token_partition_and_unknown_host_cooldown(self):
        repo = dict(self.repo, auth_identity=None, identity='repo-identity', host='github.com')
        with patch.dict('os.environ', {'GH_TOKEN': 'token-one'}):
            one = self.client(repo=repo)
            one.pr_details([1])
        with patch.dict('os.environ', {'GH_TOKEN': 'token-two'}):
            two = self.client(repo=repo)
            two.pr_details([1])
        self.assertNotEqual(one.path, two.path)
        self.assertEqual(one.pressure_path, two.pressure_path)
        self.assertNotIn('token-', one.path.read_text())
        other = self.client(repo=dict(repo, identity='other-repo', name='other'))
        self.assertEqual(one.pressure_path, other.pressure_path)

    def test_validation_and_missing_identity(self):
        client = self.client(repo=dict(self.repo, owner=None))
        self.assertEqual(client.pr_details([1]), {})
        self.assertEqual(client.metrics['requests'], 0)
        for value in (True, '1', -1, '1){evil}'):
            with self.assertRaises(ValueError):
                self.client().pr_details([value])

    def test_portable_lock_fallback(self):
        with patch('gh_stack_remote.fcntl', None):
            self.assertEqual(self.client().pr_details([1])[1]['number'], 1)
        self.assertFalse(list(self.root.rglob('*.exclusive')))

    def test_incomplete_structural_and_branch_pagination(self):
        def pages(cmd, **kwargs):
            return response({'pull_requests': [1]}, headers={'link': '<https://evil.test/next>; rel="next"'})
        self.assertIsNone(self.client(pages).refresh_stack(1))
        def branch(cmd, **kwargs):
            return response([dict(number=1, state='open', head={'ref': 'topic', 'sha': 'a'}, base={'ref': 'main', 'sha': 'b'})], headers={'link': '<https://api.github.test/next>; rel="next"'})
        self.assertEqual(self.client(branch).resolve_branches(['topic']), {})

    def test_shared_git_fetch_force_concurrency_and_offline(self):
        calls = []
        def fetch(cmd, **kwargs):
            calls.append(cmd)
            time.sleep(.03)
            return subprocess.CompletedProcess(cmd, 0, '', '')
        def refresh(_):
            return self.client(fetch).refresh_git(force=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(refresh, range(10)))
        self.assertEqual(calls, [['git', 'fetch', '--quiet', '--', 'origin']])
        self.assertTrue(all(r['fresh'] for r in results))
        self.assertEqual(sum(r['source'] == 'fetched' for r in results), 1)
        self.assertEqual(self.client(fetch).refresh_git(offline=True)['source'], 'cached')
        self.now[0] += 61
        self.assertEqual(self.client(fetch).refresh_git(offline=True)['source'], 'stale')
        self.assertEqual(len(calls), 1)

    def test_git_fetch_failure_cooldown(self):
        calls = []
        def fail(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 1, '', 'network unavailable')
        first = self.client(fail).refresh_git()
        second = self.client(fail).refresh_git(force=True)
        self.assertFalse(first['fresh'])
        self.assertFalse(second['fresh'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(first['error'], 'network unavailable')

    def test_bulk_branch_mapping_120_three_batches_reused_metadata_and_force_coalescing(self):
        calls = []
        guard = threading.Lock()
        branches = ['topic' + str(n) for n in range(1, 121)]
        def bulk(cmd, **kwargs):
            time.sleep(.01)
            query = next(value[6:] for value in cmd if value.startswith('query='))
            self.assertNotIn('baseRefOid', query)
            aliases = re.findall(r'b(\d+):pullRequests\(headRefName:("[^"]*")', query)
            self.assertLessEqual(len(aliases), 50)
            with guard:
                calls.append(cmd)
            repository = {}
            for alias, encoded in aliases:
                owner, branch = json.loads(encoded).split(':', 1)
                self.assertEqual(owner, 'org')
                number = int(branch.removeprefix('topic'))
                pr = dict(number=number, state='OPEN', isDraft=False, baseRefName='main', headRefName=branch, headRefOid=self.sha, headRepository={'nameWithOwner': 'org/repo'})
                repository['b' + alias] = {'nodes': [pr], 'pageInfo': {'hasNextPage': False}}
            return response({'data': {'repository': repository, 'rateLimit': {'cost': 1}}})
        client = self.client(bulk)
        self.assertEqual(len(client.resolve_branches(branches)), 120)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(client.pr_metadata(list(range(1, 121)))), 120)
        self.assertEqual(len(calls), 3)
        warm = self.client(bulk)
        self.assertEqual(len(warm.resolve_branches(branches)), 120)
        self.assertEqual(warm.observations[1]['state']['freshness'], 'fresh')
        self.assertEqual(len(calls), 3)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: self.client(bulk).resolve_branches(branches, force=True), range(10)))
        self.assertTrue(all(len(result) == 120 for result in results))
        self.assertEqual(len(calls), 6)

    def test_branch_absence_positive_unknown_and_head_repository_validation(self):
        def empty(cmd, **kwargs):
            self.calls.append(cmd)
            return response([])
        client = self.client(empty)
        self.assertEqual(client.resolve_branches(['new']), {})
        observation = client.branch_observations['new']
        self.assertEqual((observation['state'], observation['exists'], observation['freshness']), ('negative', False, 'fresh'))
        client.resolve_branches(['new'])
        self.assertEqual(len(self.calls), 1)
        self.now[0] += 121
        client.resolve_branches(['new'], offline=True)
        self.assertIsNone(client.branch_observations['new']['exists'])
        def ambiguous(cmd, **kwargs):
            nodes = [dict(number=n, state='OPEN', isDraft=False, baseRefName='main', headRefName='a', headRefOid='head', headRepository={'nameWithOwner': 'org/repo'}) for n in (1, 2)]
            return response({'data': {'repository': {
                'b0': {'nodes': nodes, 'pageInfo': {'hasNextPage': False}},
                'b1': {'nodes': [], 'pageInfo': {'hasNextPage': True}},
                'b2': {'nodes': [{**nodes[0], 'headRefName': 'c', 'headRepository': {'nameWithOwner': 'other/repo'}}], 'pageInfo': {'hasNextPage': False}},
            }}})
        client = self.client(ambiguous)
        self.assertEqual(client.resolve_branches(['a', 'b', 'c']), {})
        self.assertIsNone(client.branch_observations['a']['exists'])
        self.assertIsNone(client.branch_observations['b']['exists'])
        self.assertIs(client.branch_observations['c']['exists'], False)

    def test_failed_acquisition_stays_stopped_across_methods(self):
        def denied(cmd, **kwargs):
            self.calls.append(cmd)
            return response({'message': 'Bad credentials'}, 401)
        client = self.client(denied)
        client.pr_details([1])
        client.resolve_branches(['a', 'b', 'c'])
        client.refresh_stack(1)
        client.pr_metadata([2])
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(all(value['exists'] is None for value in client.branch_observations.values()))

    def test_stack_warm_force_coalescing_and_link_removal(self):
        calls = []
        phase = [0]
        def pages(cmd, **kwargs):
            time.sleep(.02)
            calls.append(cmd)
            endpoint = cmd[cmd.index('-i') + 1]
            next_page = phase[0] == 0 and '?' not in endpoint
            return response({'number': 42, 'pull_requests': [{'number': 1}]}, headers={'link': '<https://api.github.test/repos/org/repo/stacks/42?page=2>; rel="next"'} if next_page else {})
        self.assertEqual(len(self.client(pages).refresh_stack(42)['pull_requests']), 2)
        self.assertEqual(len(self.client(pages).refresh_stack(42)['pull_requests']), 2)
        self.assertEqual(len(calls), 2)
        phase[0] = 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: self.client(pages).refresh_stack(42, force=True), range(10)))
        self.assertTrue(all(len(result['pull_requests']) == 1 for result in results))
        self.assertEqual(len(calls), 3)

    def test_enterprise_tokens_partition_without_public_token_interference(self):
        with patch.dict('os.environ', {'GH_ENTERPRISE_TOKEN': 'enterprise-one', 'GH_TOKEN': 'public-one'}):
            one = self.client()
            one.pr_details([1])
        with patch.dict('os.environ', {'GH_ENTERPRISE_TOKEN': 'enterprise-two', 'GH_TOKEN': 'public-one'}):
            two = self.client()
            two.pr_details([1])
        self.assertNotEqual(one.path, two.path)
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn('enterprise-', one.path.read_text())
        with patch.dict('os.environ', {'GH_ENTERPRISE_TOKEN': 'enterprise-one', 'GH_TOKEN': 'public-two'}):
            self.assertEqual(self.client().path, one.path)

    def test_malformed_cache_is_a_miss(self):
        for value in ([], {'schema': 1}, {'schema': 1, 'prs': [], 'rest': {}, 'branches': {}},
                      {'schema': 1, 'prs': {'1': []}, 'rest': {}, 'branches': {}}):
            with self.subTest(value=value):
                client = self.client()
                client.path.parent.mkdir(parents=True, exist_ok=True)
                client.path.write_text(json.dumps(value))
                self.assertEqual(client.pr_details([1])[1]['number'], 1)


if __name__ == '__main__':
    unittest.main()
