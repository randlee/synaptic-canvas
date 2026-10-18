"""Timestamped, deterministic comparison to fc702b1; no live GitHub requests.

Set SC_STACK_EVIDENCE_PATH to retain the generated JSON evidence. Extension
HTTP internals and real quota cost are deliberately unmeasured.
"""
import copy
import hashlib
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE_PATH = HERE / 'fixtures/baseline_fc702b1_gh_stack_view.py'
BASELINE_SHA256 = 'b7cb5dd349d427e86fc50ea714da0df241dae7c37af804e89bbd1796907f7870'


def load_baseline_source():
    """Load pinned historical code without requiring git history or network."""
    source = BASELINE_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != BASELINE_SHA256:
        raise AssertionError('Historical baseline fixture changed; verify its provenance before updating the digest')
    return source.decode('utf-8')


def load_fixture():
    spec = importlib.util.spec_from_file_location('stack_efficiency_fixture', HERE / 'test_gh_stack_efficiency.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output_size(text):
    return {'utf8_bytes': len(text.encode()), 'lexical_tokens': len(re.findall(r'\w+|[^\w\s]', text)),
            'token_method': 'Unicode words and individual punctuation; not model tokenizer tokens'}


class BaselineTraceTests(unittest.TestCase):
    def test_120_layer_baseline_and_shared_reports(self):
        source = load_baseline_source()
        fixture_module = load_fixture()
        baseline = types.ModuleType('stack_baseline_fc702b1')
        baseline.__file__ = str(ROOT / 'packages/sc-gh-stack/scripts/gh_stack_view.py')
        exec(compile(source, baseline.__file__, 'exec'), baseline.__dict__)
        evidence = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'baseline_commit': 'fc702b1',
                    'layers': 120, 'transport': 'mocked GitHub subprocess boundary; local git executes in temporary repository',
                    'worktrees': 'synthetic 1/10/60 worktree inventory sharing one native catalog',
                    'unmeasured': ['HTTP inside gh-stack extension', 'real GitHub request concurrency', 'real quota cost'],
                    'semantics': 'Equivalent coherent 120-layer identity/head/base/CI observations. New reports additionally check every intended local merge pair; clean top alone is not parity evidence.',
                    'traces': []}
        for count in (1, 10, 60):
            fixture = fixture_module.EfficiencyIntegrationTests(methodName='test_filter_applied_before_detail_acquisition')
            fixture.setUp()
            try:
                sha = fixture.sha
                stack = {'trunk': 'main', 'branches': [{'name': 'layer/' + str(n), 'head': sha, 'base': sha,
                         'isMerged': False, 'isQueued': False, 'needsRebase': False,
                         'pr': {'number': n, 'state': 'OPEN'}} for n in range(1, 121)]}
                paths = [str(fixture.root)] + [str(fixture.root / ('synthetic-' + str(n))) for n in range(1, count)]
                calls, active, peak, events = [], [0], [0], []
                began = time.monotonic()
                lock = threading.Lock()
                def old_run(cmd, **kwargs):
                    with lock:
                        active[0] += 1
                        peak[0] = max(peak[0], active[0])
                        calls.append(list(cmd))
                        events.append({'elapsed_seconds': time.monotonic() - began, 'command': cmd[:3], 'active_mock_subprocesses': active[0]})
                    try:
                        time.sleep(.003)
                        if cmd[:3] == ['gh', 'stack', 'view']:
                            body = copy.deepcopy(stack)
                        elif cmd[:3] == ['gh', 'repo', 'view']:
                            body = {'owner': {'login': 'org'}, 'name': 'repo'}
                        elif cmd[:3] == ['gh', 'api', 'graphql']:
                            body = {'data': {'repository': {'pr' + str(n): dict(number=n, state='OPEN', isDraft=False, mergeable='MERGEABLE', mergeStateStatus='CLEAN', headRefOid=sha, baseRefName='main' if n == 1 else 'layer/' + str(n - 1), commits={'nodes': [{'commit': {'statusCheckRollup': {'state': 'SUCCESS'}}}]}) for n in range(1, 121)}}}
                        else:
                            raise AssertionError('unexpected baseline subprocess: ' + repr(cmd))
                        return subprocess.CompletedProcess(cmd, 0, json.dumps(body), '')
                    finally:
                        with lock:
                            active[0] -= 1
                with mock.patch.object(baseline, 'run', side_effect=old_run), mock.patch.object(baseline, 'worktree_paths', return_value=paths), mock.patch.object(baseline, 'origin_sha', return_value=sha), mock.patch.object(baseline, 'is_ancestor', return_value=True):
                    stacks, hidden = baseline.discover_stacks(None, include_all=False)
                    details = baseline.pr_details(list(range(1, 121)))
                    rows, problems, notes = baseline.build_rows(stacks[0], details, fetched=True)
                    old_text = baseline.render_table(stacks[0], rows, problems, notes, {'landable': True, 'top': 'layer/120', 'top_sha': sha, 'reason': 'fixture clean'}, trunk_origin=sha)
                self.assertEqual(len(stacks), 1)
                self.assertEqual(len(rows), 120)
                self.assertEqual(problems, [])
                self.assertEqual(len(calls), count + 2)
                self.assertEqual(sum(c[:3] == ['gh', 'stack', 'view'] for c in calls), count)
                self.assertLessEqual(peak[0], 4)
                old_trace = {'gh_subprocesses': len(calls), 'extension_views': count, 'repository_identity_calls': 1,
                             'direct_graphql_subprocesses': 1, 'graphql_aliases': [120], 'peak_mock_subprocess_concurrency': peak[0],
                             'mock_latency_seconds': .003, 'output': output_size(old_text), 'rows': len(rows),
                             'events': events, 'hidden_extension_http_requests': None, 'real_quota_cost': None}
                original_transport = fixture.transport
                git_exec = []
                actual_subprocess_run = subprocess.run
                new_events, new_active, new_peak = [], [0], [0]
                new_began = time.monotonic()
                def record_subprocess(cmd, *args, **kwargs):
                    git_exec.append(list(cmd))
                    self.assertNotEqual(cmd[0], 'gh', 'GitHub executable must never run')
                    return actual_subprocess_run(cmd, *args, **kwargs)
                def transport(cmd, **kwargs):
                    if cmd[0] == 'gh':
                        new_active[0] += 1
                        new_peak[0] = max(new_peak[0], new_active[0])
                        new_events.append({'elapsed_seconds': time.monotonic() - new_began, 'command': cmd[:3], 'active_mock_subprocesses': new_active[0]})
                        try:
                            return original_transport(cmd, **kwargs)
                        finally:
                            new_active[0] -= 1
                    if cmd[:4] == ['git', 'worktree', 'list', '--porcelain']:
                        fixture.commands.append(cmd)
                        inventory = '\0\0'.join('worktree ' + path + '\0HEAD ' + sha + '\0branch refs/heads/main' for path in paths) + '\0\0'
                        return subprocess.CompletedProcess(cmd, 0, inventory, '')
                    if cmd[:3] == ['git', 'rev-parse', '--git-dir'] and kwargs.get('cwd') in paths[1:]:
                        fixture.commands.append(cmd)
                        return subprocess.CompletedProcess(cmd, 0, str(fixture.root / '.git') + '\n', '')
                    return original_transport(cmd, **kwargs)
                with mock.patch.object(fixture_module.view, 'run', side_effect=transport), mock.patch.object(subprocess, 'run', side_effect=record_subprocess):
                    _, cold_json, _ = fixture.cli(fixture_module.view, ['--no-fetch', '--json'])
                    cold = json.loads(cold_json)
                    cold_calls = len(fixture.gh_calls())
                    _, summary, _ = fixture.cli(fixture_module.view, ['--no-fetch'])
                    _, full, _ = fixture.cli(fixture_module.view, ['--no-fetch', '--full'])
                self.assertEqual(cold_calls, 3)
                self.assertEqual(len(fixture.gh_calls()), cold_calls)
                aliases = [len(re.findall(r'p\d+:pullRequest', ' '.join(c))) for c in fixture.gh_calls()]
                self.assertEqual(aliases, [50, 50, 20])
                self.assertEqual(len(cold['stacks'][0]['rows']), 120)
                self.assertEqual(len(cold['stacks'][0]['local_mergeability']['layers']), 120)
                self.assertEqual([row['pr'] for row in cold['stacks'][0]['rows']], [row['pr'] for row in rows])
                self.assertEqual(len(re.findall(r'^\| \d+/120 ', summary, re.M)), 10)
                self.assertEqual(len(re.findall(r'^\| \d+/120 ', full, re.M)), 120)
                self.assertFalse(any(c[:3] == ['gh', 'stack', 'view'] or c[:3] == ['gh', 'repo', 'view'] for c in fixture.commands))
                new_trace = {'cold_gh_subprocesses': cold_calls, 'warm_additional_gh_subprocesses': len(fixture.gh_calls()) - cold_calls,
                             'graphql_aliases': aliases, 'extension_views': 0, 'repository_identity_calls': 0,
                             'peak_mock_gh_subprocess_concurrency': new_peak[0], 'events': new_events,
                             'actual_local_subprocesses_across_three_reports': len(git_exec),
                             'wrapper_transport_calls_across_three_reports': len(fixture.commands),
                             'cold_json': output_size(cold_json), 'default_text': output_size(summary), 'full_text': output_size(full),
                             'rows': 120, 'default_rows': 10, 'full_rows': 120, 'per_layer_local_conflict_results': 120,
                             'mock_reported_graphql_cost': cold['metrics'].get('graphql_cost'), 'real_quota_cost': None}
                evidence['traces'].append({'worktrees': count, 'baseline': old_trace, 'new': new_trace})
            finally:
                fixture.doCleanups()
        destination = os.environ.get('SC_STACK_EVIDENCE_PATH')
        if destination:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(evidence, indent=2) + '\n')

    def test_pinned_baseline_loads_without_git_history(self):
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('No git history reads permitted')):
            source = load_baseline_source()
        self.assertIn('def discover_stacks(', source)


if __name__ == '__main__':
    unittest.main()
