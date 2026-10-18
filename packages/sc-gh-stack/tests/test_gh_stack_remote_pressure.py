"""Offline regressions for shared failed-discovery and hosted request bounds."""
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gh_stack_remote import StackDataClient


def response(body, status=200):
    return subprocess.CompletedProcess([], int(status >= 400),
                                       'HTTP/2 %s\n\n%s' % (status, json.dumps(body)), '')


class RemotePressureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = dict(root=str(self.root), common_dir=str(self.root / '.git'),
                         host='github.test', owner='org', name='repo',
                         auth_identity='reader', cooldown_dir=str(self.root / 'pressure'))
        self.ticks = [1000.0]
        self.calls = []
        self.sleeps = []

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.ticks[0] += duration

    def client(self, transport=None, repo=None, **kwargs):
        return StackDataClient(repo or self.repo, run_fn=transport or self.denied,
                               clock=lambda: self.ticks[0], monotonic=lambda: self.ticks[0],
                               sleep=self.sleep, **kwargs)

    def denied(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        return response({'message': 'Forbidden'}, 403)

    def empty(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if 'graphql' not in cmd:
            return response([])
        query = next(arg[6:] for arg in cmd if arg.startswith('query='))
        aliases = re.findall(r'(b\d+):pullRequests', query)
        return response({'data': {'repository': {
            alias: {'nodes': [], 'pageInfo': {'hasNextPage': False}} for alias in aliases}}})

    def test_five_bulk_clients_share_failed_mapping_suppression(self):
        for _ in range(5):
            client = self.client()
            self.assertEqual(client.resolve_branches(['a', 'b', 'c']), {})
            self.assertTrue(all(obs['state'] == 'unknown' and obs['exists'] is None
                                for obs in client.branch_observations.values()))
        self.assertEqual(len(self.calls), 1)
        self.assertIn('graphql', self.calls[0][0])

    def test_five_targeted_clients_share_failed_mapping_suppression(self):
        for _ in range(5):
            client = self.client()
            self.assertEqual(client.resolve_branches(['a', 'b']), {})
            self.assertTrue(all(obs['exists'] is None for obs in client.branch_observations.values()))
        self.assertEqual(len(self.calls), 1, 'first failure also suppresses unattempted remainder')
        self.assertNotIn('graphql', self.calls[0][0])

    def test_failure_suppression_is_per_branch_across_overlapping_scopes(self):
        self.client().resolve_branches(['a', 'b', 'c'])
        retry = self.client(self.empty)
        retry.resolve_branches(['b', 'c', 'd'])
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn('graphql', self.calls[-1][0], 'only the newly requested branch is fetched')
        self.assertIsNone(retry.branch_observations['b']['exists'])
        self.assertIs(retry.branch_observations['d']['exists'], False)

    def test_retry_after_failure_ttl_and_success_replaces_unknown(self):
        self.client().resolve_branches(['a', 'b', 'c'])
        self.ticks[0] += 59
        self.client(self.empty).resolve_branches(['a', 'b', 'c'])
        self.assertEqual(len(self.calls), 1)
        self.ticks[0] += 1
        recovered = self.client(self.empty)
        recovered.resolve_branches(['a', 'b', 'c'])
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all(obs['state'] == 'negative' and obs['freshness'] == 'fresh'
                            for obs in recovered.branch_observations.values()))
        self.client(self.empty).resolve_branches(['a', 'b', 'c'])
        self.assertEqual(len(self.calls), 2)

    def test_explicit_force_can_retry_but_does_not_cache_failure_as_absence(self):
        self.client().resolve_branches(['a', 'b', 'c'])
        client = self.client(self.empty)
        client.resolve_branches(['a', 'b', 'c'], force=True)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all(obs['exists'] is False for obs in client.branch_observations.values()))

    def test_concurrent_forced_failures_are_coalesced(self):
        barrier = threading.Barrier(5)
        def slow_denied(cmd, **kwargs):
            time.sleep(.03)
            return self.denied(cmd, **kwargs)
        def resolve(_):
            client = self.client(slow_denied)
            barrier.wait()
            return client.resolve_branches(['a', 'b', 'c'], force=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            self.assertEqual(list(pool.map(resolve, range(5))), [{}] * 5)
        self.assertEqual(len(self.calls), 1)

    def test_incomplete_success_payload_is_unknown_and_shared(self):
        def partial(cmd, **kwargs):
            self.calls.append((cmd, kwargs))
            return response({'data': {'repository': {
                'b0': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
                'b1': {'nodes': [], 'pageInfo': {'hasNextPage': True}},
            }}})
        self.client(partial).resolve_branches(['a', 'b', 'c'])
        client = self.client(partial)
        client.resolve_branches(['a', 'b', 'c'])
        self.assertEqual(len(self.calls), 1)
        self.assertIs(client.branch_observations['a']['exists'], False)
        self.assertIsNone(client.branch_observations['b']['exists'])
        self.assertIsNone(client.branch_observations['c']['exists'])

    def test_failed_forced_mapping_does_not_repromote_prior_rest_body(self):
        def positive(cmd, **kwargs):
            self.calls.append((cmd, kwargs))
            return response([dict(number=1, state='open', draft=False, base={'ref': 'main'},
                                  head={'ref': 'a', 'sha': 'head', 'repo': {'full_name': 'org/repo'}})])
        self.assertIn('a', self.client(positive).resolve_branches(['a']))
        self.client().resolve_branches(['a'], force=True)
        cached = self.client(positive)
        self.assertEqual(cached.resolve_branches(['a']), {})
        self.assertEqual(cached.branch_observations['a']['freshness'], 'stale')
        self.ticks[0] += 61
        retry = self.client(self.empty)
        self.assertEqual(retry.resolve_branches(['a']), {})
        self.assertEqual(len(self.calls), 3, 'retry must actually revalidate old REST body')
        self.assertIs(retry.branch_observations['a']['exists'], False)

    def test_offline_read_does_not_suppress_later_online_mapping(self):
        self.client().resolve_branches(['a'], offline=True)
        self.client(self.empty).resolve_branches(['a'])
        self.assertEqual(len(self.calls), 1)

    def test_failed_mapping_cache_remains_auth_partitioned(self):
        self.client().resolve_branches(['a', 'b', 'c'])
        self.client(repo=dict(self.repo, auth_identity='other')).resolve_branches(['a', 'b', 'c'])
        self.assertEqual(len(self.calls), 2)

    def test_local_work_before_first_api_does_not_consume_hosted_deadline(self):
        client = self.client(self.empty)
        self.ticks[0] += 95
        client.resolve_branches(['a'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1]['timeout'], 30)

    def test_git_fetch_and_local_processing_do_not_consume_hosted_deadline(self):
        def transport(cmd, **kwargs):
            if cmd[:2] == ['git', 'fetch']:
                self.ticks[0] += 29
                return subprocess.CompletedProcess(cmd, 0, '', '')
            return self.empty(cmd, **kwargs)
        client = self.client(transport)
        self.assertTrue(client.refresh_git(refs=['main'])['fresh'])
        self.ticks[0] += 2
        client.resolve_branches(['a'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1]['timeout'], 30)

    def test_one_hosted_deadline_is_shared_across_acquisition_methods(self):
        def slow(cmd, **kwargs):
            result = self.empty(cmd, **kwargs)
            self.ticks[0] += 20
            return result
        client = self.client(slow)
        client.resolve_branches(['a'])
        client.pr_metadata([1])
        client.refresh_stack(1)
        self.assertEqual([kwargs['timeout'] for _, kwargs in self.calls], [30, 10])
        self.assertTrue(any('deadline' in warning for warning in client.warnings))

    def test_offline_and_warm_cache_do_not_start_hosted_deadline(self):
        self.client(self.empty).resolve_branches(['a'])
        client = self.client(self.empty)
        client.resolve_branches(['a'])
        client.resolve_branches(['missing'], offline=True)
        self.assertIsNone(client.deadline)
        self.ticks[0] += 31
        client.resolve_branches(['new'])
        self.assertEqual(self.calls[-1][1]['timeout'], 30)

    def test_shared_start_spacing_across_repositories(self):
        self.client(self.empty).resolve_branches(['a'])
        self.client(self.empty, repo=dict(self.repo, name='other')).resolve_branches(['b'])
        self.assertEqual(self.sleeps, [.25])
        self.assertEqual(len(self.calls), 2)

    def test_shared_slot_never_sleeps_beyond_hosted_deadline(self):
        self.client(self.empty).resolve_branches(['a'])
        client = self.client(self.empty, repo=dict(self.repo, name='other'), deadline_seconds=.1)
        client.resolve_branches(['b'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.sleeps, [])
        self.assertTrue(any('shared request slot' in warning for warning in client.warnings))

    def test_sleep_overrun_rechecks_deadline_before_request(self):
        self.client(self.empty).resolve_branches(['a'])
        client = self.client(self.empty, repo=dict(self.repo, name='other'))
        client.sleep = lambda _: self.ticks.__setitem__(0, self.ticks[0] + 31)
        client.resolve_branches(['b'])
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(any('deadline' in warning for warning in client.warnings))


if __name__ == '__main__':
    unittest.main()
