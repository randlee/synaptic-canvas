"""Chain provenance and bounded rendering, with all acquisition mocked."""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gh_stack_chain_check as chain


class ChainObservations(unittest.TestCase):
    def run_report(self, branch_observation, *, stale_pr=False):
        sha = 'a' * 40
        refs = {'refs/remotes/origin/main': sha, 'refs/remotes/origin/topic': sha}
        snapshot = {'repository': {}, 'stacks': [], 'refs': refs, 'fingerprint': 'epoch',
                    'warnings': ['No local gh-stack catalog; remote stacks may exist']}
        client = Mock()
        client.refresh_git.return_value = {'fresh': True, 'source': 'cached', 'observed_at': 1, 'error': None}
        pr = {'number': 1, 'headRefName': 'topic', 'headRefOid': sha, 'baseRefName': 'main', 'isDraft': False, 'state': 'OPEN'}
        client.resolve_branches.return_value = {'topic': pr} if stale_pr else {}
        client.pr_metadata.return_value = {1: pr} if stale_pr else {}
        client.observations = {1: {'state': {'freshness': 'stale'}}} if stale_pr else {}
        client.branch_observations = {'topic': branch_observation}
        client.metrics, client.warnings, client.snapshot_id = {}, [], 'hosted'
        row = {'layer': 1, 'branch': 'topic', 'origin': sha, 'pr': 1 if stale_pr else None,
               'pushed': True, 'contains_parent': True, 'pr_base_ok': True if stale_pr else None,
               'pr_head_ok': True if stale_pr else None, 'draft': False}
        report = {'trunk': 'main', 'trunk_origin': sha, 'rows': [row], 'problems': [], 'notes': [],
                  'landing': {'clean': True, 'reason': 'clean'}, 'linkable': True}
        conflicts = {'layers': [{'branch': 'topic', 'clean': True, 'reason': 'clean'}],
                     'combined': {'clean': True}, 'clean': True}
        args = argparse.Namespace(trunk='main', layers=['topic'], no_fetch=True, no_pr=True, json=True)
        output = io.StringIO()
        with patch.object(chain, 'preflight'), patch.object(chain, 'read_local_snapshot', return_value=snapshot), \
             patch.object(chain, 'StackDataClient', return_value=client), \
             patch.object(chain, 'evaluate_stack_conflicts', return_value=conflicts), \
             patch.object(chain, 'evaluate', return_value=report), contextlib.redirect_stdout(output):
            code = chain.run_check(args)
        self.assertTrue(client.resolve_branches.call_args.kwargs['offline'])
        return code, json.loads(output.getvalue())

    def test_confirmed_no_pr_allows_linkable_without_api(self):
        code, report = self.run_report({'freshness': 'fresh', 'exists': False, 'source': 'cached'})
        self.assertEqual(code, 0)
        self.assertTrue(report['linkable'])
        self.assertEqual(report['unknown_count'], 0)

    def test_unknown_or_stale_absence_never_green(self):
        for observation in ({}, {'freshness': 'unknown', 'exists': None}, {'freshness': 'stale', 'exists': False}):
            code, report = self.run_report(observation)
            self.assertEqual(code, 1)
            self.assertIsNone(report['linkable'])
            self.assertEqual(report['unknown_count'], 1)

    def test_stale_pr_columns_are_unknown(self):
        _, report = self.run_report({}, stale_pr=True)
        self.assertIsNone(report['rows'][0]['pr_base_ok'])
        self.assertIsNone(report['rows'][0]['pr_head_ok'])

    def test_summary_prioritizes_conflict_beyond_ten_and_counts_all(self):
        _, report = self.run_report({'freshness': 'fresh', 'exists': False})
        row = report['rows'][0]
        report['rows'] = [dict(copy.deepcopy(row), layer=n, branch='topic/' + str(n), local_merge_clean=n != 12) for n in range(1, 16)]
        text = chain.render(report)
        self.assertIn('| 12/15 |', text)
        self.assertIn('local merge', text)
        self.assertIn('1 conflict(s)', text)
        self.assertIn('truncated', text)
        self.assertEqual(sum(line.startswith('| ') and '/15 |' in line for line in text.splitlines()), 10)


if __name__ == '__main__':
    unittest.main()
