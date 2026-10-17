"""CLI integration and actual transport budgets; all GitHub traffic is simulated."""
import concurrent.futures
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gh_stack_view as view
import gh_stack_chain_check as chain
from gh_stack_remote import StackDataClient
from gh_stack_shared import run as real_run


class EfficiencyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.old_cwd)
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.test')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'file').write_text('base\n')
        self.git('add', 'file')
        self.git('commit', '-m', 'base')
        self.git('remote', 'add', 'origin', 'https://github.test/org/repo.git')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        refs = ['update refs/remotes/origin/main ' + self.sha]
        branches = []
        for n in range(1, 121):
            name = 'layer/' + str(n)
            refs.extend(['update refs/heads/' + name + ' ' + self.sha, 'update refs/remotes/origin/' + name + ' ' + self.sha])
            branches.append({'branch': name, 'base': self.sha, 'pullRequest': {'number': n, 'merged': False}})
        subprocess.run(['git', 'update-ref', '--stdin'], input='\n'.join(refs) + '\n', text=True, capture_output=True, check=True)
        self.catalog = self.root / '.git/gh-stack'
        self.catalog.write_text(json.dumps({'schemaVersion': 1, 'stacks': [{'number': 7, 'trunk': {'branch': 'main'}, 'branches': branches}]}))
        self.commands = []
        self.fetch_error = False
        self.env = mock.patch.dict(os.environ, {'GH_CONFIG_DIR': str(self.root / 'gh-config'), 'GH_TOKEN': 'fixture-only', 'GITHUB_TOKEN': '', 'HOME': str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        def factory(repository, **kwargs):
            repository = dict(repository, cooldown_dir=str(self.root / 'pressure'), auth_identity='fixture')
            return StackDataClient(repository, cache_dir=self.root / 'cache', **kwargs)
        for module in (view, chain):
            patcher = mock.patch.object(module, 'run', side_effect=self.transport)
            patcher.start()
            self.addCleanup(patcher.stop)
            if hasattr(module, 'StackDataClient'):
                patcher = mock.patch.object(module, 'StackDataClient', side_effect=factory)
                patcher.start()
                self.addCleanup(patcher.stop)

    def git(self, *args):
        return real_run(['git', *args]).stdout

    def transport(self, cmd, **kwargs):
        self.commands.append(cmd)
        if cmd[:2] == ['git', 'fetch']:
            return subprocess.CompletedProcess(cmd, 1 if self.fetch_error else 0, '', 'simulated network failure' if self.fetch_error else '')
        if cmd[0] != 'gh':
            return real_run(cmd, **kwargs)
        self.assertEqual(cmd[:2], ['gh', 'api'])
        self.assertIn('graphql', cmd, 'unexpected remote discovery or REST fanout')
        numbers = re.findall(r'p(\d+):pullRequest', ' '.join(cmd))
        self.assertLessEqual(len(numbers), 50)
        nodes = {}
        for number in numbers:
            n = int(number)
            nodes['p' + number] = dict(number=n, state='OPEN', isDraft=False, baseRefName='main' if n == 1 else 'layer/' + str(n - 1), headRefName='layer/' + number, baseRefOid=self.sha, headRefOid=self.sha, mergeable='MERGEABLE', mergeStateStatus='CLEAN', commits={'nodes': [{'commit': {'statusCheckRollup': {'state': 'SUCCESS'}}}]})
        body = {'data': {'repository': nodes, 'rateLimit': {'cost': 1}}}
        return subprocess.CompletedProcess(cmd, 0, 'HTTP/2 200\n\n' + json.dumps(body), '')

    def cli(self, module, args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['fixture', *args]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main()
        return code, out.getvalue(), err.getvalue()

    def gh_calls(self):
        return [cmd for cmd in self.commands if cmd[0] == 'gh']

    def test_view_120_complete_offline_and_bounded_text_no_mutations(self):
        before = (self.catalog.read_bytes(), self.git('show-ref'), (self.root / '.git/index').read_bytes())
        _, text, _ = self.cli(view, ['--no-fetch', '--no-pr', '--json'])
        stack = json.loads(text)['stacks'][0]
        self.assertEqual(len(stack['rows']), 120)
        self.assertEqual(len(stack['local_mergeability']['layers']), 120)
        self.assertTrue(all(row['local_merge_clean'] is True for row in stack['rows']))
        _, summary, _ = self.cli(view, ['--no-fetch', '--no-pr'])
        self.assertEqual(len(re.findall(r'^\| \d+/120 ', summary, re.M)), 10)
        self.assertIn('truncated', summary)
        _, full, _ = self.cli(view, ['--no-fetch', '--no-pr', '--full'])
        self.assertEqual(len(re.findall(r'^\| \d+/120 ', full, re.M)), 120)
        self.assertEqual(self.gh_calls(), [])
        self.assertFalse(any(cmd[:2] == ['git', 'fetch'] for cmd in self.commands))
        self.assertEqual(before, (self.catalog.read_bytes(), self.git('show-ref'), (self.root / '.git/index').read_bytes()))

    def test_wrappers_reuse_three_bulk_requests_and_one_fetch(self):
        self.cli(view, ['--json'])
        self.assertEqual(len(self.gh_calls()), 3)
        _, text, _ = self.cli(chain, ['--trunk', 'main', *map(str, range(1, 121)), '--json'])
        self.assertTrue(text.strip(), 'chain must produce complete structured output')
        self.assertEqual(len(self.gh_calls()), 3)
        self.assertEqual(sum(cmd[:2] == ['git', 'fetch'] for cmd in self.commands), 1)

    def test_no_fetch_reuses_fresh_shared_ref_observations(self):
        self.cli(view, ['--json'])
        _, text, _ = self.cli(view, ['--no-fetch', '--json'])
        report = json.loads(text)
        self.assertTrue(report['git_observation']['fresh'])
        self.assertEqual(report['git_observation']['source'], 'cached')
        self.assertTrue(report['stacks'][0]['coherent'])
        self.assertEqual(len(self.gh_calls()), 3)
        self.assertEqual(sum(cmd[:2] == ['git', 'fetch'] for cmd in self.commands), 1)

    def test_local_conflicts_precede_hosted_detail_selection(self):
        for module, arguments in ((view, ['--no-fetch', '--refresh-status', '--json']),
                                  (chain, ['--trunk', 'main', *map(str, range(1, 121)), '--no-fetch', '--refresh-status', '--json'])):
            events = []
            original = module.evaluate_stack_conflicts
            def local(*args, **kwargs):
                events.append('local')
                return original(*args, **kwargs)
            def acquire(cmd, **kwargs):
                if cmd[0] == 'gh':
                    events.append('hosted')
                return self.transport(cmd, **kwargs)
            with mock.patch.object(module, 'evaluate_stack_conflicts', side_effect=local), mock.patch.object(module, 'run', side_effect=acquire):
                self.cli(module, arguments)
            self.assertIn('hosted', events)
            self.assertLess(events.index('local'), events.index('hosted'))

    def test_chain_numeric_no_pr_catalog_never_calls_gh(self):
        self.cli(chain, ['--trunk', 'main', '1', '2', '--no-fetch', '--no-pr', '--json'])
        self.assertEqual(self.gh_calls(), [])

    def test_chain_numeric_no_pr_catalog_and_cache_miss_never_calls_gh(self):
        self.catalog.unlink()
        self.cli(chain, ['--trunk', 'main', '99999', '--no-fetch', '--no-pr', '--json'])
        self.assertEqual(self.gh_calls(), [])

    def test_filter_applied_before_detail_acquisition(self):
        self.cli(view, ['--trunk', 'absent', '--no-fetch', '--json'])
        self.assertEqual(self.gh_calls(), [])

    def test_failed_fetch_is_never_fresh(self):
        self.cli(view, ['--no-pr', '--json'])
        self.fetch_error = True
        _, text, _ = self.cli(view, ['--no-pr', '--refresh-git', '--json'])
        observation = json.loads(text)['git_observation']
        self.assertFalse(observation['fresh'])
        self.assertNotEqual(observation['source'], 'fetched')
        self.assertIn('failure', observation['error'])

    def test_many_real_worktrees_do_not_discover_via_api(self):
        for n in range(1, 11):
            self.git('worktree', 'add', str(self.root / ('linked ' + str(n))), 'layer/' + str(n))
        _, text, _ = self.cli(view, ['--no-fetch', '--no-pr', '--json'])
        report = json.loads(text)
        self.assertEqual(len(report['stacks']), 1)
        self.assertEqual(len(report['stacks'][0]['rows']), 120)
        self.assertEqual(self.gh_calls(), [])
        self.assertFalse(any(cmd[:3] == ['gh', 'stack', 'view'] for cmd in self.commands))

    def test_conflicted_catalog_recovery_is_identifiable_without_api(self):
        self.git('worktree', 'add', str(self.root / 'stale linked'), 'layer/1')
        gitdir = self.git('-C', str(self.root / 'stale linked'), 'rev-parse', '--git-dir').strip()
        stale = Path(gitdir) / 'gh-stack'
        stale.write_text(json.dumps({'schemaVersion': 1, 'stacks': [{'number': 7, 'trunk': {'branch': 'main'},
                                    'branches': [{'branch': 'layer/1', 'pullRequest': {'number': 1}}]}]}))
        code, text, _ = self.cli(view, ['--all', '--no-fetch', '--no-pr', '--json'])
        self.assertEqual(code, 2)
        report = json.loads(text)
        self.assertFalse(report['success'])
        catalogs = report['error']['details']['catalogs']
        self.assertEqual({Path(item['source_path']).resolve() for item in catalogs}, {self.catalog.resolve(), stale.resolve()})
        self.assertEqual(sorted(len(item['compositions'][0]['branches']) for item in catalogs), [1, 120])
        self.assertTrue(all([Path(path).resolve() for path in item['branch_owners']['layer/1']] == [(self.root / 'stale linked').resolve()] for item in catalogs))
        self.assertEqual(self.gh_calls(), [])

    def test_ten_concurrent_clients_coalesce_one_git_fetch(self):
        repository = view.read_local_snapshot(run_fn=self.transport)['repository']
        repository.update(cooldown_dir=str(self.root / 'pressure'), auth_identity='fixture')
        def slow(cmd, **kwargs):
            if cmd[:2] == ['git', 'fetch']:
                time.sleep(.03)
            return self.transport(cmd, **kwargs)
        def refresh(_):
            return StackDataClient(repository, cache_dir=self.root / 'cache', run_fn=slow).refresh_git()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(refresh, range(10)))
        self.assertTrue(all(result['fresh'] for result in results))
        self.assertEqual(sum(cmd[:2] == ['git', 'fetch'] for cmd in self.commands), 1)
        self.assertEqual(self.gh_calls(), [])

    def test_snapshot_changed_invalidates_verdict(self):
        real_snapshot = view.read_local_snapshot
        reads = [0]
        def changing(*args, **kwargs):
            snapshot = real_snapshot(*args, **kwargs)
            reads[0] += 1
            if reads[0] > 1:
                snapshot['fingerprint'] += '-changed'
            return snapshot
        with mock.patch.object(view, 'read_local_snapshot', side_effect=changing):
            _, text, _ = self.cli(view, ['--no-fetch', '--no-pr', '--json'])
        report = json.loads(text)['stacks'][0]
        self.assertIsNone(report['coherent'])
        self.assertIsNone(report['local_mergeability']['clean'])
        self.assertIsNone(report['landing']['landable'])

    def test_intermediate_conflict_and_unknown_survive_clean_tip(self):
        actual = view.evaluate_stack_conflicts
        def intermediate(*args, **kwargs):
            value = actual(*args, **kwargs)
            value['layers'][0].update(clean=False, reason='fixture intermediate conflict')
            value['layers'][1].update(clean=None, reason='fixture missing history')
            value['clean'] = False
            self.assertTrue(value['combined']['clean'])
            return value
        with mock.patch.object(view, 'evaluate_stack_conflicts', side_effect=intermediate):
            _, text, _ = self.cli(view, ['--no-fetch', '--no-pr', '--json'])
        report = json.loads(text)['stacks'][0]
        self.assertFalse(report['local_mergeability']['clean'])
        self.assertFalse(report['rows'][0]['local_merge_clean'])
        self.assertIsNone(report['rows'][1]['local_merge_clean'])
        self.assertTrue(any('content conflict' in p for p in report['problems']))


if __name__ == '__main__':
    unittest.main()
