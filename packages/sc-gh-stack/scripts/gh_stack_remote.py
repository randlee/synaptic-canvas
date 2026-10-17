#!/usr/bin/env python3
"""Scoped GitHub observations, shared across worktrees (stdlib only).

No discovery or authentication probes are performed. Callers supply locally
resolved repository identity and, when available, expected hosted head SHAs.
"""
from __future__ import annotations

import contextlib
import email.utils
try:
    import fcntl
except ImportError:  # Windows: use an exclusive sidecar lock below.
    fcntl = None
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlencode, urlparse

from gh_stack_shared import run

SCHEMA = 1
COMMON = ('number', 'state', 'isDraft', 'baseRefName', 'headRefName', 'headRefOid')
STATUS = COMMON + ('mergeable', 'mergeStateStatus', 'ci')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _read(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.snapshot-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class StackDataClient:
    """Acquire only missing requested observations; failures retain explicit unknowns.

    ``observations`` maps PR numbers to per-field provenance records. A stale
    value is retained with freshness=stale, never promoted to fresh on failure.
    """

    def __init__(self, repository, cache_dir=None, run_fn=run, clock=time.time, deadline_seconds=30, monotonic=time.monotonic, sleep=time.sleep):
        self.repository = repository
        self.run = run_fn
        self.clock = clock
        self.monotonic = monotonic
        self.sleep = sleep
        # Local discovery and git transport must not consume the hosted-query
        # allowance. Start it only on the first API attempt, then retain one
        # deadline across all hosted acquisition methods on this client.
        self.deadline_seconds = deadline_seconds
        self.deadline = None
        self.host = repository.get('host') or 'github.com'
        self.owner = repository.get('owner')
        self.name = repository.get('name')
        identity = repository.get('auth_identity')
        # Credentials partition cache without persisting any credential material.
        credential = ((os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN'))
                      if self.host == 'github.com' or self.host.endswith('.ghe.com') else
                      (os.environ.get('GH_ENTERPRISE_TOKEN') or os.environ.get('GITHUB_ENTERPRISE_TOKEN')))
        config_root = Path(os.environ.get('GH_CONFIG_DIR') or Path.home() / '.config/gh')
        try:
            config_fingerprint = hashlib.sha256((config_root / 'hosts.yml').read_bytes()).hexdigest()
        except OSError:
            config_fingerprint = 'unknown'
        auth = [identity or 'unknown', _digest(credential) if credential else 'keychain', config_fingerprint]
        self.partition = _digest([self.host, auth])
        root = repository.get('canonical_root') or repository.get('root') or '.'
        directory = Path(cache_dir) if cache_dir is not None else Path(root) / '.sc/sc-gh-stack/output'
        self.cache_dir = directory
        key = _digest([SCHEMA, repository.get('common_dir'), self.host, self.owner, self.name, auth])
        self.path = directory / ('remote-' + key + '.json')
        self.lock_path = directory / ('remote-' + key + '.lock')
        # Unknown identities coordinate conservatively by host, even with tokens.
        pressure_key = _digest([self.host, identity or 'unknown'])
        self.pressure_path = Path(repository.get('cooldown_dir') or Path.home() / '.sc/sc-gh-stack') / (pressure_key + '.json')
        self.metrics = {'requests': 0, 'graphql_requests': 0, 'rest_requests': 0, 'cache_hits': 0, 'graphql_cost': 0, 'git_fetches': 0}
        self.warnings = []
        self.observations = {}
        self.branch_observations = {}
        self.stack_observations = {}
        self.snapshot_id = None
        self._stopped = False
        self._valid_repository = bool(self.owner and self.name and repository.get('host'))
        if not self._valid_repository:
            self._warn('Repository identity incomplete; hosted fields remain unknown')

    @contextlib.contextmanager
    def _lock(self, path, seconds=5):
        path.parent.mkdir(parents=True, exist_ok=True)
        if fcntl is None:
            sidecar = path.with_suffix(path.suffix + '.exclusive')
            deadline = time.monotonic() + seconds
            descriptor = None
            while time.monotonic() < deadline:
                try:
                    descriptor = os.open(str(sidecar), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    break
                except FileExistsError:
                    time.sleep(.02)
            try:
                yield descriptor is not None
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                    sidecar.unlink(missing_ok=True)
            return
        with path.open('a') as stream:
            deadline = time.monotonic() + seconds
            acquired = False
            while time.monotonic() < deadline:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except BlockingIOError:
                    time.sleep(.02)
            try:
                yield acquired
            finally:
                if acquired:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def _load(self):
        data = _read(self.path)
        if (data.get('schema') != SCHEMA or any(not isinstance(data.get(key), dict) for key in ('prs', 'rest', 'branches'))
                or not isinstance(data.get('refreshes', {}), dict)
                or any(not isinstance(entry, dict) or not isinstance(entry.get('value'), dict) or not isinstance(entry.get('fields'), dict) for entry in data.get('prs', {}).values())
                or any(not isinstance(entry, dict) for key in ('rest', 'branches') for entry in data.get(key, {}).values())):
            data = {'schema': SCHEMA, 'prs': {}, 'rest': {}, 'branches': {}}
        return data

    def _save(self, data):
        data['snapshot_id'] = _digest([data['prs'], data['rest'], data['branches']])
        _write(self.path, data)
        self.snapshot_id = data['snapshot_id']

    def _warn(self, message):
        if message not in self.warnings:
            self.warnings.append(message)

    def _request(self, endpoint, query=None, etag=None):
        if self._stopped or not self._valid_repository:
            return None, {}, None
        if self.deadline is None:
            self.deadline = self.monotonic() + self.deadline_seconds
        remaining = self.deadline - self.monotonic()
        if remaining <= 0:
            self._warn('GitHub acquisition deadline reached; remaining hosted facts are unknown')
            self._stopped = True
            return None, {}, None
        with self._lock(self.pressure_path.with_suffix('.lock'), seconds=min(5, remaining)) as acquired:
            pressure = _read(self.pressure_path)
            if not acquired or pressure.get('until', 0) > self.clock():
                self._warn('GitHub refresh deferred: shared cooldown or refresh in progress')
                self._stopped = True
                return None, {}, None
            # Cooperating adapter clients share a small start-rate bound, not
            # just reactive throttle handling. The lock remains held through
            # the request. Direct gh/extension calls outside this adapter do
            # not participate and remain the caller's responsibility.
            delay = max(0, pressure.get('next_request_at', 0) - self.clock())
            remaining = self.deadline - self.monotonic()
            if delay >= remaining:
                self._warn('GitHub acquisition deadline reached before shared request slot; remaining hosted facts are unknown')
                self._stopped = True
                return None, {}, None
            if delay:
                self.sleep(delay)
            cmd = ['gh', 'api', '--hostname', self.host, '-i', endpoint]
            if query is not None:
                cmd += ['-f', 'query=' + query]
            if etag:
                cmd += ['-H', 'If-None-Match: ' + etag]
            remaining = self.deadline - self.monotonic()
            if remaining <= 0:
                self._warn('GitHub acquisition deadline reached; remaining hosted facts are unknown')
                self._stopped = True
                return None, {}, None
            pressure['next_request_at'] = self.clock() + .25
            _write(self.pressure_path, pressure)
            self.metrics['requests'] += 1
            self.metrics['graphql_requests' if query else 'rest_requests'] += 1
            try:
                proc = self.run(cmd, check=False, cwd=str(self.repository.get('root') or '.'), timeout=remaining)
            except Exception as exc:
                self._warn('GitHub request failed: ' + str(exc))
                self._stopped = True
                return None, {}, None
            raw = proc.stdout or ''
            headers = {}
            status = 200 if proc.returncode == 0 else 0
            if raw.startswith('HTTP/'):
                pieces = re.split(r'\r?\n\r?\n', raw, maxsplit=1)
                lines = pieces[0].splitlines()
                status = int(lines[0].split()[1])
                for line in lines[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.lower()] = value.strip()
                raw = pieces[1] if len(pieces) > 1 else ''
            try:
                body = json.loads(raw) if raw.strip() else None
            except ValueError:
                body = None
            message = json.dumps(body) + (proc.stderr or '')
            throttle = status == 429 or (status == 403 and (
                headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in headers or
                any(term in message.lower() for term in ('rate limit', 'secondary', 'abuse'))))
            errors = body.get('errors') if isinstance(body, dict) else None
            if errors and any(term in message.lower() for term in ('rate_limit', 'rate limit', 'secondary')):
                throttle = True
            if throttle:
                until = self.clock() + 60
                retry = headers.get('retry-after', '')
                try:
                    until = max(until, self.clock() + float(retry))
                except ValueError:
                    try:
                        until = max(until, email.utils.parsedate_to_datetime(retry).timestamp())
                    except (ValueError, TypeError):
                        pass
                try:
                    until = max(until, float(headers.get('x-ratelimit-reset', 0)))
                except ValueError:
                    pass
                _write(self.pressure_path, dict(pressure, until=until, reason='throttle'))
                self._warn('GitHub throttled; shared cooldown recorded')
            if throttle or status not in (200, 201, 304) or proc.returncode != 0 or errors:
                self._stopped = True
                label = 'authentication/permission' if status in (401, 403) and not throttle else 'request'
                self._warn('GitHub %s failed (HTTP %s)%s' % (label, status, ': GraphQL errors' if errors else ''))
                # Partial GraphQL data cannot establish complete requested fields.
                return None, headers, status
            if headers.get('x-ratelimit-remaining') == '0':
                try:
                    until = float(headers.get('x-ratelimit-reset', self.clock() + 60))
                except ValueError:
                    until = self.clock() + 60
                _write(self.pressure_path, dict(pressure, until=until, reason='primary exhausted'))
                self._stopped = True
            return body, headers, status

    def _rest(self, data, endpoint, force=False):
        old = data['rest'].get(endpoint, {})
        if not force and 0 <= self.clock() - old.get('time', -1e20) < 120:
            return old.get('body')
        body, headers, status = self._request(endpoint, etag=old.get('etag'))
        if status == 304:
            body = old.get('body')
        if body is not None:
            data['rest'][endpoint] = {'body': body, 'time': self.clock(),
                                      'etag': headers.get('etag', old.get('etag') if status == 304 else None),
                                      'link': headers.get('link', old.get('link') if status == 304 else None)}
        return body

    def _store(self, data, pr, source, fields):
        if not isinstance(pr, dict) or not pr.get('number'):
            return
        key = str(pr['number'])
        old = data['prs'].get(key, {})
        if pr.get('headRefOid') and old.get('value', {}).get('headRefOid') != pr['headRefOid']:
            old = {}
        value = old.setdefault('value', {})
        provenance = old.setdefault('fields', {})
        for field in fields:
            if field in pr:
                value[field] = pr[field]
                provenance[field] = {'source': source, 'observed_at': self.clock(), 'head': pr.get('headRefOid')}
        data['prs'][key] = old

    @staticmethod
    def _normalize(pr):
        if not isinstance(pr, dict):
            return {}
        head, base = pr.get('head') or {}, pr.get('base') or {}
        state = str(pr.get('state', 'UNKNOWN')).upper()
        if pr.get('merged') or pr.get('merged_at'):
            state = 'MERGED'
        return {'number': pr.get('number'), 'state': state, 'isDraft': pr.get('draft', False),
                'headRefName': head.get('ref'), 'headRefOid': head.get('sha'),
                'baseRefName': base.get('ref')}

    def _fresh(self, entry, fields, expected=None):
        value = entry.get('value', {})
        if expected and value.get('headRefOid') != expected:
            return False
        ttl = 60 if value.get('ci') in ('PENDING', 'EXPECTED', 'IN_PROGRESS', 'QUEUED') else 120
        return all(field in value and not entry.get('fields', {}).get(field, {}).get('refresh_error')
                   and 0 <= self.clock() - entry.get('fields', {}).get(field, {}).get('observed_at', -1e20) < ttl for field in fields)

    def _result(self, data, numbers, fields, head_map):
        result = {}
        for number in numbers:
            entry = data['prs'].get(str(number), {})
            value = dict(entry.get('value', {}))
            provenance = {}
            for field in fields:
                observation = dict(entry.get('fields', {}).get(field, {}))
                fresh = self._fresh(entry, (field,), head_map.get(number))
                observation['freshness'] = 'fresh' if fresh else ('stale' if field in value else 'unknown')
                if not fresh:
                    observation['reason'] = observation.get('refresh_error') or entry.get('unavailable_reason') or 'missing, expired, or head changed'
                    if not observation.get('observed_at') and entry.get('unavailable_at') is not None:
                        observation.update(source='refresh', observed_at=entry['unavailable_at'])
                provenance[field] = observation
            self.observations[number] = provenance
            if value:
                # An old-head CI value must not be displayed against a new head.
                if head_map.get(number) and value.get('headRefOid') != head_map[number]:
                    value['ci'] = None
                result[number] = value
            if not self._fresh(entry, fields, head_map.get(number)):
                self._warn('PR #%s: requested hosted fields are stale or unknown' % number)
        self.snapshot_id = data.get('snapshot_id')
        return result

    def _prs(self, numbers, force=False, offline=False, fields='status', head_map=None):
        started = time.monotonic()
        if any(type(n) is not int or n <= 0 for n in numbers):
            raise ValueError('PR numbers must be positive integers')
        numbers = sorted(set(numbers))
        wanted = STATUS if fields == 'status' else COMMON
        head_map = head_map or {}
        scope = _digest([numbers, fields, head_map])
        with self._lock(self.lock_path) as acquired:
            data = self._load()
            coalesced = data.get('refreshes', {}).get(scope, -1e20) >= started
            def retry_deferred(number):
                entry = data['prs'].get(str(number), {})
                return (entry.get('unavailable_head') == head_map.get(number)
                        and 0 <= self.clock() - entry.get('unavailable_at', -1e20) < 60)
            missing = [n for n in numbers if (force and not coalesced) or (
                not self._fresh(data['prs'].get(str(n), {}), wanted, head_map.get(n)) and not retry_deferred(n))]
            self.metrics['cache_hits'] += len(numbers) - len(missing)
            if missing and acquired and not offline:
                # A requested refresh must not return the old green timestamp
                # as fresh after auth/throttle/deadline/partial-data failure.
                # Successful fields replace this marker in _store; values and
                # their original observation times remain useful on failure.
                for number in missing:
                    entry = data['prs'].get(str(number), {})
                    for field in wanted:
                        if field in entry.get('value', {}):
                            entry.setdefault('fields', {}).setdefault(field, {})['refresh_error'] = 'requested refresh incomplete or failed'
                if fields != 'status' and len(missing) <= 2:
                    for number in missing:
                        body = self._rest(data, 'repos/%s/%s/pulls/%s' % (self.owner, self.name, number), force=True)
                        self._store(data, self._normalize(body), 'REST', COMMON)
                        if self._stopped:
                            break
                else:
                    for start in range(0, len(missing), 50):
                        selection = ' '.join('p%s:pullRequest(number:%s){%s}' % (n, n, ' '.join(COMMON) + (' mergeable mergeStateStatus commits(last:1){nodes{commit{statusCheckRollup{state}}}}' if fields == 'status' else '')) for n in missing[start:start + 50])
                        query = 'query{repository(owner:%s,name:%s){%s} rateLimit{cost remaining resetAt}}' % (json.dumps(self.owner), json.dumps(self.name), selection)
                        body, _, _ = self._request('graphql', query=query)
                        if body:
                            payload = body.get('data') or {}
                            self.metrics['graphql_cost'] += (payload.get('rateLimit') or {}).get('cost', 0)
                            for pr in (payload.get('repository') or {}).values():
                                if isinstance(pr, dict):
                                    if fields == 'status':
                                        had_commits = 'commits' in pr
                                        nodes = (pr.pop('commits', None) or {}).get('nodes') or []
                                        commit = nodes[-1].get('commit') if nodes else None
                                        if commit is not None:
                                            pr['ci'] = (commit.get('statusCheckRollup') or {}).get('state', 'NONE')
                                        elif not nodes and had_commits:
                                            pr['ci'] = 'NONE'
                                    self._store(data, pr, 'GraphQL', wanted)
                        if self._stopped:
                            break
                for number in missing:
                    entry = data['prs'].setdefault(str(number), {'value': {}, 'fields': {}})
                    if not self._fresh(entry, wanted, head_map.get(number)):
                        entry.update(unavailable_at=self.clock(), unavailable_head=head_map.get(number),
                                     unavailable_reason='required hosted fields unavailable from last refresh; retry after 60s or explicitly refresh')
                    else:
                        for key in ('unavailable_at', 'unavailable_head', 'unavailable_reason'):
                            entry.pop(key, None)
                refreshes = data.setdefault('refreshes', {})
                refreshes[scope] = time.monotonic()
                if len(refreshes) > 256:
                    data['refreshes'] = dict(sorted(refreshes.items(), key=lambda item: item[1])[-256:])
                self._save(data)
            elif missing and not acquired:
                self._warn('GitHub refresh in progress; bounded wait expired')
            return self._result(data, numbers, wanted, head_map)

    def pr_details(self, numbers, force=False, offline=False, fields='status', head_map=None):
        return self._prs(numbers, force, offline, fields, head_map)

    def pr_metadata(self, numbers, force=False, offline=False, head_map=None):
        return self._prs(numbers, force, offline, 'metadata', head_map)

    def resolve_branches(self, branches, force=False, offline=False):
        started = time.monotonic()
        result = {}
        branches = sorted(set(branches))
        if any(not isinstance(branch, str) or not branch for branch in branches):
            raise ValueError('Branch names must be nonempty strings')
        scope = 'branches:' + _digest(branches)
        with self._lock(self.lock_path) as acquired:
            data = self._load()
            coalesced = data.get('refreshes', {}).get(scope, -1e20) >= started
            missing = []
            def observed(branch, entry):
                fresh = entry.get('complete', False) and 0 <= self.clock() - entry.get('time', -1e20) < 120
                self.branch_observations[branch] = {
                    'state': ('positive' if entry.get('pr') else 'negative') if fresh else 'unknown',
                    'exists': bool(entry.get('pr')) if fresh else None,
                    'source': entry.get('source'), 'observed_at': entry.get('time'),
                    'freshness': 'fresh' if fresh else ('stale' if entry.get('time') is not None else 'unknown'),
                    'reason': entry.get('reason') if not fresh else ('PR mapping confirmed' if entry.get('pr') else 'No open PR for this branch'),
                }
                if fresh and entry.get('pr'):
                    pr = entry['pr']
                    result[branch] = dict(pr)
                    self._result(data, [pr['number']], COMMON, {})
            for branch in branches:
                cached = data['branches'].get(branch, {})
                if (not force or coalesced) and cached.get('complete') and 0 <= self.clock() - cached.get('time', -1e20) < 120:
                    observed(branch, cached)
                    continue
                if ((not force or coalesced)
                        and 0 <= self.clock() - cached.get('unavailable_at', -1e20) < 60):
                    observed(branch, cached)
                    self._warn('Branch %s: PR mapping unknown; retry deferred after incomplete refresh' % branch)
                    continue
                if offline or not acquired or self._stopped:
                    observed(branch, {**cached, 'complete': False, 'reason': 'PR mapping unavailable: offline, failed request, or refresh in progress'})
                    self._warn('Branch %s: PR mapping unknown' % branch)
                    continue
                missing.append(branch)
            def accept(branch, nodes, source, complete):
                matches = [pr for pr in nodes if isinstance(pr, dict) and pr.get('headRefName') == branch
                           and pr.get('state') == 'OPEN' and (pr.get('headRepositoryNameWithOwner') or '').lower() == (self.owner + '/' + self.name).lower()]
                valid = all(isinstance(pr, dict) and type(pr.get('number')) is int and pr['number'] > 0
                            and all(field in pr and pr[field] is not None for field in COMMON)
                            and pr.get('headRepositoryNameWithOwner') for pr in nodes)
                complete = complete and valid and len(matches) <= 1
                entry = {'time': self.clock(), 'source': source, 'complete': complete,
                         'pr': matches[0] if complete and matches else None,
                         'reason': None if complete else 'Ambiguous or incomplete PR mapping'}
                if complete:
                    data['branches'][branch] = entry
                    if entry['pr']:
                        self._store(data, entry['pr'], source, COMMON)
                else:
                    # A failed/partial acquisition is unknown, not confirmed
                    # absence. Persist the failure separately from the prior
                    # observation so later worktrees do not immediately repeat
                    # the same denied or ambiguous query.
                    entry = dict(data['branches'].get(branch, {}), complete=False,
                                 unavailable_at=self.clock(), reason=entry['reason'])
                    data['branches'][branch] = entry
                observed(branch, entry)
                if not complete:
                    self._warn('Branch %s: ambiguous or incomplete PR mapping' % branch)
            if len(missing) <= 2:
                for branch in missing:
                    if self._stopped:
                        accept(branch, [], None, False)
                        continue
                    endpoint = 'repos/%s/%s/pulls?%s' % (self.owner, self.name, urlencode({'state': 'open', 'head': self.owner + ':' + branch, 'per_page': 100}))
                    # Mapping freshness/retry suppression is managed above.
                    # Revalidate the REST body on an actual retry rather than
                    # re-promoting an older response after a failed refresh.
                    body = self._rest(data, endpoint, force=True)
                    nodes = [{**self._normalize(pr), 'headRepositoryNameWithOwner': ((pr.get('head') or {}).get('repo') or {}).get('full_name')} for pr in body if isinstance(pr, dict)] if isinstance(body, list) else []
                    complete = isinstance(body, list) and len(nodes) == len(body) and not re.search(r'rel="next"', data['rest'].get(endpoint, {}).get('link') or '')
                    accept(branch, nodes, 'REST', bool(complete))
            else:
                for start in range(0, len(missing), 50):
                    batch = missing[start:start + 50]
                    if self._stopped:
                        for branch in batch:
                            accept(branch, [], None, False)
                        continue
                    selection = ' '.join('b%s:pullRequests(headRefName:%s,states:OPEN,first:2){nodes{%s headRepository{nameWithOwner}} pageInfo{hasNextPage}}' % (i, json.dumps(branch), ' '.join(COMMON)) for i, branch in enumerate(batch))
                    query = 'query{repository(owner:%s,name:%s){%s} rateLimit{cost remaining resetAt}}' % (json.dumps(self.owner), json.dumps(self.name), selection)
                    body, _, _ = self._request('graphql', query=query)
                    payload = body.get('data') or {} if isinstance(body, dict) else {}
                    self.metrics['graphql_cost'] += (payload.get('rateLimit') or {}).get('cost', 0)
                    repository = payload.get('repository') or {}
                    for i, branch in enumerate(batch):
                        connection = repository.get('b%s' % i) or {}
                        nodes = connection.get('nodes')
                        normalized = [{**pr, 'headRepositoryNameWithOwner': (pr.get('headRepository') or {}).get('nameWithOwner')} for pr in nodes if isinstance(pr, dict)] if isinstance(nodes, list) else []
                        complete = isinstance(nodes, list) and len(normalized) == len(nodes) and connection.get('pageInfo', {}).get('hasNextPage') is False
                        accept(branch, normalized, 'GraphQL', complete)
            if acquired and not offline:
                if missing:
                    data.setdefault('refreshes', {})[scope] = time.monotonic()
                self._save(data)
            return result

    def refresh_stack(self, number, force=False):
        if type(number) is not int or number <= 0:
            raise ValueError('Stack number must be a positive integer')
        started = time.monotonic()
        with self._lock(self.lock_path) as acquired:
            if not acquired:
                self._warn('Stack refresh in progress')
                self.stack_observations[number] = {'source': None, 'freshness': 'unknown',
                                                   'complete': False, 'observed_at': None,
                                                   'reason': 'Stack refresh in progress'}
                return None
            data = self._load()
            endpoint = 'repos/%s/%s/stacks/%s' % (self.owner, self.name, int(number))
            first_endpoint = endpoint
            requests_before = self.metrics['requests']
            scope = 'stack:' + str(number)
            coalesced = data.get('refreshes', {}).get(scope, -1e20) >= started
            force = force and not coalesced
            first = None
            complete = True
            seen = set()
            observed_times = []
            page_identity = {'number': number}
            while endpoint and endpoint not in seen:
                seen.add(endpoint)
                cached = data['rest'].get(endpoint, {})
                reused = not force and 0 <= self.clock() - cached.get('time', -1e20) < 120
                body = self._rest(data, endpoint, force=force)
                entry = data['rest'].get(endpoint, {})
                if entry.get('time') is not None:
                    observed_times.append(entry['time'])
                if body is None:
                    complete = False
                    break
                if (not isinstance(body, dict) or not isinstance(body.get('pull_requests'), list)
                        or ('number' in body and (type(body['number']) is not int or body['number'] != number))
                        or any(key in body and key in page_identity and body[key] != page_identity[key]
                               for key in ('id', 'node_id'))):
                    self._warn('Malformed or inconsistent stack structural page')
                    complete = False
                    break
                for key in ('id', 'node_id'):
                    if key in body:
                        page_identity[key] = body[key]
                if not reused:
                    entry.pop('stack_refresh_failed', None)
                if entry.get('stack_refresh_failed'):
                    complete = False
                    break
                if first is None:
                    first = json.loads(json.dumps(body))
                else:
                    first['pull_requests'].extend(body['pull_requests'])
                link = data['rest'].get(endpoint, {}).get('link') or ''
                match = re.search(r'<([^>]+)>;\s*rel="next"', link)
                endpoint = None
                if match:
                    parsed = urlparse(match.group(1))
                    if parsed.netloc not in ('api.' + self.host, self.host):
                        self._warn('Rejected cross-host stack pagination')
                        complete = False
                        break
                    endpoint = parsed.path.lstrip('/') + ('?' + parsed.query if parsed.query else '')
                if self._stopped:
                    complete = endpoint is None
                    break
            if endpoint in seen:
                complete = False
                self._warn('Stack pagination cycle; structural response incomplete')
            if not complete and first_endpoint in data['rest']:
                # A failed explicit refresh must not make the old structural
                # response fresh again merely because its original TTL remains.
                data['rest'][first_endpoint]['stack_refresh_failed'] = True
            observed_at = min(observed_times) if observed_times else None
            self.stack_observations[number] = {
                'source': 'REST' if self.metrics['requests'] > requests_before else ('cached' if observed_at is not None else None),
                'freshness': 'fresh' if complete else ('stale' if observed_at is not None else 'unknown'),
                'complete': complete, 'observed_at': observed_at,
                'reason': None if complete else 'Stack structural response incomplete or last refresh failed',
            }
            data.setdefault('refreshes', {})[scope] = time.monotonic()
            self._save(data)
            if not complete:
                self._warn('Stack structural response incomplete')
                return None
            return first

    def invalidate(self, numbers=None):
        with self._lock(self.lock_path) as acquired:
            if not acquired:
                self._warn('Cache invalidation deferred: refresh in progress')
                return
            data = self._load()
            if numbers is None:
                data['prs'], data['branches'], data['rest'] = {}, {}, {}
            else:
                affected = {int(n) for n in numbers}
                for number in affected:
                    data['prs'].pop(str(number), None)
                data['branches'] = {branch: entry for branch, entry in data['branches'].items() if not entry.get('pr') or entry['pr'].get('number') not in affected}
                # Structural REST payloads may contain the changed PR.
                data['rest'] = {}
            self._save(data)

    def refresh_git(self, force=False, offline=False, refs=None):
        """Fetch only required branch refs, sharing per-ref freshness across readers.

        ``refs=None`` retains the legacy configured-refspec fetch. Explicit
        scopes never inherit freshness from a different explicit ref scope.
        A deleted catalog branch is negatively cached, not allowed to abort
        refresh of every surviving branch in the same scope.
        """
        from gh_stack_local import _branch
        started = time.monotonic()
        remote = self.repository.get('remote') or 'origin'
        if not _branch(remote):
            raise ValueError('invalid remote name')
        selected = None if refs is None else sorted(set(refs))
        if selected is not None and any(not _branch(ref) for ref in selected):
            raise ValueError('fetch refs must be valid branch names')
        requested = ['*'] if selected is None else selected
        key = _digest([self.repository.get('common_dir'), remote, self.host, self.owner, self.name])
        path = self.cache_dir / ('git-' + key + '.json')
        def fresh(entry):
            stamp = entry.get('observed_at')
            return stamp is not None and 0 <= self.clock() - stamp < 60 and not entry.get('error')
        def entry_for(state, ref):
            entries = state.get('refs', {})
            # A configured broad refspec may actually exclude branches. Its
            # success cannot establish coverage for an explicit scope.
            return entries.get(ref, {})
        def result(state, fetched=False):
            entries = [entry_for(state, ref) for ref in requested]
            complete = all(fresh(entry) for entry in entries)
            stamps = [entry.get('observed_at') for entry in entries]
            stamp = min(stamps) if stamps and all(value is not None for value in stamps) else None
            errors = list(dict.fromkeys(entry['error'] for entry in entries if entry.get('error')))
            return {'fresh': complete, 'observed_at': stamp,
                    'source': 'fetched' if fetched else ('cached' if complete else ('stale' if any(value is not None for value in stamps) else 'unknown')),
                    'error': '; '.join(errors) or None,
                    'refs': {ref: dict(entry_for(state, ref), fresh=fresh(entry_for(state, ref))) for ref in requested}}
        with self._lock(path.with_suffix('.lock')) as acquired:
            state = _read(path)
            if 'refs' not in state:
                state = {'refs': {'*': state} if state else {}}
            missing = []
            for ref in requested:
                entry = entry_for(state, ref)
                coalesced = entry.get('completed_monotonic', -1e20) >= started
                if (not fresh(entry) or (force and not coalesced)) and entry.get('retry_at', 0) <= self.clock():
                    missing.append(ref)
            if offline or not acquired or not missing:
                return result(state)
            # Git work has its own total bound; it must not consume the hosted
            # API budget before the first API request has even been attempted.
            git_deadline = self.monotonic() + 60
            def invoke(command):
                remaining = git_deadline - self.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Git refresh deadline reached')
                return self.run(command, check=False,
                                cwd=str(self.repository.get('root') or '.'), timeout=remaining)
            def fetch(names):
                self.metrics['git_fetches'] += 1
                command = ['git', 'fetch', '--quiet']
                if selected is None:
                    command += ['--', remote]
                else:
                    command += ['--no-tags', '--no-recurse-submodules', '--', remote]
                    command += ['+refs/heads/%s:refs/remotes/%s/%s' % (ref, remote, ref) for ref in names]
                try:
                    proc = invoke(command)
                    return (proc.stderr or proc.stdout or 'git fetch failed').strip() if proc.returncode else None
                except Exception as exc:
                    return str(exc)
            error = fetch(missing)
            absent, successful = set(), set(missing) if not error else set()
            if selected is not None and error and re.search(r"could(?:n't| not) find remote ref", error, re.I):
                # One advertisement read partitions the entire scope. Retrying
                # each ref separately would turn a stale stack into O(N) reads.
                try:
                    self.metrics['git_ref_discoveries'] = self.metrics.get('git_ref_discoveries', 0) + 1
                    advertised = invoke(['git', 'ls-remote', '--heads', '--', remote,
                                         *['refs/heads/' + ref for ref in missing]])
                    if advertised.returncode:
                        raise ValueError((advertised.stderr or advertised.stdout or 'remote ref discovery failed').strip())
                    present = set()
                    for line in advertised.stdout.splitlines():
                        match = re.fullmatch(r'([0-9a-fA-F]{40}|[0-9a-fA-F]{64})\s+refs/heads/(.+)', line)
                        if not match or match[2] not in missing:
                            raise ValueError('Invalid remote ref advertisement')
                        present.add(match[2])
                    absent = set(missing) - present
                    if present:
                        error = fetch(sorted(present))
                        if not error:
                            successful = present
                except Exception as exc:
                    error = str(exc)
            for ref in missing:
                entry = dict(state['refs'].get(ref, {}))
                if ref in absent:
                    entry.update(error='Remote branch not advertised: ' + ref, exists=False,
                                 retry_at=self.clock() + 60, completed_monotonic=time.monotonic())
                elif ref not in successful:
                    entry.update(error=error, retry_at=self.clock() + 15, completed_monotonic=time.monotonic())
                else:
                    entry = {'observed_at': self.clock(), 'completed_monotonic': time.monotonic(), 'error': None, 'exists': True}
                state['refs'][ref] = entry
            if error:
                self._warn('Git fetch failed; remote refs are stale: ' + error)
            if absent:
                self._warn('Remote branches absent; surviving refs refreshed independently: ' + ', '.join(sorted(absent)))
            _write(path, state)
            return result(state, fetched=bool(successful))
