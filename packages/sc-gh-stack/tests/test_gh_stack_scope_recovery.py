"""Scoped catalog/fetch recovery; all transports are fake or local Git only."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gh_stack_local import read_local_snapshot, scope_diagnostics
from gh_stack_remote import StackDataClient


def test_unrelated_invalid_and_conflicting_catalog_scopes(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, text=True, capture_output=True, check=True).stdout.strip()
    git('init', '-b', 'main')
    git('remote', 'add', 'origin', 'git@github.com:org/repo.git')
    monkeypatch.chdir(tmp_path)
    good = {'id': 'good', 'number': 1, 'trunk': {'branch': 'main'}, 'branches': [{'branch': 'healthy', 'pullRequest': {'number': 10}}]}
    malformed = {'id': 'bad', 'trunk': {'branch': 'main'}, 'branches': [{'branch': 'other', 'base': 'bad-sha'}]}
    conflict = {'id': 'conflict', 'trunk': {'branch': 'main'}, 'branches': [{'branch': 'one'}]}
    alternative = dict(conflict, branches=[{'branch': 'two'}])
    (tmp_path / '.git/gh-stack').write_text(json.dumps({'schemaVersion': 1, 'stacks': [good, malformed, conflict, alternative]}))
    snapshot = read_local_snapshot()
    assert len(snapshot['stacks']) == 1
    assert len(scope_diagnostics(snapshot)) == 2
    assert scope_diagnostics(snapshot, stacks=snapshot['stacks']) == []
    assert len(scope_diagnostics(snapshot, branches=['one'])) == 1
    assert len(scope_diagnostics(snapshot, branches=['other'])) == 1


@pytest.mark.parametrize('hint', [dict(branches=['healthy']), dict(id='good'), dict(number=1), dict(pr_numbers=[10])])
def test_affirmative_scope_collision_is_not_hidden(hint):
    stack = dict(id='good', number=1, branches=[dict(name='healthy', pr=dict(number=10))])
    snapshot = dict(warnings=['damage'], scope_issues=[dict(message='damage', **hint)])
    assert scope_diagnostics(snapshot, stacks=[stack]) == ['damage']


def test_unreadable_unknown_scope_stays_visible_but_not_blocking_explicit_scope():
    snapshot = dict(warnings=['unreadable catalog'], scope_issues=[dict(message='unreadable catalog', scope_known=False)])
    assert scope_diagnostics(snapshot) == ['unreadable catalog']
    assert scope_diagnostics(snapshot, branches=['healthy']) == []
    assert snapshot['warnings'] == ['unreadable catalog']


def client(tmp_path, transport, clock=lambda: 1000):
    return StackDataClient(dict(root=str(tmp_path), common_dir=str(tmp_path / '.git'), host='github.test',
                                owner='org', name='repo', auth_identity='test', cooldown_dir=str(tmp_path / 'pressure')),
                           run_fn=transport, clock=clock)


def test_deleted_branch_does_not_poison_survivors_and_negative_cache_coalesces(tmp_path):
    calls = []
    def transport(cmd, **kwargs):
        calls.append(cmd)
        assert cmd[0] == 'git'
        if cmd[1] == 'ls-remote':
            return subprocess.CompletedProcess(cmd, 0, 'a' * 40 + '\trefs/heads/main\n' + 'b' * 40 + '\trefs/heads/healthy\n', '')
        if any('refs/heads/deleted:' in arg for arg in cmd):
            return subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref refs/heads/deleted")
        return subprocess.CompletedProcess(cmd, 0, '', '')
    report = client(tmp_path, transport).refresh_git(refs=['main', 'healthy', 'deleted'])
    assert report['source'] == 'fetched'
    assert report['fresh'] is False
    assert report['refs']['healthy']['fresh'] is True
    assert report['refs']['main']['fresh'] is True
    assert report['refs']['deleted']['fresh'] is False
    assert report['refs']['deleted']['exists'] is False
    assert len(calls) == 3  # failed batch + one advertisement + surviving batch
    again = client(tmp_path, transport).refresh_git(refs=['main', 'healthy', 'deleted'], force=True, offline=True)
    assert again['fresh'] is False
    assert len(calls) == 3
    assert client(tmp_path, transport).refresh_git(refs=['healthy'])['fresh'] is True
    # Ordinary readers do not retry the missing catalog branch immediately.
    client(tmp_path, transport).refresh_git(refs=['main', 'healthy', 'deleted'])
    assert len(calls) == 3


@pytest.mark.parametrize('advertisement', [subprocess.CompletedProcess([], 1, '', 'offline'),
                                          subprocess.CompletedProcess([], 0, 'malformed', '')])
def test_failed_or_malformed_advertisement_never_certifies_missing_scope(tmp_path, advertisement):
    calls = []
    def transport(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == 'ls-remote':
            return advertisement
        return subprocess.CompletedProcess(cmd, 128, '', "fatal: couldn't find remote ref deleted")
    report = client(tmp_path, transport).refresh_git(refs=['healthy', 'deleted'])
    assert report['fresh'] is False
    assert all(not entry['fresh'] for entry in report['refs'].values())
    assert len(calls) == 2


def test_git_refresh_does_not_consume_expired_hosted_deadline(tmp_path):
    calls = []
    def transport(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '', '')
    adapter = client(tmp_path, transport)
    adapter.deadline = -1
    assert adapter.refresh_git(refs=['healthy'])['fresh'] is True
    assert len(calls) == 1


def test_real_local_git_missing_branch_recovery_and_reappearance(tmp_path):
    """Exercise actual Git stderr/advertisement/refspec syntax without a network."""
    server = tmp_path / 'remote.git'
    work = tmp_path / 'work'
    work.mkdir()
    def git(*args, cwd=work):
        return subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True, check=True).stdout.strip()
    git('init', '--bare', str(server))
    git('init', '-b', 'main')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '--allow-empty', '-m', 'base')
    git('branch', 'healthy')
    git('branch', 'deleted')
    git('remote', 'add', 'origin', str(server))
    git('push', '--all', 'origin')
    original_sha = git('rev-parse', 'main')
    git('--git-dir=' + str(server), 'update-ref', '-d', 'refs/heads/deleted')
    now = [1000]
    calls = []
    def transport(cmd, **kwargs):
        calls.append(cmd)
        kwargs.pop('check', None)
        return subprocess.run(cmd, text=True, capture_output=True, check=False, **kwargs)
    report = client(work, transport, clock=lambda: now[0]).refresh_git(refs=['main', 'healthy', 'deleted'])
    assert len(calls) == 3
    assert report['refs']['healthy']['fresh'] is True
    assert report['refs']['deleted']['exists'] is False
    # Recovery does not delete existing local/tracking refs to disguise absence.
    assert git('rev-parse', 'refs/remotes/origin/deleted') == original_sha
    git('--git-dir=' + str(server), 'update-ref', 'refs/heads/deleted', original_sha)
    now[0] += 61
    restored = client(work, transport, clock=lambda: now[0]).refresh_git(refs=['main', 'healthy', 'deleted'])
    assert restored['fresh'] is True
    assert restored['refs']['deleted']['exists'] is True

