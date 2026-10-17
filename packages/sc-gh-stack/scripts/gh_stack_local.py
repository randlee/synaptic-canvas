#!/usr/bin/env python3
"""Read native gh-stack catalogs and predict content conflicts without networking.

Catalogs are historical observations; refs and conflict probes are a separate epoch.
Nothing here migrates catalogs or changes refs, the index, or working files.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

from gh_stack_shared import ToolError, run

_CONFLICT_CACHE = OrderedDict()
_CONFLICT_CACHE_LIMIT = 2048


def _merge_epoch(run_fn):
    """Conservative process-local cache epoch; external drivers cannot be cached."""
    try:
        def output(*args):
            proc = run_fn(['git', *args], check=False)
            if proc.returncode:
                raise ValueError('cannot establish merge semantics')
            return proc.stdout
        common = os.path.realpath(output('rev-parse', '--git-common-dir').removesuffix('\n'))
        if not os.path.isdir(common):
            return None
        config = output('config', '--null', '--list', '--show-origin')
        if re.search(r'merge\.[^\x00\n]+\.driver\n', config):
            return None
        files = output('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', '.gitattributes', '**/.gitattributes').split('\0')
        # Ignored attribute files can still affect tracked files. Include every
        # ancestor directory rather than relying on the attribute file being tracked.
        for tracked in output('ls-files', '-z', '--cached').split('\0'):
            if tracked:
                files.extend(str(parent / '.gitattributes') for parent in Path(tracked).parents)
        files.append('.gitattributes')
        files += [os.path.join(common, 'info', 'attributes'), output('rev-parse', '--git-path', 'index').removesuffix('\n')]
        # Include explicit and standard global attribute sources as well.
        configured = run_fn(['git', 'config', '--path', '--get', 'core.attributesFile'], check=False)
        if configured.returncode == 0:
            files.append(configured.stdout.removesuffix('\n'))
        files += [os.path.expanduser('~/.gitattributes'), os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'git', 'attributes')]
        exec_path = Path(output('--exec-path').removesuffix('\n'))
        files += ['/etc/gitattributes', str(exec_path.parent.parent / 'etc/gitattributes')]
        hashes = []
        for filename in sorted(set(files)):
            if filename:
                try:
                    hashes.append((filename, hashlib.sha256(Path(filename).read_bytes()).hexdigest()))
                except FileNotFoundError:
                    hashes.append((filename, None))
        git_env = sorted((k, v) for k, v in os.environ.items() if k.startswith('GIT_'))
        return common, hashlib.sha256(repr((output('--version'), config, hashes, git_env)).encode()).hexdigest()
    except (ToolError, OSError, ValueError):
        return None


def _branch(value):
    # Strict ref component validation, without one subprocess per layer.
    return (isinstance(value, str) and bool(value) and not value.startswith(('-', '/'))
            and not value.endswith(('/', '.')) and '..' not in value and '@{' not in value
            and value != '@' and not re.search(r'[\x00-\x20\x7f~^:?*\[\\]', value)
            and all(p and not p.startswith('.') and not p.endswith('.lock') for p in value.split('/')))


def _identity(url):
    if '://' in url:
        try:
            parsed = urlsplit(url)
            host, path = parsed.hostname, parsed.path.strip('/')
        except ValueError:
            return None
    else:
        match = re.fullmatch(r'(?:[^/@:]+@)?([^/:]+):(.+)', url)
        if not match:
            return None
        host, path = match.groups()
    path = path.removesuffix('.git')
    parts = path.split('/')
    if not host or '.' not in host or len(parts) != 2 or not all(parts):
        return None
    return host.lower(), parts[0], parts[1]


def _normalize(item, refs):
    if not isinstance(item, dict) or not isinstance(item.get('trunk'), dict):
        raise ValueError('stack needs trunk.branch and branches array')
    trunk = item['trunk'].get('branch')
    branches = item.get('branches')
    if not _branch(trunk) or not isinstance(branches, list) or not branches:
        raise ValueError('stack needs valid trunk.branch and nonempty branches array')
    result = {'trunk': trunk, 'branches': [], 'worktree': None}
    for key in ('id', 'number'):
        if key in item:
            value = item[key]
            if (key == 'id' and (not isinstance(value, str) or not value)) or (key == 'number' and (type(value) is not int or value <= 0)):
                raise ValueError('invalid stack ' + key)
            result[key] = value
    seen = {trunk}
    seen_prs = set()
    for layer in branches:
        if not isinstance(layer, dict) or not _branch(layer.get('branch')) or layer['branch'] in seen:
            raise ValueError('invalid or repeated branch')
        name = layer['branch']
        seen.add(name)
        for field in ('base', 'head'):
            if field in layer and (not isinstance(layer[field], str) or (layer[field] and not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', layer[field]))):
                raise ValueError('invalid recorded ' + field)
        pr = layer.get('pullRequest')
        if pr is not None and (not isinstance(pr, dict) or type(pr.get('number')) is not int or pr['number'] <= 0 or ('merged' in pr and type(pr['merged']) is not bool)):
            raise ValueError('invalid pullRequest number/merged')
        if pr:
            if pr['number'] in seen_prs:
                raise ValueError('repeated pullRequest number in stack')
            seen_prs.add(pr['number'])
        merged = pr.get('merged', False) if pr else False
        result['branches'].append({'name': name, 'head': refs.get('refs/heads/' + name),
                                   'recorded_head': layer.get('head'), 'base': layer.get('base'),
                                   'pr': {'number': pr['number'], **({'state': 'MERGED'} if merged else {})} if pr else None,
                                   'isMerged': merged, 'isQueued': None})
    return result


def _scope_hint(item):
    """Retain only validated identity hints; malformed scope stays unknown."""
    branches = item.get('branches') if isinstance(item, dict) else None
    names = [branch.get('branch') for branch in branches if isinstance(branch, dict)] if isinstance(branches, list) else []
    return {'branches': [name for name in names if _branch(name)],
            'pr_numbers': [branch['pullRequest']['number'] for branch in (branches if isinstance(branches, list) else [])
                           if isinstance(branch, dict) and isinstance(branch.get('pullRequest'), dict)
                           and type(branch['pullRequest'].get('number')) is int],
            'id': item.get('id') if isinstance(item, dict) and isinstance(item.get('id'), str) else None,
            'number': item.get('number') if isinstance(item, dict) and type(item.get('number')) is int else None,
            'scope_known': isinstance(branches, list) and bool(branches) and len(names) == len(branches) and all(_branch(name) for name in names)}


def scope_diagnostics(snapshot, *, stacks=None, branches=None):
    """Return blocking diagnostics for an explicit scope, not unrelated stacks.

    All warnings remain in the snapshot for visibility. Without a scope, discovery
    is still conservative. An explicit scope is not invalidated by an unreadable
    unrelated catalog, but affirmative branch/stack identity collisions block it.
    """
    if stacks is None and branches is None:
        return list(snapshot.get('warnings', []))
    stacks = stacks or []
    names = set(branches or []) | {branch['name'] for stack in stacks for branch in stack['branches']}
    ids = {stack['id'] for stack in stacks if stack.get('id') is not None}
    numbers = {stack['number'] for stack in stacks if stack.get('number') is not None}
    prs = {(branch.get('pr') or {}).get('number') for stack in stacks for branch in stack['branches']} - {None}
    by_message = {}
    for issue in snapshot.get('scope_issues', []):
        by_message.setdefault(issue['message'], []).append(issue)
    def relevant(issue):
        return (bool(names & set(issue.get('branches', [])))
                or bool(prs & set(issue.get('pr_numbers', [])))
                or issue.get('id') in ids or issue.get('number') in numbers)
    return [warning for warning in snapshot.get('warnings', [])
            if warning not in by_message or any(relevant(issue) for issue in by_message[warning])]


def read_local_snapshot(remote='origin', run_fn=run):
    """Resolve catalogs once per git directory, returning useful local unknowns."""
    if not _branch(remote):
        raise ToolError('invalid remote name')
    def git(*args, cwd=None, check=True):
        return run_fn(['git', *args], cwd=cwd, check=check)
    top = git('rev-parse', '--show-toplevel', check=False)
    current_worktree = top.stdout.removesuffix('\n') if top.returncode == 0 else None
    def gitdir(flag, cwd=None):
        value = git('rev-parse', flag, cwd=cwd).stdout.removesuffix('\n')
        return os.path.realpath(os.path.join(cwd or os.getcwd(), value))
    common, current = gitdir('--git-common-dir'), gitdir('--git-dir')
    warnings, scope_issues = [], []
    refs = {}
    for line in git('for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads/', 'refs/remotes/').stdout.splitlines():
        ref, sha = line.split(' ', 1)
        refs[ref] = sha
    records, record = [], {}
    for token in git('worktree', 'list', '--porcelain', '-z').stdout.split('\0'):
        if not token:
            if record:
                records.append(record)
                record = {}
        else:
            key, _, value = token.partition(' ')
            record[key] = value
    if record:
        records.append(record)
    # Git lists the primary worktree (or bare repository) first. Do not infer
    # its location by stripping a .git suffix: separate git directories exist.
    root = records[0].get('worktree') if records else common
    directories = {common, current}
    owners = {}
    branch_owners = {}
    for record in records:
        path = record.get('worktree')
        if not path:
            continue
        if record.get('branch'):
            name = record['branch'].removeprefix('refs/heads/')
            owners[name] = path
            branch_owners.setdefault(name, []).append(path)
        try:
            directories.add(gitdir('--git-dir', cwd=path))
        except ToolError as exc:
            warnings.append(f'Cannot inspect worktree {path!r}: {exc}')
    url = git('remote', 'get-url', remote, check=False)
    identity = _identity(url.stdout.strip()) if url.returncode == 0 else None
    if not identity:
        warnings.append(f'Remote {remote!r} identity unknown; configure an unambiguous host/owner/repository URL for hosted reads')
    repository = {'root': root, 'current_worktree': current_worktree, 'common_dir': common, 'git_dir': current, 'remote': remote,
                  'host': identity[0] if identity else None, 'owner': identity[1] if identity else None,
                  'name': identity[2] if identity else None,
                  'identity': f'{identity[0]}:{identity[1]}/{identity[2]}' if identity else None}
    candidates, epoch, catalogs = [], [], []
    for directory in sorted(directories):
        path = Path(directory) / 'gh-stack'
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            epoch.append((str(path), None))
            continue
        except OSError as exc:
            message = f'Cannot read catalog {path}: {exc}'
            warnings.append(message)
            scope_issues.append({'message': message, 'scope_known': False})
            epoch.append((str(path), str(exc)))
            continue
        digest = hashlib.sha256(raw).hexdigest()
        epoch.append((str(path), digest))
        diagnostic = {'source_path': str(path), 'digest': digest, 'compositions': [],
                      'branch_owners': {name: list(paths) for name, paths in branch_owners.items()}, 'errors': []}
        catalogs.append(diagnostic)
        try:
            catalog = json.loads(raw)
            if not isinstance(catalog, dict) or type(catalog.get('schemaVersion')) is not int or catalog['schemaVersion'] != 1 or not isinstance(catalog.get('stacks'), list):
                raise ValueError('expected schemaVersion 1 and stacks array')
            if 'repository' in catalog and not isinstance(catalog['repository'], str):
                raise ValueError('repository identity must be a string')
            if catalog.get('repository') and repository['identity'] and catalog['repository'] != repository['identity']:
                raise ValueError('catalog repository differs from selected remote')
            for item in catalog['stacks']:
                try:
                    normalized = _normalize(item, refs)
                    candidates.append(normalized)
                    # Recovery evidence is independent of authoritative selection:
                    # preserve every valid catalog definition, including disputes.
                    composition = {'trunk': normalized['trunk'],
                                   'branches': [{'name': branch['name'], 'pr_number': (branch.get('pr') or {}).get('number')}
                                                for branch in normalized['branches']]}
                    composition.update({key: normalized[key] for key in ('id', 'number') if key in normalized})
                    diagnostic['compositions'].append(composition)
                except ValueError as exc:
                    diagnostic['errors'].append(str(exc))
                    message = f'Invalid stack in {path}: {exc}; inspect catalog without migrating it'
                    warnings.append(message)
                    scope_issues.append(dict(_scope_hint(item), message=message))
        except (ValueError, UnicodeError) as exc:
            diagnostic['errors'].append(str(exc))
            message = f'Invalid catalog {path}: {exc}; inspect catalog without migrating it'
            warnings.append(message)
            scope_issues.append({'message': message, 'scope_known': False})
    unique, blocked = [], set()
    for candidate in candidates:
        if candidate in unique:
            continue
        unique.append(candidate)
    for i, left in enumerate(unique):
        for j in range(i):
            right = unique[j]
            overlap = {b['name'] for b in left['branches']} & {b['name'] for b in right['branches']}
            pr_overlap = {(b.get('pr') or {}).get('number') for b in left['branches']} & {(b.get('pr') or {}).get('number') for b in right['branches']}
            same_id = any(left.get(k) is not None and left.get(k) == right.get(k) for k in ('id', 'number'))
            if overlap or (pr_overlap - {None}) or same_id:
                blocked.update((i, j))
                message = 'Conflicting stack identities/orders/membership in local catalogs; affected stacks omitted; reconcile catalogs explicitly'
                for affected in (left, right):
                    scope_issues.append({'message': message, 'scope_known': True,
                                         'branches': [branch['name'] for branch in affected['branches']],
                                         'pr_numbers': [(branch.get('pr') or {}).get('number') for branch in affected['branches']],
                                         'id': affected.get('id'), 'number': affected.get('number')})
    if blocked:
        warnings.append('Conflicting stack identities/orders/membership in local catalogs; affected stacks omitted; reconcile catalogs explicitly')
    stacks = [s for i, s in enumerate(unique) if i not in blocked]
    for stack in stacks:
        stack['worktree'] = next((owners[b['name']] for b in reversed(stack['branches']) if b['name'] in owners), None)
    if not epoch or not any(value for _, value in epoch):
        warnings.append('No local gh-stack catalog; remote-only stacks may still exist')
    fingerprint = hashlib.sha256(json.dumps([epoch, refs, repository['identity'], remote, records], sort_keys=True).encode()).hexdigest()
    return {'repository': repository, 'refs': refs, 'stacks': stacks, 'catalogs': catalogs,
            'warnings': warnings, 'scope_issues': scope_issues, 'fingerprint': fingerprint}


def evaluate_stack_conflicts(stack, refs, remote='origin', run_fn=run):
    """Probe every active layer plus top/trunk; exit 1 alone proves conflict."""
    if not _branch(remote):
        raise ToolError('invalid remote name')
    def resolve(name):
        if not _branch(name):
            return None
        sha = refs.get(f'refs/remotes/{remote}/{name}') or refs.get('refs/heads/' + name)
        return sha if isinstance(sha, str) and re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', sha) else None
    memo = {}
    epoch = _merge_epoch(run_fn)
    def probe(base, head):
        key = (base, head)
        reusable_key = (epoch, base, head)
        if epoch is not None and reusable_key in _CONFLICT_CACHE:
            memo[key] = _CONFLICT_CACHE[reusable_key]
            _CONFLICT_CACHE.move_to_end(reusable_key)
        if key not in memo:
            if not base or not head:
                memo[key] = (None, 'missing base/head ref or object; fetch relevant refs/history')
            else:
                try:
                    proc = run_fn(['git', 'merge-tree', '--write-tree', base, head], check=False)
                    memo[key] = ((True, 'local merge clean') if proc.returncode == 0 else
                                 (False, 'local content conflict') if proc.returncode == 1 else
                                 (None, 'merge-tree unavailable/history incomplete: ' + (proc.stderr or proc.stdout).strip()))
                except ToolError as exc:
                    memo[key] = (None, str(exc))
            if epoch is not None and memo[key][0] is not None:
                _CONFLICT_CACHE[reusable_key] = memo[key]
                while len(_CONFLICT_CACHE) > _CONFLICT_CACHE_LIMIT:
                    _CONFLICT_CACHE.popitem(last=False)
        clean, reason = memo[key]
        return {'base': base, 'head': head, 'clean': clean, 'reason': reason}
    trunk = resolve(stack.get('trunk'))
    parent, top = trunk, None
    layers = []
    for branch in stack.get('branches', []):
        if branch.get('isMerged') or (branch.get('pr') or {}).get('state') == 'MERGED':
            parent = trunk
            continue
        head = resolve(branch.get('name'))
        layers.append({'branch': branch.get('name'), **probe(parent, head)})
        parent, top = head, head
    combined = probe(trunk, top) if layers else {'base': trunk, 'head': None, 'clean': None, 'reason': 'no active layers'}
    values = [layer['clean'] for layer in layers] + [combined['clean']]
    clean = False if False in values else True if all(v is True for v in values) else None
    return {'layers': layers, 'combined': combined, 'clean': clean}
