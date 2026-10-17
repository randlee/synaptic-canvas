"""Scoped git transport budgets and shared per-ref observations; no network."""
import concurrent.futures
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gh_stack_remote import StackDataClient


class ScopedGitRefresh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repository = {'root': str(self.root), 'common_dir': str(self.root / '.git'),
                           'remote': 'upstream', 'host': 'github.test', 'owner': 'org', 'name': 'repo'}
        self.now = [1000]
        self.commands = []
        self.failure = False

    def transport(self, cmd, **kwargs):
        self.commands.append(cmd)
        self.assertEqual(cmd[:2], ['git', 'fetch'])
        return subprocess.CompletedProcess(cmd, int(self.failure), '', 'unavailable' if self.failure else '')

    def client(self, transport=None):
        return StackDataClient(self.repository, cache_dir=self.root / 'cache', run_fn=transport or self.transport, clock=lambda: self.now[0])

    def test_explicit_scope_exact_refspec_and_warm_subset(self):
        first = self.client().refresh_git(refs=['main', 'layer/1'])
        self.assertTrue(first['fresh'])
        self.assertEqual(self.commands, [['git', 'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--', 'upstream',
                                         '+refs/heads/layer/1:refs/remotes/upstream/layer/1', '+refs/heads/main:refs/remotes/upstream/main']])
        self.assertEqual(self.client().refresh_git(refs=['main'])['source'], 'cached')
        self.client().refresh_git(refs=['main', 'layer/2'])
        self.assertEqual(self.commands[-1][-1], '+refs/heads/layer/2:refs/remotes/upstream/layer/2')
        self.assertEqual(len(self.commands[-1]), 8)

    def test_scope_ttl_and_offline_aggregate(self):
        self.client().refresh_git(refs=['main'])
        self.now[0] += 30
        self.client().refresh_git(refs=['other'])
        self.now[0] += 31
        stale = self.client().refresh_git(refs=['main', 'other'], offline=True)
        self.assertFalse(stale['fresh'])
        self.assertFalse(stale['refs']['main']['fresh'])
        self.assertTrue(stale['refs']['other']['fresh'])
        self.client().refresh_git(refs=['main', 'other'])
        self.assertEqual(self.commands[-1][-1], '+refs/heads/main:refs/remotes/upstream/main')
        self.assertEqual(len(self.commands), 3)

    def test_failed_scope_never_covers_other_scope(self):
        self.client().refresh_git(refs=['main'])
        self.failure = True
        failed = self.client().refresh_git(refs=['missing'])
        self.assertFalse(failed['fresh'])
        self.assertTrue(self.client().refresh_git(refs=['main'], offline=True)['fresh'])
        self.assertFalse(self.client().refresh_git(refs=['missing'], force=True)['fresh'])
        self.assertEqual(len(self.commands), 2)
        self.assertFalse(self.client().refresh_git(refs=['unseen'], offline=True)['fresh'])

    def test_ten_forced_same_scope_coalesce(self):
        def slow(cmd, **kwargs):
            time.sleep(.05)
            return self.transport(cmd, **kwargs)
        def fetch(_):
            return self.client(slow).refresh_git(refs=['main', 'topic'], force=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(fetch, range(10)))
        self.assertTrue(all(result['fresh'] for result in results))
        self.assertEqual(len(self.commands), 1)

    def test_empty_scope_and_validation_no_transport(self):
        self.assertTrue(self.client().refresh_git(refs=[])['fresh'])
        for invalid in ('--upload-pack=bad', 'bad..ref', 'bad ref'):
            with self.assertRaises(ValueError):
                self.client().refresh_git(refs=[invalid])
        self.assertEqual(self.commands, [])

    def test_legacy_configured_fetch_does_not_prove_explicit_coverage(self):
        self.client().refresh_git()
        self.assertEqual(self.commands[0], ['git', 'fetch', '--quiet', '--', 'upstream'])
        self.assertFalse(self.client().refresh_git(refs=['topic'], offline=True)['fresh'])
        self.client().refresh_git(refs=['topic'])
        self.assertEqual(len(self.commands), 2)


if __name__ == '__main__':
    unittest.main()
