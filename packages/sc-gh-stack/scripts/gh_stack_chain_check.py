#!/usr/bin/env python3
"""Pre-link chain check for a proposed gh stack (read-only).

Installed as ``.claude/scripts/gh_stack_chain_check.py`` by the sc-gh-stack
package.  Given a trunk and the intended layer order (bottom to top, branch
names or PR numbers), it verifies what the stack writer otherwise checks by
hand before every ``gh stack link``:

* every layer head is pushed (``origin/<branch>`` exists);
* each layer contains its parent's pushed head (``git merge-base
  --is-ancestor``), so the chain is linear;
* the PR for each layer, if one exists, is open, not a draft, its head is the
  pushed head, and its base is the expected parent (the trunk for the bottom);
* the top merges clean into the trunk (``git merge-tree --write-tree``, exit
  code only; never the legacy 3-arg form).

Local catalogs and batched refs identify layers before scoped cached/API reads.
Every intended layer and the top/trunk pair receive local conflict checks.

Exit codes: 0 chain is linkable, 1 problems listed under VERDICT, 2 the
environment failed (one ``gh-stack-chain-check: ...`` line on stderr).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_stack_shared import ToolError, guarded, is_ancestor, origin_sha, run, short, ReportArgumentParser, compact_report  # noqa: E402
from gh_stack_local import read_local_snapshot, evaluate_stack_conflicts, scope_diagnostics, _branch as valid_branch
from gh_stack_remote import StackDataClient
from gh_stack_view import add_refresh_options, _selected, _catalog_composition, _scope_epoch, _git_scope_fresh


def merge_clean(base_sha: str, head_sha: str) -> bool | None:
    """True/False from ``git merge-tree --write-tree``; None when git is too old."""
    proc = run(["git", "merge-tree", "--write-tree", base_sha, head_sha], check=False)
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None  # usage error: git < 2.38 or an unexpected failure


PR_FIELDS = "number,headRefName,baseRefName,headRefOid,isDraft,state"


def list_prs(branches=None, *, client=None) -> list[dict]:
    """Compatibility helper; never scan unrelated repository PRs."""
    if not branches:
        return []
    client = client or StackDataClient(read_local_snapshot(run_fn=run)["repository"], run_fn=run)
    return list(client.resolve_branches(branches).values())


def index_prs(prs: list[dict]) -> tuple[dict[int, dict], dict[str, dict]]:
    """Map PR number -> PR and head branch -> the OPEN PR for it (else newest)."""
    prs = [p for p in prs if isinstance(p, dict) and isinstance(p.get("number"), int) and isinstance(p.get("headRefName"), str)]
    by_number = {int(p["number"]): p for p in prs}
    by_branch: dict[str, dict] = {}
    for p in sorted(prs, key=lambda p: int(p["number"])):
        cur = by_branch.get(p["headRefName"])
        if cur is None or (cur.get("state") != "OPEN" and p.get("state") == "OPEN"):
            by_branch[p["headRefName"]] = p
        elif cur.get("state") == p.get("state"):
            by_branch[p["headRefName"]] = p  # newest wins among equals
    return by_number, by_branch


def view_pr(number: int, *, client=None, offline=False) -> dict:
    """Targeted cached/REST lookup; no GraphQL-first PR command."""
    client = client or StackDataClient(read_local_snapshot(run_fn=run)["repository"], run_fn=run)
    data = client.pr_metadata([number], offline=offline).get(number)
    if not data or not isinstance(data.get("headRefName"), str):
        raise ToolError(f"PR #{number} branch mapping unknown; supply a branch name or refresh its metadata", "STATE.PR_UNKNOWN")
    return data


def resolve_layers(args: list[str], by_number: dict[int, dict], by_branch: dict[str, dict] | None = None, *, offline=False, client=None) -> list[str]:
    """Resolve numeric identifiers from local/cache before any scoped lookup."""
    layers = []
    for arg in args:
        if arg.isdigit():
            pr = by_number.get(int(arg))
            if pr is None:
                pr = view_pr(int(arg), client=client, offline=offline) if client is not None else (
                    None if offline else view_pr(int(arg)))
                if not pr:
                    raise ToolError(f"PR #{arg} has no local mapping; pass its branch name (--no-pr makes no API calls)", "STATE.PR_UNKNOWN")
                by_number[int(arg)] = pr
                if by_branch is not None:
                    by_branch.setdefault(pr["headRefName"], pr)
            layers.append(pr["headRefName"])
        else:
            layers.append(arg)
    return layers


def evaluate(trunk: str, layers: list[str], by_branch: dict[str, dict], *, fetched: bool, use_pr: bool, refs=None, remote="origin", conflicts=None, ref_observations=None, pr_observations=None) -> dict:
    """Pure chain evaluation over injected lookups (origin_sha, is_ancestor, merge_clean)."""
    rows: list[dict] = []
    problems: list[str] = []
    notes: list[str] = []
    resolve = (lambda name: refs.get(f"refs/remotes/{remote}/{name}")) if refs is not None else origin_sha
    fresh = lambda name: fetched and (ref_observations is None or ref_observations.get(name, {}).get('fresh') is True)
    trunk_sha = resolve(trunk) if fresh(trunk) else None
    if fetched and trunk_sha is None and ref_observations is None:
        raise ToolError(f"origin/{trunk} does not exist; pass the trunk branch name exactly as on origin")
    if len(layers) != len(set(layers)):
        problems.append("a branch appears twice in the proposed order")
    if trunk in layers:
        problems.append(f"{trunk} is the trunk; it is never a layer (drop it from the list)")
    if any(not n.strip() for n in layers):
        problems.append("an empty branch name was passed")
    parent_name = trunk
    parent_sha = trunk_sha
    for idx, name in enumerate(layers, start=1):
        sha = resolve(name) if fresh(name) else None
        pr = by_branch.get(name) if use_pr else None
        trusted = lambda field: pr_observations is None or pr_observations.get((pr or {}).get('number'), {}).get(field, {}).get('freshness') == 'fresh'
        row = {"layer": idx, "branch": name, "origin": sha, "pr": pr.get("number") if pr else None,
               "pushed": None if not fresh(name) else sha is not None, "contains_parent": None,
               "pr_base_ok": None, "pr_head_ok": None, "draft": bool(pr and pr.get("isDraft")),
               "pr_state": pr.get("state") if pr else None, "expected_base": parent_name}
        if fresh(name) and sha is None:
            problems.append(f"L{idx} {name}: not on origin (unpushed) -> push it before linking")
        elif sha and parent_sha:
            row["contains_parent"] = is_ancestor(parent_sha, sha)
            if not row["contains_parent"]:
                if idx == 1:
                    if is_ancestor(sha, parent_sha):
                        problems.append(f"L1 {name}: has no commits beyond {trunk} (already merged or empty)")
                    else:
                        notes.append(f"L1 {name}: behind {trunk} ({short(sha)} does not contain {short(parent_sha)}); fine unless CONFLICTING, do not rebase just to catch up")
                        row["contains_parent"] = None
                else:
                    problems.append(f"L{idx} {name}: does not contain parent {parent_name} @ {short(parent_sha)} -> cut from a stale head or a fork; declare a merge-forward or reorder")
        if pr:
            if trusted('state') and pr.get("state") is not None and pr.get("state") != "OPEN":
                problems.append(f"L{idx} {name}: PR #{pr['number']} is {pr.get('state')} -> a merged/closed PR cannot be linked; open a new one")
            if trusted('isDraft') and pr.get("isDraft"):
                problems.append(f"L{idx} {name}: PR #{pr['number']} is DRAFT -> blocks gh stack merge; mark ready before landing")
            base_ok = pr.get("baseRefName") == parent_name if trusted('baseRefName') and pr.get('baseRefName') is not None else None
            row["pr_base_ok"] = base_ok
            if base_ok is False:
                notes.append(f"L{idx} {name}: PR #{pr['number']} base is {pr.get('baseRefName')}, expected {parent_name}; `gh stack link --base {trunk} ...` corrects it, verify afterwards")
            if fetched and sha:
                head_ok = pr.get("headRefOid") == sha if trusted('headRefOid') and pr.get('headRefOid') is not None else None
                row["pr_head_ok"] = head_ok
                if head_ok is False:
                    problems.append(f"L{idx} {name}: PR #{pr['number']} head {short(pr.get('headRefOid'))} != origin {short(sha)} -> stale PR head; wait for GitHub or re-push")
        elif use_pr:
            notes.append(f"L{idx} {name}: no PR yet; `gh stack link` creates one with base {parent_name}")
        rows.append(row)
        parent_name = name
        parent_sha = sha if ref_observations is not None else sha or parent_sha
    landing: dict = {"clean": None, "reason": "not judged"}
    if fetched and rows and rows[-1]["origin"] and trunk_sha and not any(r["pushed"] is False for r in rows):
        result = conflicts['combined']['clean'] if conflicts is not None else merge_clean(trunk_sha, rows[-1]["origin"])
        if result is None:
            landing = {"clean": None, "reason": "git merge-tree --write-tree unavailable (git < 2.38); check with a scratch `git merge --no-commit`"}
        elif result:
            landing = {"clean": True, "reason": f"top {rows[-1]['branch']} @ {short(rows[-1]['origin'])} merges clean into {trunk} @ {short(trunk_sha)}"}
        else:
            landing = {"clean": False, "reason": f"top {rows[-1]['branch']} conflicts with {trunk}; resolve on a new top layer, never on a frozen one"}
            problems.append(f"top {rows[-1]['branch']}: merge into {trunk} conflicts")
    report = {"trunk": trunk, "trunk_origin": trunk_sha, "rows": rows, "problems": problems,
              "notes": notes, "landing": landing, "linkable": not problems}
    report["link_command"] = link_command(report) if report["linkable"] and rows else None
    return report


def icon(value: bool | None) -> str:
    return {True: "✅", False: "⛔", None: "❓"}[value]


def render(report: dict, *, full=False) -> str:
    def priority(row):
        return (not row.get('changed', False),
                not (row.get('local_merge_clean') is False or row.get('pushed') is False or row.get('pr_head_ok') is False or row.get('pr_base_ok') is False),
                not row.get('unknown', False), row['layer'])
    shown = report['rows'] if full else sorted(report['rows'], key=priority)[:10]
    lines = [f"chain: {len(report['rows'])} layer(s) -> {report['trunk']} @ {short(report['trunk_origin'])}", ""]
    hdr = ["L", "branch", "PR", "pushed", "contains parent", "PR base", "PR head", "local merge"]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "|".join("---" for _ in hdr) + "|")
    for r in shown:
        pr = f"#{r['pr']}" + (" (draft)" if r["draft"] else "") if r["pr"] else "-"
        lines.append("| " + " | ".join([f"{r['layer']}/{len(report['rows'])}", r["branch"], pr,
                                        icon(r["pushed"]), icon(r["contains_parent"]),
                                        icon(r["pr_base_ok"]) if r["pr"] else "-",
                                        icon(r["pr_head_ok"]) if r["pr"] else "-",
                                        icon(r.get('local_merge_clean'))]) + " |")
    lines.append("")
    if len(shown) < len(report['rows']):
        lines.append(f"truncated: showing {len(shown)} of {len(report['rows'])} layers; --full or --json for all")
    lines.append(f"local content: {sum(row.get('local_merge_clean') is False for row in report['rows'])} conflict(s), {sum(row.get('local_merge_clean') is None for row in report['rows'])} unknown layer(s)")
    if report["problems"]:
        lines.append(f"VERDICT: ❌ NOT LINKABLE ({len(report['problems'])} issue(s))")
        lines.extend(f"- {p}" for p in (report["problems"] if full else report["problems"][:10]))
        if not full and len(report['problems']) > 10:
            lines.append('issues truncated; --full or --json for all')
    elif report.get('linkable') is not True:
        lines.append('VERDICT: ❓ UNKNOWN - required observations are incomplete or stale')
    else:
        lines.append("VERDICT: ✅ LINKABLE - every head pushed, chain linear, PR state consistent")
    land = report["landing"]
    lines.append(f"MERGE INTO TRUNK: {icon(land['clean'])} {land['reason']}")
    lines.extend(f"- note: {n}" for n in (report["notes"] if full else report["notes"][:10]))
    if report.get('snapshot_id'):
        lines.append(f"snapshot {report['snapshot_id']}; git {report['git_observation']['source']}; {report.get('unknown_count', 0)} unknown layer(s)")
    lines.extend('warning: ' + warning for warning in report.get('warnings', [])[:5])
    if report["linkable"] and report["rows"]:
        lines.append("")
        lines.append("next: " + link_command(report))
        if any(not r["pr"] for r in report["rows"]):
            lines.append("      (a bare branch name pushes the LOCAL ref: run it from that layer's own worktree, or open its PR first and re-run the check)")
        else:
            lines.append("      (run from a worktree checked out on a stack branch)")
    return "\n".join(lines)


def link_command(report: dict) -> str:
    """Shell-safe: bare PR numbers, never `#N` (a `#` starts a comment in bash)."""
    return f"gh stack link --base {shlex.quote(report['trunk'])} " + " ".join(
        str(r["pr"]) if r["pr"] else shlex.quote(r["branch"]) for r in report["rows"])


def preflight(*, need_gh: bool) -> None:
    for tool in ("git",) + (("gh",) if need_gh else ()):
        if not shutil.which(tool):
            raise ToolError(f"`{tool}` not on PATH")
    if run(["git", "rev-parse", "--git-dir"], check=False).returncode != 0:
        raise ToolError("not inside a git repository")


def main() -> int:
    ap = ReportArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trunk", required=True, help="branch the stack lands on (e.g. develop, integrate/phase-bc)")
    ap.add_argument("layers", nargs="+", help="proposed order bottom to top: branch names or PR numbers")
    ap.add_argument("--no-fetch", action="store_true", help="skip `git fetch origin`; compare against the cached origin/* refs")
    ap.add_argument("--no-pr", action="store_true", help="strictly no API calls; use qualified local/cache mapping")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    add_refresh_options(ap)
    args = ap.parse_args()
    if args.compact_json and (args.json or args.full):
        ap.error('--compact-json conflicts with --json and --full')
    if args.no_fetch and (args.refresh_git or args.refresh):
        ap.error('--no-fetch conflicts with an explicit git refresh')
    if args.no_pr and (args.refresh_status or args.refresh):
        ap.error('--no-pr conflicts with an explicit hosted refresh')
    return guarded("gh-stack-chain-check", lambda: run_check(args), json_errors=args.json or args.compact_json)


def run_check(args: argparse.Namespace) -> int:
    preflight(need_gh=False)
    remote = getattr(args, 'remote', 'origin')
    if not valid_branch(args.trunk) or not valid_branch(remote):
        raise ToolError('invalid trunk or remote name', 'INPUT.INVALID_REF')
    if any((not value.isdigit() and not valid_branch(value)) or (value.isdigit() and int(value) <= 0) for value in args.layers):
        raise ToolError('layers must be valid branch names or positive PR numbers', 'INPUT.INVALID_LAYER')
    snapshot = read_local_snapshot(remote, run_fn=run)
    stacks = [stack for stack in snapshot['stacks'] if _selected(stack, getattr(args, 'stack', None))]
    if getattr(args, 'stack', None) and not stacks:
        raise ToolError('no local stack matches the requested scope', 'STATE.STACK_UNKNOWN')
    client = StackDataClient(snapshot['repository'], run_fn=run)
    git_only = getattr(args, 'refresh_git', False) and not (getattr(args, 'refresh_status', False) or getattr(args, 'refresh', False))
    status_only = getattr(args, 'refresh_status', False) and not (getattr(args, 'refresh_git', False) or getattr(args, 'refresh', False))
    offline = args.no_pr or git_only
    force = getattr(args, 'refresh_status', False) or getattr(args, 'refresh', False)
    catalog = {}
    for stack in stacks:
        for branch in stack['branches']:
            number = (branch.get('pr') or {}).get('number')
            if number:
                existing = catalog.get(number)
                if existing and existing['headRefName'] != branch['name']:
                    raise ToolError('conflicting local PR branch mappings', 'STATE.CATALOG_CONFLICT')
                catalog[number] = {'number': number, 'headRefName': branch['name']}
    requested_numbers = sorted({int(value) for value in args.layers if value.isdigit()})
    # Resolve numeric identifiers in one request sequence, never one call per PR.
    missing_numbers = [number for number in requested_numbers if number not in catalog]
    cached_mapping = client.pr_metadata(missing_numbers, offline=offline, force=force) if missing_numbers else {}
    catalog.update(cached_mapping)
    by_number, by_branch = index_prs(list(catalog.values()))
    layers = resolve_layers(args.layers, by_number, by_branch, offline=True)
    if any(not valid_branch(branch) for branch in layers):
        raise ToolError('invalid layer branch name', 'INPUT.INVALID_REF')
    catalog_scope = [stack for stack in stacks if any(branch['name'] in layers for branch in stack['branches'])]
    catalog_scope.append({'trunk': args.trunk, 'branches': [{'name': branch} for branch in layers]})
    git_observation = client.refresh_git(force=getattr(args, 'refresh_git', False) or getattr(args, 'refresh', False),
                                         offline=args.no_fetch or status_only, refs=[args.trunk, *layers])
    if git_observation['source'] == 'fetched':
        refreshed = read_local_snapshot(remote, run_fn=run)
        # A catalog change while numeric identifiers were being resolved needs
        # a new report; do not silently pin the old mapping to the new catalog.
        if _catalog_composition(refreshed, catalog_scope) != _catalog_composition(snapshot, catalog_scope):
            raise ToolError('catalog changed during layer resolution; retry local status', 'STATE.SNAPSHOT_CHANGED')
        snapshot = refreshed
    refs = snapshot['refs']
    stack = {'trunk': args.trunk, 'branches': [{'name': branch, 'isMerged': False} for branch in layers]}
    conflicts = evaluate_stack_conflicts(stack, refs, remote, run_fn=run)
    known = {branch: by_branch[branch] for branch in layers if branch in by_branch}
    unresolved = [branch for branch in layers if branch not in known]
    if unresolved:
        known.update(client.resolve_branches(unresolved, offline=offline, force=force))
    numbers = sorted({pr['number'] for pr in known.values()})
    heads = {pr['number']: refs.get(f'refs/remotes/{remote}/{branch}') for branch, pr in known.items()}
    head_map = {number: sha for number, sha in heads.items() if sha}
    already_refreshed = set(cached_mapping) | {known[branch]['number'] for branch in unresolved if branch in known}
    remaining = [number for number in numbers if number not in already_refreshed]
    reused = [number for number in numbers if number in already_refreshed]
    details = client.pr_metadata(reused, offline=offline, head_map=head_map) if reused else {}
    if remaining:
        details.update(client.pr_metadata(remaining, force=force, offline=offline, head_map=head_map))
    for branch, pr in list(known.items()):
        known[branch] = details.get(pr['number'], pr)
    report = evaluate(args.trunk, layers, known,
                      fetched=True if git_observation.get('refs') is not None else bool(refs.get(f'refs/remotes/{remote}/{args.trunk}')),
                      use_pr=True, refs=refs, remote=remote, conflicts=conflicts, ref_observations=git_observation.get('refs'),
                      pr_observations=client.observations)
    unknown_count = 0
    local = {entry['branch']: entry for entry in conflicts['layers']}
    for row in report['rows']:
        entry = local[row['branch']]
        row['local_merge_clean'], row['local_merge_reason'] = entry['clean'], entry['reason']
        row['provenance'] = client.observations.get((known.get(row['branch']) or {}).get('number'), {})
        branch_observation = getattr(client, 'branch_observations', {}).get(row['branch'], {})
        row['branch_observation'] = branch_observation
        absent = not row['pr'] and branch_observation.get('freshness') == 'fresh' and branch_observation.get('exists') is False
        stale = not absent and (not row['provenance'] or any(value.get('freshness') != 'fresh' for value in row['provenance'].values()))
        row['hosted_stale'] = stale
        if stale:
            row['pr_base_ok'] = row['pr_head_ok'] = None
        if entry['clean'] is False:
            report['problems'].append(f"L{row['layer']} {row['branch']}: local content conflict against intended parent")
        row_fresh = _git_scope_fresh(git_observation, [args.trunk, row['branch'], row.get('expected_base', args.trunk)])
        if not _git_scope_fresh(git_observation, [row['branch']]):
            row['pushed'] = None
        row['unknown'] = entry['clean'] is None or stale or not row_fresh
        if row['unknown']:
            unknown_count += 1
    discovery_incomplete = [warning for warning in scope_diagnostics(snapshot, stacks=catalog_scope, branches=layers)
                            if not warning.startswith('No local gh-stack catalog')]
    if conflicts['clean'] is None or unknown_count or discovery_incomplete:
        report['linkable'] = None if not report['problems'] else False
    elif report['problems']:
        report['linkable'] = False
    report['local_mergeability'] = conflicts
    final_snapshot = read_local_snapshot(remote, run_fn=run)
    if _scope_epoch(final_snapshot, catalog_scope, remote=remote, branches=[args.trunk, *layers]) != _scope_epoch(snapshot, catalog_scope, remote=remote, branches=[args.trunk, *layers]):
        raise ToolError('Snapshot changed during evaluation; retry the scoped chain check', 'STATE.SNAPSHOT_CHANGED')
    report.update(schema_version=1, success=True, git_observation=git_observation, observations=client.observations,
                  catalogs=snapshot.get('catalogs', []),
                  metrics=client.metrics, warnings=list(dict.fromkeys(snapshot['warnings'] + client.warnings)), unknown_count=unknown_count,
                  snapshot_id=hashlib.sha256((snapshot['fingerprint'] + str(client.snapshot_id)).encode()).hexdigest()[:24])
    report['link_command'] = link_command(report) if report['linkable'] is True else None
    if args.json or getattr(args, 'compact_json', False):
        print(json.dumps(compact_report(report) if getattr(args, 'compact_json', False) else report, indent=2))
    else:
        print(render(report, full=getattr(args, 'full', False)))
    return 0 if report["linkable"] is True else 1


if __name__ == "__main__":
    sys.exit(main())
