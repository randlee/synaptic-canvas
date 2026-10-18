"""Local-only fixtures: no GitHub or extension executable is involved."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import gh_stack_local as local


@pytest.fixture
def repo(tmp_path, monkeypatch):
    path = tmp_path / 'repo odd\nname'
    path.mkdir()
    def git(*args):
        return subprocess.run(['git', *args], cwd=path, text=True, capture_output=True, check=True).stdout.strip()
    git('init', '-b', 'main')
    git('config', 'user.email', 'test@example.com')
    git('config', 'user.name', 'Test')
    (path / 'f').write_text('base\n')
    git('add', '.')
    git('commit', '-m', 'base')
    git('remote', 'add', 'origin', 'https://github.com/owner/project.git')
    git('branch', 'one')
    monkeypatch.chdir(path)
    return path, git


def catalog(path, branches=None, **extra):
    data = {'schemaVersion': 1, 'stacks': [{'trunk': {'branch': 'main'}, 'branches': branches or [{'branch': 'one', 'pullRequest': {'number': 12, 'merged': False}}], **extra}]}
    (path / 'gh-stack').write_text(json.dumps(data))


def test_native_catalog_no_checked_out_layer_and_identity(repo):
    path, git = repo
    catalog(path / '.git')
    commands = []
    def run(cmd, **kwargs):
        commands.append(cmd)
        return local.run(cmd, **kwargs)
    snapshot = local.read_local_snapshot(run_fn=run)
    assert snapshot['repository']['identity'] == 'github.com:owner/project'
    assert snapshot['stacks'][0]['worktree'] is None
    branch = snapshot['stacks'][0]['branches'][0]
    assert branch['head'] == git('rev-parse', 'one')
    assert branch['recorded_head'] is None
    assert branch['pr'] == {'number': 12}
    assert all(cmd[0] == 'git' for cmd in commands)
    assert sum('for-each-ref' in cmd for cmd in commands) == 1
    assert snapshot['fingerprint'] == local.read_local_snapshot()['fingerprint']
    git('branch', 'two')
    assert snapshot['fingerprint'] != local.read_local_snapshot()['fingerprint']


def test_worktree_common_legacy_dedupe_and_conflict(repo, tmp_path):
    path, git = repo
    worktree = tmp_path / 'linked\n tree'
    git('worktree', 'add', str(worktree), 'one')
    legacy = Path(git('-C', str(worktree), 'rev-parse', '--git-dir'))
    catalog(path / '.git', number=3)
    catalog(legacy, number=3)
    snapshot = local.read_local_snapshot()
    assert len(snapshot['stacks']) == 1
    assert snapshot['stacks'][0]['worktree'] == str(worktree)
    def linked_runner(cmd, **kwargs):
        return local.run(cmd, **{**kwargs, 'cwd': kwargs.get('cwd') or str(worktree)})
    linked_snapshot = local.read_local_snapshot(run_fn=linked_runner)
    assert linked_snapshot['repository']['root'] == snapshot['repository']['root']
    assert linked_snapshot['repository']['common_dir'] == snapshot['repository']['common_dir']
    assert linked_snapshot['repository']['current_worktree'] == str(worktree)
    assert linked_snapshot['fingerprint'] == snapshot['fingerprint']
    catalog(legacy, branches=[{'branch': 'other'}], number=3)
    snapshot = local.read_local_snapshot()
    assert snapshot['stacks'] == []
    assert any('Conflicting' in w for w in snapshot['warnings'])
    diagnostics = {entry['source_path']: entry for entry in snapshot['catalogs']}
    common_source, legacy_source = str(path / '.git/gh-stack'), str(legacy / 'gh-stack')
    assert set(diagnostics) == {common_source, legacy_source}
    assert diagnostics[common_source]['compositions'] == [{'trunk': 'main', 'number': 3, 'branches': [{'name': 'one', 'pr_number': 12}]}]
    assert diagnostics[legacy_source]['compositions'] == [{'trunk': 'main', 'number': 3, 'branches': [{'name': 'other', 'pr_number': None}]}]
    for source, entry in diagnostics.items():
        import hashlib
        assert entry['digest'] == hashlib.sha256(Path(source).read_bytes()).hexdigest()
        assert entry['branch_owners']['one'] == [str(worktree)]
        assert entry['branch_owners']['main'] == [str(path)]
        assert entry['errors'] == []


@pytest.mark.parametrize('data', [[], {'schemaVersion': 2, 'stacks': []}, {'schemaVersion': True, 'stacks': []}, {'schemaVersion': 1, 'stacks': [{'trunk': {'branch': '--evil'}, 'branches': []}]}, {'schemaVersion': 1, 'stacks': [{'trunk': {'branch': 'main'}, 'branches': [{'branch': 'one', 'pullRequest': {'number': True}}]}]}])
def test_malformed_catalog_unknown_identity(repo, data):
    path, git = repo
    (path / '.git/gh-stack').write_text(json.dumps(data))
    git('remote', 'set-url', 'origin', '/tmp/local-repository.git')
    snapshot = local.read_local_snapshot()
    assert snapshot['stacks'] == []
    assert snapshot['repository']['identity'] is None
    assert any('Invalid' in w for w in snapshot['warnings'])
    assert snapshot['catalogs'][0]['errors']


def test_missing_catalog_and_invalid_remote(repo):
    snapshot = local.read_local_snapshot()
    assert any('remote-only' in w for w in snapshot['warnings'])
    with pytest.raises(local.ToolError):
        local.read_local_snapshot(remote='--upload-pack=bad')


def test_duplicate_pr_numbers_within_stack_are_rejected(repo):
    path, _ = repo
    catalog(path / '.git', branches=[{'branch': 'one', 'pullRequest': {'number': 12}}, {'branch': 'other', 'pullRequest': {'number': 12}}])
    snapshot = local.read_local_snapshot()
    assert snapshot['stacks'] == []
    assert any('repeated pullRequest number' in w for w in snapshot['warnings'])


def test_duplicate_pr_membership_across_stacks_blocks_only_conflicts(repo):
    path, _ = repo
    def stack(name, number):
        return {'trunk': {'branch': 'main'}, 'branches': [{'branch': name, 'pullRequest': {'number': number}}]}
    data = {'schemaVersion': 1, 'stacks': [stack('one', 12), stack('other', 12), stack('unrelated', 13)]}
    (path / '.git/gh-stack').write_text(json.dumps(data))
    snapshot = local.read_local_snapshot()
    assert [s['branches'][0]['name'] for s in snapshot['stacks']] == ['unrelated']
    assert any('Conflicting' in w for w in snapshot['warnings'])


@pytest.mark.parametrize('stack_id,accepted', [('ST_global', True), ('123', True), (123, False), ('', False), (True, False)])
def test_native_stack_id_remains_string(repo, stack_id, accepted):
    path, _ = repo
    catalog(path / '.git', id=stack_id, number=7)
    snapshot = local.read_local_snapshot()
    assert bool(snapshot['stacks']) is accepted
    if accepted:
        assert snapshot['stacks'][0]['id'] == stack_id
        assert snapshot['stacks'][0]['number'] == 7


@pytest.mark.parametrize('url,expected', [
    ('https://github.example/owner/project.git', ('github.example', 'owner', 'project')),
    ('ssh://git@github.com/owner/project.git', ('github.com', 'owner', 'project')),
    ('https://[broken', None), ('/tmp/local.git', None),
])
def test_identity_parser(url, expected):
    assert local._identity(url) == expected


def test_real_intermediate_conflict_clean_top_and_no_mutation(repo):
    path, git = repo
    git('checkout', 'one')
    (path / 'f').write_text('layer\n')
    git('commit', '-am', 'layer')
    git('checkout', '-b', 'two')
    (path / 'f').write_text('trunk\n')
    git('commit', '-am', 'resolution')
    git('checkout', 'main')
    (path / 'f').write_text('trunk\n')
    git('commit', '-am', 'trunk')
    catalog(path / '.git', branches=[{'branch': 'one'}, {'branch': 'two'}])
    snapshot = local.read_local_snapshot()
    before = (git('show-ref'), git('status', '--porcelain'), (path / '.git/index').read_bytes(), (path / 'f').read_bytes())
    result = local.evaluate_stack_conflicts(snapshot['stacks'][0], snapshot['refs'])
    assert result['layers'][0]['clean'] is False
    assert result['combined']['clean'] is True
    assert result['clean'] is False
    assert before == (git('show-ref'), git('status', '--porcelain'), (path / '.git/index').read_bytes(), (path / 'f').read_bytes())


def test_unknown_missing_error_and_merged_parent():
    refs = {'refs/heads/main': 'a' * 40, 'refs/heads/one': 'b' * 40, 'refs/heads/two': 'c' * 40}
    stack = {'trunk': 'main', 'branches': [{'name': 'one', 'isMerged': True}, {'name': 'two'}, {'name': 'missing'}]}
    calls = []
    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 128, '', 'missing history')
    result = local.evaluate_stack_conflicts(stack, refs, run_fn=runner)
    assert result['layers'][0]['base'] == 'a' * 40
    assert result['clean'] is None
    assert sum('merge-tree' in cmd for cmd in calls) == 1
    assert 'history' in result['layers'][0]['reason']


def test_scale_all_layers_and_immutable_probe_memo():
    refs = {'refs/heads/main': 'a' * 40}
    branches = []
    for i in range(120):
        name = f'layer/{i}'
        refs['refs/heads/' + name] = f'{i + 1:040x}'
        branches.append({'name': name})
    calls = []
    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, 'tree', '')
    result = local.evaluate_stack_conflicts({'trunk': 'main', 'branches': branches}, refs, run_fn=runner)
    assert len(result['layers']) == 120
    assert result['clean'] is True
    assert sum('merge-tree' in cmd for cmd in calls) == 121


def test_reusable_conflict_memo_and_attribute_invalidation(repo):
    path, git = repo
    catalog(path / '.git')
    snapshot = local.read_local_snapshot()
    calls = []
    def runner(cmd, **kwargs):
        calls.append(cmd)
        return local.run(cmd, **kwargs)
    args = snapshot['stacks'][0], snapshot['refs']
    local.evaluate_stack_conflicts(*args, run_fn=runner)
    assert sum('merge-tree' in cmd for cmd in calls) == 1
    local.evaluate_stack_conflicts(*args, run_fn=runner)
    assert sum('merge-tree' in cmd for cmd in calls) == 1
    (path / '.gitattributes').write_text('f merge=union\n')
    local.evaluate_stack_conflicts(*args, run_fn=runner)
    assert sum('merge-tree' in cmd for cmd in calls) == 2
    git('config', 'merge.custom.driver', 'true')
    local.evaluate_stack_conflicts(*args, run_fn=runner)
    local.evaluate_stack_conflicts(*args, run_fn=runner)
    assert sum('merge-tree' in cmd for cmd in calls) == 4


@pytest.mark.parametrize('url,canonical,destination,port', [
    ('git@work:owner/project.git', 'github.com', 'git@work', None),
    ('git@work.example:owner/project.git', 'github.enterprise', 'git@work.example', None),
    ('ssh://build@work:443/owner/project.git', 'ssh.github.com', 'build@work', 443),
    ('git@ghe:owner/project.git', 'ghe', 'git@ghe', None),
])
def test_ssh_identity_uses_bounded_local_configuration(url, canonical, destination, port):
    calls = []
    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, 'hostname ' + canonical + '\n', '')
    expected_host = 'github.com' if canonical == 'ssh.github.com' else canonical
    assert local._remote_identity(url, runner) == (expected_host, 'owner', 'project')
    assert calls == [(['ssh', '-G'] + (['-p', str(port)] if port else []) + ['--', destination],
                      {'check': False, 'timeout': 5})]


def test_https_undotted_enterprise_never_invokes_ssh():
    def forbidden(*args, **kwargs):
        raise AssertionError('HTTPS identity requires no subprocess')
    assert local._remote_identity('https://ghe/owner/project.git', forbidden) == ('ghe', 'owner', 'project')
    assert local._remote_identity('https://ghe/prefix/owner/project.git', forbidden) is None


@pytest.mark.parametrize('stdout,returncode', [('', 1), ('hostname a\nhostname b\n', 0), ('hostname bad/name\n', 0)])
def test_ssh_identity_failure_never_falls_back_to_transport_alias(stdout, returncode):
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, returncode, stdout, '')
    assert local._remote_identity('git@work.example:owner/project.git', runner) is None


def test_missing_host_identity_is_not_catalog_failure(repo):
    path, git = repo
    catalog(path / '.git', number=7)
    git('remote', 'set-url', 'origin', '/tmp/local-repository.git')
    snapshot = local.read_local_snapshot()
    assert snapshot['repository']['identity'] is None
    assert snapshot['stacks'][0]['number'] == 7
    assert any('identity unknown' in warning for warning in snapshot['warnings'])
    assert local.scope_diagnostics(snapshot) == []
    assert local.scope_diagnostics(snapshot, stacks=snapshot['stacks']) == []


@pytest.mark.parametrize('conflict', [False, True])
def test_missing_worktree_catalog_recovered_from_validated_administration(repo, tmp_path, conflict):
    path, git = repo
    worktree = tmp_path / 'missing linked worktree'
    git('worktree', 'add', str(worktree), 'one')
    admin = Path(git('-C', str(worktree), 'rev-parse', '--git-dir'))
    catalog(path / '.git', number=7)
    catalog(admin, number=7, branches=[{'branch': 'other' if conflict else 'one',
                                      'pullRequest': {'number': 12, 'merged': False}}])
    # Simulate an unavailable checkout without deleting any Git metadata.
    worktree.rename(tmp_path / 'parked linked worktree')
    snapshot = local.read_local_snapshot()
    assert str(admin / 'gh-stack') in {entry['source_path'] for entry in snapshot['catalogs']}
    assert any('unavailable' in warning for warning in snapshot['warnings'])
    if conflict:
        assert snapshot['stacks'] == []
        assert any('Conflicting' in warning for warning in local.scope_diagnostics(snapshot))
    else:
        assert snapshot['stacks'][0]['number'] == 7
        assert local.scope_diagnostics(snapshot, stacks=snapshot['stacks']) == []
