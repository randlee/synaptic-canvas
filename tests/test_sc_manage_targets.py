"""Target isolation and real filesystem install/list/uninstall round trips.

All destinations and profiles are temporary. No user installation or network
is used; sc-gh-stack has no pip dependencies.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from sc_cli import install as installer

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'packages/sc-manage/scripts'
sys.path.insert(0, str(SCRIPTS))
import sc_manage_common as common
import sc_manage_install as manage_install
import sc_manage_uninstall as manage_uninstall

TARGETS = ('claude', 'codex', 'cursor', 'hermes')


@pytest.fixture
def sandbox(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    env = dict(os.environ, SC_REPO_PATH=str(ROOT))
    roots = {target: tmp_path / 'profiles' / ('.' + target) for target in TARGETS}
    for target, directory in roots.items():
        env[f'GLOBAL_{target.upper()}_DIR'] = str(directory)
        env[f'USER_{target.upper()}_DIR'] = str(directory)
    env['CODEX_HOME'] = str(roots['codex'])
    env['HERMES_HOME'] = str(roots['hermes'])
    return project, roots, env


def dispatch(sandbox, *args):
    project, _, env = sandbox
    result = subprocess.run([sys.executable, str(SCRIPTS / 'sc_manage_dispatch.py'), *args],
                            cwd=project, env=env, capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('scope', ['local', 'global', 'user'])
def test_real_target_round_trip_and_no_peer_writes(sandbox, target, scope):
    project, roots, _ = sandbox
    code, body = dispatch(sandbox, '--install', 'sc-gh-stack', '--' + scope, '--' + target)
    assert code == 0 and body['success'], body
    dest = project / f'.{target}' if scope == 'local' else roots[target]
    assert body['data']['targets'] == [target]
    assert Path(body['data']['dest']) == dest
    for skill in ('sc-gh-stack', 'sc-gh-stack-view'):
        assert (dest / 'skills' / skill / 'SKILL.md').exists()
    assert len(list((dest / 'scripts').glob('gh_stack_*.py'))) == 5
    if target != 'claude':
        assert not (dest / 'commands').exists() and not (dest / 'agents').exists()
    if target == 'hermes' and scope == 'local':
        assert 'trust' in body['data']['notes'][0]
        assert not (roots['hermes'] / 'config.yaml').exists()
    for peer in set(TARGETS) - {target}:
        assert not (project / f'.{peer}').exists()
        assert not roots[peer].exists()
    code, body = dispatch(sandbox, '--list', '--' + target)
    row = next(item for item in body['data']['packages'] if item['name'] == 'sc-gh-stack')
    assert code == 0
    assert row['installed_by_target'] == {target: 'local' if scope == 'local' else 'global'}
    marker = dest / 'keep-user-file.txt'
    marker.write_text('unrelated')
    code, body = dispatch(sandbox, '--uninstall', 'sc-gh-stack', '--' + scope, '--' + target)
    assert code == 0 and body['success'], body
    assert not (dest / 'skills/sc-gh-stack/SKILL.md').exists()
    assert not (dest / 'scripts/gh_stack_view.py').exists()
    assert marker.read_text() == 'unrelated'


def test_multiple_targets_and_selective_uninstall(sandbox):
    project, _, _ = sandbox
    code, body = dispatch(sandbox, '--install', 'sc-gh-stack', '--project',
                          '--claude', '--codex', '--cursor', '--hermes')
    assert code == 0 and body['data']['targets'] == list(TARGETS)
    assert body['data']['dest'] is None
    assert set(body['data']['destinations']) == set(TARGETS)
    code, body = dispatch(sandbox, '--uninstall', 'sc-gh-stack', '--local', '--codex')
    assert code == 0
    for target in TARGETS:
        assert (project / f'.{target}/skills/sc-gh-stack/SKILL.md').exists() is (target != 'codex')
    code, body = dispatch(sandbox, '--list', '--claude', '--codex', '--cursor', '--hermes')
    row = next(item for item in body['data']['packages'] if item['name'] == 'sc-gh-stack')
    assert code == 0 and row['installed'] == 'mixed'
    assert row['installed_by_target'] == {target: 'no' if target == 'codex' else 'local' for target in TARGETS}


def test_default_remains_claude_only(sandbox):
    project, _, _ = sandbox
    code, body = dispatch(sandbox, '--install', 'sc-gh-stack', '--local')
    assert code == 0 and body['data']['targets'] == ['claude']
    assert (project / '.claude/skills/sc-gh-stack/SKILL.md').exists()
    assert not any((project / f'.{target}').exists() for target in TARGETS[1:])


def test_single_quoted_argument_string(sandbox):
    code, body = dispatch(sandbox, '--install sc-gh-stack --global --hermes')
    assert code == 0 and body['data']['targets'] == ['hermes']


@pytest.mark.parametrize('args', [
    ['--install', 'sc-gh-stack', '--global', '--codez'],
    ['--install', 'sc-gh-stack', '--global', '--co'],
    ['--install', 'sc-gh-stack', '--global', '--local'],
    ['--install', 'sc-gh-stack', '--list', '--global'],
    ['--install', 'sc-gh-stack', '--codex'],
    ['--docs', 'sc-gh-stack', '--codex'],
    ['--list', '--global'],
    ['--install', '../sc-gh-stack', '--local', '--hermes'],
])
def test_invalid_flags_fail_before_install(sandbox, args):
    project, roots, _ = sandbox
    code, body = dispatch(sandbox, *args)
    assert code != 0 and body['success'] is False
    assert body['error']['code'] == 'INPUT_INVALID'
    assert not any(root.exists() for root in roots.values())
    assert not any((project / f'.{target}').exists() for target in TARGETS)


@pytest.mark.parametrize('module', [manage_install, manage_uninstall])
@pytest.mark.parametrize('targets', [[], ['unknown'], ['codex', 1], 'codex', None])
def test_json_target_validation_before_dependencies(module, targets, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps({
        'package': 'sc-gh-stack', 'scope': 'global', 'targets': targets})))
    assert module.main() == 1
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'INPUT_INVALID'


@pytest.mark.parametrize('target', ['codex', 'hermes'])
def test_profile_home_used_and_project_scope_stays_local(target, tmp_path, monkeypatch):
    profile = tmp_path / 'custom-profile'
    monkeypatch.setenv(target.upper() + '_HOME', str(profile))
    monkeypatch.delenv('GLOBAL_' + target.upper() + '_DIR', raising=False)
    monkeypatch.delenv('USER_' + target.upper() + '_DIR', raising=False)
    assert common.target_roots({}, target) == (profile, profile)
    monkeypatch.setattr(common, 'resolve_repo_root', lambda: tmp_path)
    assert common.resolve_dest('global', profile, profile, target)[0] == profile
    assert common.resolve_dest('local', profile, profile, target)[0] == tmp_path / f'.{target}'


@pytest.mark.parametrize('target', TARGETS[1:])
def test_backend_explicit_destination_filters_artifacts_and_cleanup(target, tmp_path):
    dest = tmp_path / 'custom-profile'
    assert installer.main(['install', 'sc-gh-stack', '--dest', str(dest), '--' + target]) == 0
    assert (dest / 'scripts/gh_stack_view.py').exists()
    assert not (dest / 'commands').exists() and not (dest / 'agents').exists()
    keep = dest / 'commands/keep.md'
    keep.parent.mkdir()
    keep.write_text('not owned by this target')
    assert installer.main(['uninstall', 'sc-gh-stack', '--dest', str(dest), '--' + target]) == 0
    assert keep.exists()


def test_backend_multiple_targets_cannot_share_explicit_destination(tmp_path, capsys):
    dest = tmp_path / '.claude'
    assert installer.main(['install', 'sc-gh-stack', '--dest', str(dest), '--claude', '--codex']) == 1
    assert not dest.exists()
    assert 'one target' in capsys.readouterr().err


@pytest.mark.parametrize('target', TARGETS)
def test_installed_manager_works_without_source_env(target, sandbox, monkeypatch):
    project, roots, env = sandbox
    manager = roots[target]
    assert installer.main(['install', 'sc-manage', '--dest', str(manager), '--' + target]) == 0
    record = manager / 'scripts/sc_manage_source.json'
    assert json.loads(record.read_text())['sc_repo_path'] == str(ROOT)
    child_env = dict(env)
    child_env.pop('SC_REPO_PATH', None)
    installed_dispatch = manager / 'scripts/sc_manage_dispatch.py'
    result = subprocess.run([sys.executable, str(installed_dispatch), '--install', 'sc-gh-stack',
                             '--local', '--' + target], cwd=project, env=child_env, capture_output=True, text=True)
    body = json.loads(result.stdout)
    assert result.returncode == 0 and body['success'], result.stderr + result.stdout
    skill = project / f'.{target}/skills/sc-gh-stack'
    assert (skill / '../../scripts/gh_stack_view.py').resolve().is_file()
    assert installer.main(['uninstall', 'sc-manage', '--dest', str(manager), '--' + target]) == 0
    assert not record.exists()
    assert (project / f'.{target}/skills/sc-gh-stack/SKILL.md').exists()


@pytest.mark.parametrize('module,action', [(manage_install, 'run_install'), (manage_uninstall, 'run_uninstall')])
def test_partial_failure_reports_completed_targets_and_stops(module, action, sandbox, monkeypatch, capsys):
    _, roots, _ = sandbox
    payload = {'package': 'sc-gh-stack', 'scope': 'global', 'sc_repo_path': str(ROOT),
               'targets': ['claude', 'codex', 'cursor']}
    for target, root in roots.items():
        payload[f'global_{target}_dir'] = str(root)
    calls = []
    def execute(repo, package, dest, target):
        calls.append(target)
        return (1, '', 'simulated failure') if target == 'codex' else (0, '', '')
    monkeypatch.setattr(module, action, execute)
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(payload)))
    assert module.main() == 1
    body = json.loads(capsys.readouterr().out)
    assert body['success'] is False
    assert body['data'] == {'completed_targets': ['claude'], 'failed_target': 'codex'}
    assert calls == ['claude', 'codex']


@pytest.mark.parametrize('module', [manage_install, manage_uninstall])
def test_same_destination_refused_before_actions(module, tmp_path, monkeypatch, capsys):
    payload = {'package': 'sc-gh-stack', 'scope': 'global', 'sc_repo_path': str(ROOT),
               'targets': ['codex', 'hermes'], 'global_codex_dir': str(tmp_path), 'global_hermes_dir': str(tmp_path)}
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(module, 'run_install' if module is manage_install else 'run_uninstall',
                        lambda *_: pytest.fail('No actions allowed after invalid preflight'))
    assert module.main() == 1
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'DEST_INVALID'


def test_backend_uninstall_permission_failure_is_not_success(tmp_path, monkeypatch):
    dest = tmp_path / 'profile'
    assert installer.main(['install', 'sc-gh-stack', '--dest', str(dest), '--codex']) == 0
    blocked = dest / 'scripts/gh_stack_view.py'
    unlink = Path.unlink
    def fail_owned(path, *args, **kwargs):
        if path == blocked:
            raise PermissionError('simulated permission failure')
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', fail_owned)
    assert installer.main(['uninstall', 'sc-gh-stack', '--dest', str(dest), '--codex']) == 1
    assert blocked.exists()


@pytest.mark.parametrize('target', ['cursor', 'hermes'])
def test_backend_combined_local_flags_are_explicit_only(tmp_path, monkeypatch, target):
    monkeypatch.chdir(tmp_path)
    assert installer.main(['install', 'sc-gh-stack', '--local', '--' + target]) == 0
    assert (tmp_path / f'.{target}/skills/sc-gh-stack/SKILL.md').exists()
    assert not (tmp_path / '.claude').exists()
    assert not (tmp_path / '.codex').exists()


def test_cursor_sc_manage_writes_native_command_and_keeps_installer_scripts(tmp_path):
    dest = tmp_path / '.cursor'
    assert installer.main(['install', 'sc-manage', '--dest', str(dest), '--cursor']) == 0
    skill = dest / 'skills/managing-sc-packages/SKILL.md'
    command = dest / 'commands/sc-manage.md'
    dispatch = dest / 'scripts/sc_manage_dispatch.py'
    assert skill.is_file() and command.is_file() and dispatch.is_file()
    text = command.read_text(encoding='utf-8')
    assert 'name: sc-manage' in text
    assert 'allowed-tools' not in text
    assert '!`' not in text
    assert 'sc_manage_dispatch.py' in text
    assert (command.parent / '../scripts/sc_manage_dispatch.py').resolve() == dispatch.resolve()
    assert not (dest / 'agents').exists()
    keep = dest / 'commands/keep.md'
    keep.write_text('unrelated')
    assert installer.main(['uninstall', 'sc-manage', '--dest', str(dest), '--cursor']) == 0
    assert not command.exists()
    assert not (dest / 'scripts/sc_manage_source.json').exists()
    assert keep.read_text() == 'unrelated'


def test_claude_sc_manage_keeps_bang_command(tmp_path):
    dest = tmp_path / '.claude'
    assert installer.main(['install', 'sc-manage', '--dest', str(dest), '--claude']) == 0
    text = (dest / 'commands/sc-manage.md').read_text(encoding='utf-8')
    assert 'allowed-tools' in text
    assert '!`python3 scripts/sc_manage_dispatch.py' in text
    cursor_template = (ROOT / 'packages/sc-manage/cursor/sc-manage.md').read_text(encoding='utf-8')
    assert text != cursor_template
