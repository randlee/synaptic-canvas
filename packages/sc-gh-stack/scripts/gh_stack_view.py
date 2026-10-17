#!/usr/bin/env python3
"""Local-first stack coherence, content-conflict and cached GitHub status report."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_stack_shared import ToolError, guarded, is_ancestor, origin_sha, run, short, ReportArgumentParser, compact_report
from gh_stack_local import read_local_snapshot, evaluate_stack_conflicts, scope_diagnostics, _branch as valid_branch
from gh_stack_remote import StackDataClient, _read as read_snapshot, _write as write_snapshot

SKIPPED: list[str] = []


def stack_json_at(path: str) -> dict | None:
    """Compatibility reader: inspect catalogs locally, never run gh stack view."""
    def local_run(cmd, **kwargs):
        kwargs.setdefault("cwd", path)
        if kwargs["cwd"] is None:
            kwargs["cwd"] = path
        return run(cmd, **kwargs)
    try:
        snapshot = read_local_snapshot(run_fn=local_run)
        branch = local_run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], check=False).stdout.strip()
        matches = [s for s in snapshot["stacks"] if any(b["name"] == branch for b in s["branches"])]
        SKIPPED.extend(snapshot["warnings"])
        return matches[0] if len(matches) == 1 else None
    except ToolError as exc:
        SKIPPED.append(f"{path}: {exc}")
        return None


def select_stacks(found: list[dict], trunk_filter: str | None, *, include_all: bool) -> tuple[list[dict], int]:
    """Filter the deduped stack list down to what should be shown.

    Rules:

    * ``trunk_filter`` set - keep only stacks with that trunk (open-only
      unless ``include_all``).
    * no filter and ``include_all`` - keep everything.
    * no filter, not ``include_all`` (the default) - keep every stack that
      still has an open layer, regardless of trunk name.

    Returns (stacks, hidden_count).
    """
    def is_open(d: dict) -> bool:
        return any(not b.get("isMerged") and (b.get("pr") or {}).get("state", "OPEN") != "CLOSED"
                   for b in d["branches"])

    if trunk_filter:
        stacks = [d for d in found if d["trunk"] == trunk_filter and (include_all or is_open(d))]
    elif include_all:
        stacks = found
    else:
        stacks = [d for d in found if is_open(d)]
    stacks.sort(key=lambda d: (not d["trunk"].startswith("integrate/"), d["trunk"], d["branches"][0]["name"]))
    return stacks, len(found) - len(stacks)



def discover_stacks(trunk_filter: str | None, *, include_all: bool, snapshot=None) -> tuple[list[dict], int]:
    """Read each common/legacy catalog once, then filter before remote reads."""
    snapshot = snapshot if snapshot is not None else read_local_snapshot(run_fn=run)
    SKIPPED.extend(w for w in snapshot["warnings"] if w not in SKIPPED)
    return select_stacks(snapshot["stacks"], trunk_filter, include_all=include_all)


def pr_details(numbers: list[int], *, client=None, force=False, offline=False, head_map=None) -> dict[int, dict]:
    """Required hosted fields only, scoped/reused/batched by the shared adapter."""
    if any(type(n) is not int or n <= 0 for n in numbers):
        raise ToolError("PR numbers must be positive integers")
    if not numbers:
        return {}
    if client is None:
        client = StackDataClient(read_local_snapshot(run_fn=run)["repository"], run_fn=run)
    return client.pr_details(numbers, force=force, offline=offline, head_map=head_map)


def landing_verdict(stack: dict, rows: list[dict], trunk_origin: str | None) -> dict:
    """Judge the stack as one landing, independent of chain coherence.

    The chain verdict answers "can gh stack merge walk this bottom-up?".  A
    stack is also landable as a single merge of its top layer when (a) the
    top layer's pushed head contains every open layer's pushed head and (b)
    that head merges into the trunk without conflicts.  Both are checked
    against origin refs only, never local tracking.
    """
    open_rows = [r for r in rows if not r.get("merged")]
    if not open_rows or trunk_origin is None:
        return {"landable": None, "top": None, "reason": "no open layer or trunk not fetched"}
    top = open_rows[-1]
    top_sha = top.get("origin")
    if not top_sha:
        return {"landable": None, "top": top["branch"], "reason": "top layer has no origin head"}
    missing = [r["branch"] for r in open_rows[:-1] if not r.get("origin") or not is_ancestor(r["origin"], top_sha)]
    if missing:
        return {"landable": False, "top": top["branch"], "top_sha": top_sha,
                "reason": "top head does not contain: " + ", ".join(missing)}
    tree = run(["git", "merge-tree", "--write-tree", trunk_origin, top_sha], check=False)
    if tree.returncode == 1:
        conflicts = [line for line in tree.stdout.splitlines() if line.startswith("CONFLICT")]
        return {"landable": False, "top": top["branch"], "top_sha": top_sha,
                "reason": "merge into trunk conflicts: " + ("; ".join(conflicts[:3]) or "see git merge-tree")}
    if tree.returncode != 0:
        return {"landable": None, "top": top["branch"], "top_sha": top_sha,
                "reason": "git merge-tree --write-tree unavailable (git < 2.38) or failed; check with a scratch `git merge --no-commit`"}
    return {"landable": True, "top": top["branch"], "top_sha": top_sha,
            "reason": f"top head contains all {len(open_rows)} open layer(s) and merges clean into {stack['trunk']}"}


def build_rows(stack: dict, prs: dict[int, dict], *, fetched: bool, refs=None, remote="origin", ref_observations=None, pr_observations=None) -> tuple[list[dict], list[str], list[str]]:
    trunk = stack["trunk"]
    resolve = (lambda name: refs.get(f"refs/remotes/{remote}/{name}")) if refs is not None else origin_sha
    fresh = lambda name: fetched and (ref_observations is None or ref_observations.get(name, {}).get('fresh') is True)
    trunk_origin = resolve(trunk) if fresh(trunk) else None
    rows: list[dict] = []
    problems: list[str] = []
    notes: list[str] = []
    expected_base = trunk_origin
    # Name of the branch the next open layer must be based on.  Starts at the
    # trunk and only advances past OPEN layers: a merged layer's content now
    # lives in the trunk (GitHub retargets its child onto the trunk), so the
    # layer above a merged one is judged against the trunk, not the merged head.
    parent = trunk
    for idx, br in enumerate(stack["branches"], start=1):
        name = br["name"]
        pr = prs.get((br.get("pr") or {}).get("number") or -1, {})
        number = (br.get('pr') or {}).get('number')
        trusted = lambda field: pr_observations is None or pr_observations.get(number, {}).get(field, {}).get('freshness') == 'fresh'
        if br.get("isMerged"):
            rows.append({"layer": idx, "branch": name, "pr": (br.get("pr") or {}).get("number"),
                         "head": br.get("head"), "base": br.get("base"), "merged": True, "queued": False,
                         "draft": False, "mergeable": None, "merge_state": "MERGED", "ci": pr.get("ci"),
                         "base_ok": None, "origin_ok": None, "needs_rebase": False, "origin": None,
                         "pr_head": pr.get("headRefOid"), "expected_base": expected_base, "pr_base": pr.get("baseRefName")})
            # Merged: its head is (an ancestor of) the trunk head now.  The next
            # open layer must sit on the trunk; ``parent`` stays at the trunk.
            expected_base = trunk_origin if ref_observations is not None else trunk_origin or br.get("head") or expected_base
            parent = trunk
            continue
        # gh stack omits ``head``/``base`` for a layer that has no local branch
        # (e.g. viewed from a sibling worktree before the branch was fetched).
        # Never subscript them directly: a missing key must degrade to ❓, not crash.
        head = br.get("head")
        base = br.get("base")
        origin = resolve(name) if fresh(name) else None
        if (br.get("pr") or {}).get("number") is not None and prs and not pr:
            notes.append(f"L{idx} {name}: PR #{(br.get('pr') or {}).get('number')} could not be resolved on GitHub (deleted, or no access); merge and CI shown as unknown")
        base_ok = (base == expected_base) if (expected_base and base and (ref_observations is None or fresh(name))) else None
        origin_ok = None
        if origin:
            if head:
                origin_ok = (False if head != origin else None if pr and not trusted('headRefOid')
                             else not pr or pr.get("headRefOid") == origin)
            elif pr:
                # No local head to compare; the remote side (origin vs PR) can still be checked.
                origin_ok = pr.get("headRefOid") == origin if trusted('headRefOid') else None
        if head is None:
            notes.append(f"L{idx} {name}: gh stack reported no local head (branch not present locally); local tracking not verified")
        if base is None:
            notes.append(f"L{idx} {name}: gh stack reported no base SHA; base coherence not verified")
        row = {
            "layer": idx,
            "branch": name,
            "pr": (br.get("pr") or {}).get("number"),
            "head": head,
            "origin": origin,
            "pr_head": pr.get("headRefOid"),
            "base": base,
            "expected_base": expected_base,
            "base_ok": base_ok,
            "origin_ok": origin_ok,
            "needs_rebase": br.get("needsRebase"),
            "merged": br.get("isMerged"),
            "queued": br.get("isQueued"),
            "draft": pr.get("isDraft"),
            "mergeable": pr.get("mergeable"),
            "merge_state": pr.get("mergeStateStatus"),
            "ci": pr.get("ci"),
            "pr_base": pr.get("baseRefName"),
            "behind_trunk": False,
            "pr_unresolved": bool((br.get("pr") or {}).get("number") is not None and prs and not pr),
        }
        conflict_head = origin if ref_observations is not None else origin or head
        if refs is not None and expected_base and conflict_head:
            row["needs_rebase"] = not is_ancestor(expected_base, conflict_head)
            br["needsRebase"] = row["needs_rebase"]
        parent_is_trunk = parent == trunk
        if pr and trusted('baseRefName') and pr.get("baseRefName") not in (None, parent):
            problems.append(f"L{idx} {name}: PR #{row['pr']} base is {pr['baseRefName']}, expected {parent}")
        if base_ok is False:
            # The lowest OPEN layer (idx 1, or any layer whose lower layers are
            # all merged) may sit on an older trunk commit: that is a note, not
            # a rebase order.  Against an open parent it is a real mismatch.
            if parent_is_trunk and is_ancestor(base or "", expected_base):
                row["behind_trunk"] = True
                notes.append(f"L{idx} {name}: behind trunk ({short(base)} < {short(expected_base)}); fine unless CONFLICTING, do not restart CI just to catch up")
            else:
                problems.append(f"L{idx} {name}: base {short(base)} != parent head {short(expected_base)} -> needs rebase")
        if origin_ok is False:
            problems.append(
                f"L{idx} {name}: local {short(head)} / origin {short(origin)} / PR {short(pr.get('headRefOid'))} differ"
                " -> local tracking stale or unpushed; owner must fetch+reset or push"
            )
        if br.get("needsRebase"):
            if row["behind_trunk"]:
                notes.append(f"L{idx} {name}: gh stack reports needsRebase, but only against a trunk that moved; no action while its CI can go green")
            else:
                problems.append(f"L{idx} {name}: gh stack reports needsRebase")
        if trusted('mergeable') and pr.get("mergeable") == "CONFLICTING":
            problems.append(f"L{idx} {name}: PR #{row['pr']} CONFLICTING")
        if trusted('isDraft') and pr.get("isDraft"):
            problems.append(f"L{idx} {name}: PR #{row['pr']} is DRAFT (blocks stack merge)")
        if trusted('state') and pr.get("state") == "CLOSED":
            problems.append(f"L{idx} {name}: PR #{row['pr']} is CLOSED")
        rows.append(row)
        # The next layer must be based on THIS layer's pushed head (fall back to local, then PR).
        expected_base = origin if ref_observations is not None else origin or head or pr.get("headRefOid") or expected_base
        parent = name
    return rows, problems, notes


ICON_SYNC = {"ok": "✅", "stale": "🔄", "rebase": "⚠️", "behind": "⏳", "unknown": "❓"}
ICON_MERGE = {"MERGED": "\U0001f3c1", "OK": "✅", "BLOCKED": "\U0001f6a7"}
ICON_CI = {"SUCCESS": "✅", "FAILURE": "⛔", "ERROR": "⛔", "PENDING": "\U0001f300",
           "EXPECTED": "\U0001f300", "NONE": "—"}


def sync_icon(r: dict) -> str:
    if r["merged"]:
        return ICON_MERGE["MERGED"]
    if r["origin_ok"] is False:
        return ICON_SYNC["stale"]
    if r.get("behind_trunk"):
        return ICON_SYNC["behind"]
    if r.get("pr_unresolved"):
        return ICON_SYNC["unknown"]
    if r.get("hosted_stale") and r.get("pr"):
        return ICON_SYNC["unknown"]
    if r["base_ok"] is False or r["needs_rebase"]:
        return ICON_SYNC["rebase"]
    if r["base_ok"] is None or r["origin_ok"] is None:
        return ICON_SYNC["unknown"]
    return ICON_SYNC["ok"]


def merge_icon(r: dict) -> str:
    """✅ only when GitHub says the PR can merge now; anything else is 🚧."""
    if r["merged"]:
        return ICON_MERGE["MERGED"]
    if r.get("pr_unresolved"):
        return ICON_SYNC["unknown"]
    if r.get("mergeable") in (None, "UNKNOWN") or r.get("merge_state") in (None, "UNKNOWN"):
        return ICON_SYNC["unknown"]
    if r.get("hosted_stale"):
        return ICON_SYNC["unknown"]
    if r["draft"] or r["queued"] or r["mergeable"] != "MERGEABLE":
        return ICON_MERGE["BLOCKED"]
    return ICON_MERGE["OK"] if r["merge_state"] in ("CLEAN", "HAS_HOOKS", "UNSTABLE") else ICON_MERGE["BLOCKED"]


def ci_icon(r: dict) -> str:
    if r.get("pr_unresolved") or r.get("hosted_stale"):
        return ICON_SYNC["unknown"]
    return ICON_CI.get(r["ci"] or "NONE", ICON_CI["NONE"])


def render_landing(landing: dict) -> str:
    if landing["landable"] is None:
        return f"LANDING: ❓ not judged - {landing['reason']}"
    if landing["landable"]:
        return f"LANDING: ✅ top/trunk content prediction for {landing['top']} @ {short(landing['top_sha'])}; not whole-stack eligibility; hosted policy is separate - {landing['reason']}"
    return f"LANDING: ❌ {landing['top']} @ {short(landing.get('top_sha'))} cannot land as one merge - {landing['reason']}"


def render_table(stack: dict, rows: list[dict], problems: list[str], notes: list[str], landing: dict, *, trunk_origin: str | None, full=False, coherent=None) -> str:
    hdr = ["L", "PR", "rebase", "local conflict", "GitHub", "CI"]
    lines = [f"stack: {stack['branches'][-1]['name']} -> {stack['trunk']} @ {short(trunk_origin)}", ""]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "|".join("---" for _ in hdr) + "|")
    def hosted_blocked(row):
        return not row.get("merged") and (merge_icon(row) == ICON_MERGE["BLOCKED"] or ci_icon(row) == "⛔")
    visible = rows if full else sorted(rows, key=lambda r: (
        not (r.get("local_merge_clean") is False or r.get("needs_rebase") or r.get("origin_ok") is False or hosted_blocked(r)),
        not ((not r.get("merged") and r.get("local_merge_clean") is None) or r.get("pr_unresolved") or r.get("hosted_stale")),
        not r.get("changed"), r["layer"]))[:10]
    for r in visible:
        pr = f"#{r['pr']}" if r["pr"] else "-"
        lines.append("| " + " | ".join([
            f"{r['layer']}/{len(rows)}", pr, sync_icon(r),
            {True: "clean", False: "CONFLICT", None: "unknown"}[r.get("local_merge_clean")],
            merge_icon(r), ci_icon(r),
        ]) + " |")
    lines.append("")
    if problems:
        lines.append(f"VERDICT: ❌ NOT COHERENT ({len(problems)} issue(s))")
        lines.extend(f"- {p}" for p in (problems if full else problems[:10]))
    elif coherent is True:
        lines.append("VERDICT: ✅ COHERENT - observed local/fetched chain; hosted eligibility is separate")
    else:
        lines.append("VERDICT: ❓ coherence unknown - incomplete or stale observations; hosted eligibility is separate")
    unknown = sum(r.get("local_merge_clean") is None for r in rows if not r.get("merged"))
    conflicts = sum(r.get("local_merge_clean") is False for r in rows)
    hosted_unknown = sum(bool(r.get("hosted_stale") or r.get("pr_unresolved") or r.get("mergeable") in (None, "UNKNOWN")) for r in rows if not r.get("merged"))
    blocked = sum(hosted_blocked(r) for r in rows)
    lines.append(f"scope: {len(rows)} layers; {conflicts} local conflicts; {unknown} local unknowns; {blocked} hosted/check blockers; {hosted_unknown} hosted unknown/stale; showing {len(visible)} rows")
    if len(visible) < len(rows) or (not full and len(problems) > 10):
        lines.append("output truncated; --full or --json returns all layers and issues")
    lines.append(render_landing(landing))
    lines.extend(f"- note: {n}" for n in (notes if full else notes[:3]))
    if not full and len(notes) > 3:
        lines.append(f"notes: {len(notes)} total; --full to show all")
    return "\n".join(lines)


def legend() -> str:
    lines = []
    lines.append("rebase: ✅ not needed (base==parent head, local==origin==PR)  ⚠️ needed  ⏳ behind a moved trunk, no action  🔄 local tracking stale: fetch+reset before any sync  ❓ unknown (--no-fetch, or PR unresolved)  🏁 merged")
    lines.append("GitHub: ✅ observed mergeable (not an authorization or policy guarantee)  🚧 blocked  ❓ stale/unknown  🏁 merged; local conflict is separate")
    lines.append("CI: ✅ green  🌀 running  ⛔ failed, do not enter  — none")
    return "\n".join(lines)


def add_refresh_options(ap, *, include_structure=False):
    ap.add_argument("--remote", default="origin", help="selected git remote")
    ap.add_argument("--stack", help="stack number, ID, or one of its branch names")
    ap.add_argument("--full", action="store_true", help="show every layer/issue; does not refresh")
    ap.add_argument("--compact-json", action="store_true", help="bounded JSON presentation (ten rows/stacks); not complete composition evidence; does not refresh")
    ap.add_argument("--refresh-git", action="store_true", help="refresh git refs once; no API requests unless combined with --refresh-status")
    ap.add_argument("--refresh-status", action="store_true", help="refresh required hosted fields without implying a git fetch")
    refresh_help = ("refresh selected stack membership, git refs and required hosted fields" if include_structure else
                    "refresh git refs and required hosted fields")
    ap.add_argument("--refresh", action="store_true", help=refresh_help)


def main() -> int:
    ap = ReportArgumentParser(description=__doc__)
    ap.add_argument("--trunk", help="only stacks with this trunk")
    ap.add_argument("--phase", help="shorthand for --trunk integrate/phase-<PHASE>")
    ap.add_argument("--all", action="store_true", help="include merged/closed stacks")
    ap.add_argument("--no-fetch", action="store_true", help="forbid fetching; reuse qualified cached refs")
    ap.add_argument("--no-pr", action="store_true", help="strictly no GitHub API calls; cached data is qualified")
    ap.add_argument("--json", action="store_true", help="complete structured snapshot")
    add_refresh_options(ap, include_structure=True)
    args = ap.parse_args()
    if args.compact_json and (args.json or args.full):
        ap.error("--compact-json conflicts with --json and --full")
    if args.no_fetch and (args.refresh_git or args.refresh):
        ap.error("--no-fetch conflicts with an explicit git refresh")
    if args.no_pr and (args.refresh_status or args.refresh):
        ap.error("--no-pr conflicts with an explicit hosted refresh")
    trunk_filter = args.trunk or (f"integrate/phase-{args.phase.lower()}" if args.phase else None)
    return guarded("gh-stack-view", lambda: run_report(args, trunk_filter), json_errors=args.json or args.compact_json)


def preflight() -> None:
    if not shutil.which("git"):
        raise ToolError("`git` not on PATH")
    if run(["git", "rev-parse", "--git-dir"], check=False).returncode != 0:
        raise ToolError("not inside a git repository")


def _selected(stack, selector):
    return not selector or str(stack.get("number", "")) == selector or stack.get("id") == selector or any(
        b["name"] == selector for b in stack["branches"])


def _remote_shape(data, refs, *, expected_number=None, local_stack=None):
    """Normalize native stacks REST data without importing/migrating its catalog."""
    if not isinstance(data, dict):
        return None
    number = data.get("number")
    if type(number) is not int or number <= 0 or (expected_number is not None and number != expected_number):
        return None
    base = data.get("base")
    trunk = (base.get("ref") if isinstance(base, dict) else None) or data.get("trunk")
    prs = data.get("pull_requests")
    if not valid_branch(trunk) or not isinstance(prs, list) or not prs:
        return None
    local = {(branch["name"], (branch.get("pr") or {}).get("number")): branch
             for branch in (local_stack or {}).get("branches", [])}
    branches = []
    names, numbers = {trunk}, set()
    for pr in prs:
        if not isinstance(pr, dict) or not isinstance(pr.get("head"), dict):
            return None
        head = pr["head"]
        name = head.get("ref")
        if (not valid_branch(name) or name in names or type(pr.get("number")) is not int
                or pr["number"] <= 0 or pr["number"] in numbers
                or not isinstance(pr.get("state", "UNKNOWN"), str)
                or pr.get("state", "UNKNOWN").upper() not in ("OPEN", "CLOSED", "MERGED", "UNKNOWN")
                or ("merged" in pr and type(pr["merged"]) is not bool)
                or (pr.get("merged_at") is not None and not isinstance(pr["merged_at"], str))):
            return None
        names.add(name)
        numbers.add(pr["number"])
        recorded = local.get((name, pr["number"]), {})
        merged = pr.get("state", "").upper() == "MERGED" or bool(pr.get("merged") or pr.get("merged_at"))
        branches.append({"name": name, "head": refs.get("refs/heads/" + name),
                         "recorded_head": recorded.get("recorded_head"), "base": recorded.get("base"),
                         "base_source": "local_catalog" if recorded.get("base") is not None else None,
                         "isMerged": merged, "isQueued": None, "needsRebase": None,
                         "pr": {"number": pr["number"], "state": "MERGED" if merged else str(pr.get("state", "UNKNOWN")).upper()}})
    return {"trunk": trunk, "branches": branches, "number": number,
            "id": data.get("id"), "worktree": (local_stack or {}).get("worktree"), "source": "REST"}


def _catalog_composition(snapshot, scope=None):
    """Exclude fetched refs, but retain all catalog identities and recorded state."""
    selected = snapshot["stacks"]
    if scope is not None:
        names = {branch['name'] for stack in scope for branch in stack['branches']}
        ids = {stack['id'] for stack in scope if stack.get('id') is not None}
        numbers = {stack['number'] for stack in scope if stack.get('number') is not None}
        selected = [stack for stack in selected if stack.get('id') in ids or stack.get('number') in numbers
                    or any(branch['name'] in names for branch in stack['branches'])]
    return ([{"source_path": entry.get("source_path"), "digest": entry.get("digest")}
             for entry in snapshot.get("catalogs", [])] if scope is None else [warning for warning in scope_diagnostics(snapshot, stacks=scope)
                                                                            if not warning.startswith('No local gh-stack catalog')],
            [{"trunk": stack["trunk"], "id": stack.get("id"), "number": stack.get("number"),
              "branches": [{key: branch.get(key) for key in ("name", "recorded_head", "base", "pr", "isMerged")}
                           for branch in stack["branches"]]}
             for stack in selected])


def _scope_epoch(snapshot, scope, *, remote='origin', branches=None):
    """Unrelated worktrees/refs must not invalidate a qualified explicit scope."""
    names = set(branches or []) | {stack['trunk'] for stack in scope} | {
        branch['name'] for stack in scope for branch in stack['branches']}
    refs = {prefix + name: snapshot['refs'].get(prefix + name) for name in sorted(names)
            for prefix in ('refs/heads/', f'refs/remotes/{remote}/')}
    return (_catalog_composition(snapshot, scope), refs,
            [warning for warning in scope_diagnostics(snapshot, stacks=scope, branches=names)
             if not warning.startswith('No local gh-stack catalog')],
            {key: snapshot['repository'].get(key) for key in ('identity', 'common_dir', 'remote')})


def _git_scope_fresh(observation, names):
    """A missing retired branch must not poison surviving independent refs."""
    entries = observation.get('refs')
    if entries is None:
        return observation['fresh']
    return all(entries.get(name, {}).get('fresh') is True for name in names)


def _refresh_structure(client, number, refs, *, force, local_stack=None, require_fresh=False):
    data = client.refresh_stack(number, force=force)
    structural = _remote_shape(data, refs, expected_number=number, local_stack=local_stack)
    observation = dict(getattr(client, "stack_observations", {}).get(number, {}))
    if require_fresh and (structural is None or observation.get("freshness") != "fresh" or observation.get("complete") is not True):
        raise ToolError(f"Stack #{number} membership refresh failed or is incomplete; retry the scoped --refresh before using its composition",
                        "STATE.STACK_STRUCTURE_UNKNOWN", {"stack": number, "structure_observation": observation})
    if structural is not None:
        structural["structure_observation"] = observation or {
            "source": "REST", "freshness": "unknown", "complete": False, "observed_at": None}
    return structural


def run_report(args: argparse.Namespace, trunk_filter: str | None) -> int:
    preflight()
    SKIPPED.clear()
    remote = getattr(args, "remote", "origin")
    snapshot = read_local_snapshot(remote, run_fn=run)
    stacks, hidden = discover_stacks(trunk_filter, include_all=args.all, snapshot=snapshot)
    selector = getattr(args, "stack", None)
    # Lifecycle enrichment must not mutate the catalog epoch we later verify.
    stacks = copy.deepcopy([s for s in stacks if _selected(s, selector)])
    # A trunk filter still requests discovery of every stack on that trunk;
    # only an exact stack selector establishes independent fixed membership.
    catalog_scope = list(stacks) if selector else None
    repository = snapshot["repository"]
    client = StackDataClient(repository, run_fn=run)
    git_only = getattr(args, "refresh_git", False) and not getattr(args, "refresh_status", False) and not getattr(args, "refresh", False)
    offline = args.no_pr or git_only
    force_status = getattr(args, "refresh_status", False) or getattr(args, "refresh", False)
    refresh_structure = getattr(args, "refresh", False)
    if not stacks and selector and selector.isdigit() and not offline:
        structural = _refresh_structure(client, int(selector), snapshot["refs"], force=force_status,
                                        require_fresh=refresh_structure)
        if structural and (not trunk_filter or structural["trunk"] == trunk_filter):
            stacks = [structural]
            SKIPPED[:] = [w for w in SKIPPED if not w.startswith("No local gh-stack catalog")]
    if not stacks:
        raise ToolError("no locally tracked stack matches; inspect local catalog diagnostics or request --stack NUMBER for scoped remote discovery"
                        + ("; " + "; ".join(SKIPPED) if SKIPPED else ""), "STATE.STACK_UNKNOWN",
                        {"catalogs": snapshot.get("catalogs", []), "warnings": SKIPPED})
    if refresh_structure:
        refreshed_stacks = []
        for stack in stacks:
            if stack.get("source") == "REST":
                refreshed_stacks.append(stack)
                continue
            number = stack.get("number")
            if type(number) is not int or number <= 0:
                raise ToolError("A numeric stack number is required to refresh membership; use --stack NUMBER for scoped remote discovery",
                                "STATE.STACK_NUMBER_UNKNOWN")
            structural = _refresh_structure(client, number, snapshot["refs"], force=True,
                                            local_stack=stack, require_fresh=True)
            if trunk_filter and structural["trunk"] != trunk_filter:
                raise ToolError(f"Stack #{number} now targets {structural['trunk']!r}, outside requested trunk {trunk_filter!r}; inspect its new scope",
                                "STATE.SNAPSHOT_CHANGED")
            refreshed_stacks.append(structural)
        stacks = refreshed_stacks
    else:
        for stack in stacks:
            stack.setdefault("structure_observation", {"source": "local_catalog", "freshness": "unknown",
                                                       "complete": False, "observed_at": None})
    epoch_scope = [*catalog_scope, *stacks] if catalog_scope is not None else None
    status_only = getattr(args, "refresh_status", False) and not getattr(args, "refresh_git", False) and not getattr(args, "refresh", False)
    git_observation = client.refresh_git(
        force=getattr(args, "refresh_git", False) or getattr(args, "refresh", False),
        offline=args.no_fetch or status_only,
        refs=sorted({st["trunk"] for st in stacks} | {b["name"] for st in stacks for b in st["branches"] if not b.get("isMerged")}))
    if git_observation["source"] == "fetched":
        refreshed = read_local_snapshot(remote, run_fn=run)
        if _catalog_composition(refreshed, epoch_scope) != _catalog_composition(snapshot, epoch_scope):
            raise ToolError("Local catalog composition changed while refreshing refs; retry the scoped report",
                            "STATE.SNAPSHOT_CHANGED")
        snapshot = refreshed
        # Membership may deliberately come from REST. Only refresh local heads;
        # never replace that ordered composition with the historical catalog.
        for stack in stacks:
            for branch in stack["branches"]:
                branch["head"] = snapshot["refs"].get("refs/heads/" + branch["name"])
    refs = snapshot["refs"]
    # Derive the local facts first. Hosted lifecycle can subsequently retire a
    # layer; only that changed parent sequence requires another local pass.
    local_conflicts = [evaluate_stack_conflicts(st, refs, remote, run_fn=run) for st in stacks]
    merged_shapes = [tuple(bool(b.get("isMerged")) for b in st["branches"]) for st in stacks]
    unmapped = [b["name"] for st in stacks for b in st["branches"] if not b.get("pr") and not b.get("isMerged")]
    mappings = client.resolve_branches(unmapped, offline=offline, force=force_status) if unmapped else {}
    for st in stacks:
        for branch in st["branches"]:
            mapped = mappings.get(branch["name"])
            if not branch.get("pr") and mapped:
                branch["pr"] = {"number": mapped["number"], "state": mapped.get("state", "UNKNOWN")}
    numbers = sorted({b["pr"]["number"] for st in stacks for b in st["branches"] if b.get("pr") and not b.get("isMerged")})
    head_map = {b["pr"]["number"]: refs.get(f"refs/remotes/{remote}/{b['name']}")
                for st in stacks for b in st["branches"] if b.get("pr") and not b.get("isMerged")}
    head_map = {n: sha for n, sha in head_map.items() if sha}
    prs = pr_details(numbers, client=client, force=force_status, offline=offline, head_map=head_map)
    prs = {n: prs.get(n, {}) for n in numbers}
    report = []
    any_problem = False
    scope = hashlib.sha256(json.dumps([selector, trunk_filter, args.all], sort_keys=True).encode()).hexdigest()[:16]
    previous_path = client.cache_dir / (client.path.stem + "-view-" + scope + ".json")
    previous = read_snapshot(previous_path)
    previous_rows = {(s["trunk"], r["branch"]): r for s in previous.get("stacks", []) for r in s.get("rows", [])}
    for stack_index, st in enumerate(stacks):
        effective_prs = dict(prs)
        effective_observations = copy.deepcopy(client.observations)
        for b in st["branches"]:
            number = (b.get("pr") or {}).get("number")
            detail = prs.get(number, {})
            lifecycle = client.observations.get(number, {}).get("state", {})
            fresh_state = lifecycle.get("freshness") == "fresh"
            if st.get("source") == "REST" and not fresh_state:
                # A failed forced detail refresh may return an old cached state.
                # It must not retire or reactivate a layer from fresh REST scope.
                b["lifecycle_observation"] = dict(st["structure_observation"])
                effective_observations.setdefault(number, {})['state'] = dict(b['lifecycle_observation'])
                if detail and b.get("pr"):
                    detail = dict(detail, state=b["pr"]["state"])
                    effective_prs[number] = detail
                continue
            if fresh_state:
                b["lifecycle_observation"] = dict(lifecycle)
            if fresh_state and detail.get("state") == "MERGED":
                b["isMerged"] = True
            if fresh_state and detail.get("state") and b.get("pr"):
                b["pr"]["state"] = detail["state"]
        stack_fetched = _git_scope_fresh(git_observation, [st['trunk'], *[
            branch['name'] for branch in st['branches'] if not branch.get('isMerged')]])
        rows, problems, notes = build_rows(st, effective_prs,
                                           fetched=stack_fetched if git_observation.get('refs') is None else True,
                                           refs=refs, remote=remote, ref_observations=git_observation.get('refs'),
                                           pr_observations=effective_observations)
        conflicts = local_conflicts[stack_index]
        if tuple(bool(b.get("isMerged")) for b in st["branches"]) != merged_shapes[stack_index]:
            conflicts = evaluate_stack_conflicts(st, refs, remote, run_fn=run)
        by_branch = {r["branch"]: r for r in conflicts["layers"]}
        for row in rows:
            local = by_branch.get(row["branch"], {})
            row["local_merge_clean"] = local.get("clean")
            row["local_merge_reason"] = local.get("reason", "merged layer")
            row["provenance"] = client.observations.get(row["pr"], {})
            row["branch_observation"] = getattr(client, "branch_observations", {}).get(row["branch"], {})
            row["hosted_stale"] = (not row["provenance"] or any(v.get("freshness") != "fresh" for v in row["provenance"].values())) if row["pr"] else True
            if local.get("clean") is False:
                problems.append(f"L{row['layer']} {row['branch']}: local content conflict against intended parent")
            before = previous_rows.get((st["trunk"], row["branch"]), {})
            keys = ("head", "origin", "base", "ci", "mergeable", "merge_state", "needs_rebase", "local_merge_clean")
            row["changed"] = any(row.get(k) != before.get(k) for k in keys)
        trunk_origin = refs.get(f"refs/remotes/{remote}/{st['trunk']}") if stack_fetched else None
        active = [r for r in rows if not r.get("merged")]
        combined = conflicts["combined"]
        top = active[-1] if active else {}
        missing = [r["branch"] for r in active[:-1] if not (r.get("origin") or r.get("head")) or not combined.get("head") or not is_ancestor(r.get("origin") or r["head"], combined["head"])]
        landing = {"landable": False if missing else combined["clean"], "top": top.get("branch"),
                   "top_sha": combined.get("head"), "reason": "top does not contain: " + ", ".join(missing) if missing else combined["reason"]}
        blocking = ([warning for warning in scope_diagnostics(snapshot, stacks=[st])
                     if not warning.startswith('No local gh-stack catalog')]
                    if selector else SKIPPED)
        if blocking:
            problems.append(f"discovery incomplete: {len(blocking)} catalog/worktree diagnostic(s)")
            landing["landable"] = None
            landing["reason"] = "local catalog discovery incomplete"
        def chain_unknown(row):
            if row.get("base_ok") is None or row.get("origin_ok") is None:
                return True
            if row["pr"]:
                return any(row["provenance"].get(field, {}).get("freshness") != "fresh"
                           for field in ("state", "baseRefName", "headRefOid"))
            absent = row["branch_observation"]
            return absent.get("exists") is not False or absent.get("freshness") != "fresh"
        coherent = False if problems else (None if any(chain_unknown(r) for r in active) else True)
        any_problem |= coherent is not True or conflicts["clean"] is not True
        entry = {"trunk": st["trunk"], "trunk_origin": trunk_origin, "id": st.get("id"), "number": st.get("number"),
                 "structure_observation": st["structure_observation"],
                 "worktree": st.get("worktree"), "branches": st["branches"], "rows": rows, "problems": problems,
                 "notes": notes, "coherent": coherent, "landing": landing, "local_mergeability": conflicts}
        report.append(entry)
    final_snapshot = read_local_snapshot(remote, run_fn=run)
    changed = (_scope_epoch(final_snapshot, epoch_scope, remote=remote) != _scope_epoch(snapshot, epoch_scope, remote=remote)
               if epoch_scope is not None else final_snapshot['fingerprint'] != snapshot['fingerprint'])
    if changed:
        raise ToolError("Snapshot changed during evaluation; retry the scoped report",
                        "STATE.SNAPSHOT_CHANGED")
    required_refs = sorted({stack['trunk'] for stack in stacks} | {
        branch['name'] for stack in stacks for branch in stack['branches'] if not branch.get('isMerged')})
    # Lifecycle may have retired a deleted catalog branch after the initial
    # fetch. Qualify freshness against the complete active report scope, while
    # retaining every requested ref's failed observation for diagnostics.
    git_observation = dict(git_observation, requested_fresh=git_observation['fresh'], required_refs=required_refs,
                           fresh=_git_scope_fresh(git_observation, required_refs))
    payload = {"schema_version": 1, "success": True, "stacks": report, "hidden": hidden, "coherent": not any_problem,
               "catalogs": snapshot.get("catalogs", []),
               "skipped_worktrees": SKIPPED, "warnings": list(dict.fromkeys(SKIPPED + client.warnings)),
               "git_observation": git_observation, "observations": client.observations, "metrics": client.metrics,
               "snapshot_id": hashlib.sha256((snapshot["fingerprint"] + str(client.snapshot_id)).encode()).hexdigest()[:24]}
    write_snapshot(previous_path, payload)
    if args.json or getattr(args, 'compact_json', False):
        print(json.dumps(compact_report(payload) if getattr(args, 'compact_json', False) else payload, indent=2))
    else:
        blocks = [render_table(entry, entry["rows"], entry["problems"], entry["notes"], entry["landing"],
                               trunk_origin=entry["trunk_origin"], full=getattr(args, "full", False), coherent=entry["coherent"])
                  for entry in report]
        print("\n\n".join(blocks))
        print(f"snapshot {payload['snapshot_id']}; git {git_observation['source']}; {len(report)} stack(s); hosted observations age/source in --json")
        if hidden:
            print(f"hidden: {hidden} merged/closed/other-trunk stack(s); --all to show")
        for warning in payload["warnings"][:5]:
            print("warning: " + warning)
        if len(payload["warnings"]) > 5:
            print(f"warnings: {len(payload['warnings'])} total; --json for all")
        print(legend())
    return 1 if any_problem else 0


if __name__ == "__main__":
    sys.exit(main())
