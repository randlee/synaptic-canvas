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

Three data sources: ``git rev-parse``/``merge-base``/``merge-tree`` after one
fetch, and ONE ``gh pr list`` call.  Never runs a ``gh stack`` write command.

Exit codes: 0 chain is linkable, 1 problems listed under VERDICT, 2 the
environment failed (one ``gh-stack-chain-check: ...`` line on stderr).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_stack_shared import ToolError, guarded, is_ancestor, origin_sha, run, short  # noqa: E402


def merge_clean(base_sha: str, head_sha: str) -> bool | None:
    """True/False from ``git merge-tree --write-tree``; None when git is too old."""
    proc = run(["git", "merge-tree", "--write-tree", base_sha, head_sha], check=False)
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None  # usage error: git < 2.38 or an unexpected failure


PR_FIELDS = "number,headRefName,baseRefName,headRefOid,isDraft,state"


def list_prs() -> list[dict]:
    """One call: every OPEN PR (bounded; closed/merged PRs cannot be linked anyway)."""
    proc = run(["gh", "pr", "list", "--state", "open", "--limit", "500", "--json", PR_FIELDS])
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(f"gh pr list returned non-JSON: {proc.stdout[:200]!r}") from exc
    if not isinstance(data, list):
        raise ToolError("gh pr list returned an unexpected shape; run `gh auth status`")
    return data


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


def view_pr(number: int) -> dict:
    """Exact lookup for a PR number that is not in the open list (closed, merged, or beyond the page)."""
    proc = run(["gh", "pr", "view", str(number), "--json", PR_FIELDS], check=False)
    if proc.returncode != 0:
        raise ToolError(f"PR #{number} not found (`gh pr view {number}` failed); pass a branch name instead")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(f"gh pr view {number} returned non-JSON: {proc.stdout[:200]!r}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("headRefName"), str):
        raise ToolError(f"gh pr view {number} returned an unexpected shape; upgrade gh or pass the branch name")
    return data


def resolve_layers(args: list[str], by_number: dict[int, dict], by_branch: dict[str, dict] | None = None) -> list[str]:
    """Turn PR numbers into head branch names; branch names pass through.

    A number missing from the open list is fetched individually so a closed or
    merged PR is reported by ``evaluate`` as a problem instead of "not found".
    """
    layers: list[str] = []
    for arg in args:
        if arg.isdigit():
            pr = by_number.get(int(arg))
            if pr is None:
                pr = view_pr(int(arg))
                by_number[int(arg)] = pr
                if by_branch is not None:
                    by_branch.setdefault(pr["headRefName"], pr)
            layers.append(pr["headRefName"])
        else:
            layers.append(arg)
    return layers


def evaluate(trunk: str, layers: list[str], by_branch: dict[str, dict], *, fetched: bool, use_pr: bool) -> dict:
    """Pure chain evaluation over injected lookups (origin_sha, is_ancestor, merge_clean)."""
    rows: list[dict] = []
    problems: list[str] = []
    notes: list[str] = []
    trunk_sha = origin_sha(trunk) if fetched else None
    if fetched and trunk_sha is None:
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
        sha = origin_sha(name) if fetched else None
        pr = by_branch.get(name) if use_pr else None
        row = {"layer": idx, "branch": name, "origin": sha, "pr": pr.get("number") if pr else None,
               "pushed": None if not fetched else sha is not None, "contains_parent": None,
               "pr_base_ok": None, "pr_head_ok": None, "draft": bool(pr and pr.get("isDraft")),
               "pr_state": pr.get("state") if pr else None, "expected_base": parent_name}
        if fetched and sha is None:
            problems.append(f"L{idx} {name}: not on origin (unpushed) -> push it before linking")
        elif fetched and parent_sha:
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
            if pr.get("state") != "OPEN":
                problems.append(f"L{idx} {name}: PR #{pr['number']} is {pr.get('state')} -> a merged/closed PR cannot be linked; open a new one")
            if pr.get("isDraft"):
                problems.append(f"L{idx} {name}: PR #{pr['number']} is DRAFT -> blocks gh stack merge; mark ready before landing")
            base_ok = pr.get("baseRefName") == parent_name
            row["pr_base_ok"] = base_ok
            if not base_ok:
                notes.append(f"L{idx} {name}: PR #{pr['number']} base is {pr.get('baseRefName')}, expected {parent_name}; `gh stack link --base {trunk} ...` corrects it, verify afterwards")
            if fetched and sha:
                head_ok = pr.get("headRefOid") == sha
                row["pr_head_ok"] = head_ok
                if not head_ok:
                    problems.append(f"L{idx} {name}: PR #{pr['number']} head {short(pr.get('headRefOid'))} != origin {short(sha)} -> stale PR head; wait for GitHub or re-push")
        elif use_pr:
            notes.append(f"L{idx} {name}: no PR yet; `gh stack link` creates one with base {parent_name}")
        rows.append(row)
        parent_name = name
        parent_sha = sha or parent_sha
    landing: dict = {"clean": None, "reason": "not judged"}
    if fetched and rows and rows[-1]["origin"] and trunk_sha and not any(r["pushed"] is False for r in rows):
        result = merge_clean(trunk_sha, rows[-1]["origin"])
        if result is None:
            landing = {"clean": None, "reason": "git merge-tree --write-tree unavailable (git < 2.38); check with a scratch `git merge --no-commit`"}
        elif result:
            landing = {"clean": True, "reason": f"top {rows[-1]['branch']} @ {short(rows[-1]['origin'])} merges clean into {trunk} @ {short(trunk_sha)}"}
        else:
            landing = {"clean": False, "reason": f"top {rows[-1]['branch']} conflicts with {trunk}; resolve on a new top layer, never on a frozen one"}
            problems.append(f"top {rows[-1]['branch']}: merge into {trunk} conflicts")
    return {"trunk": trunk, "trunk_origin": trunk_sha, "rows": rows, "problems": problems,
            "notes": notes, "landing": landing, "linkable": not problems}


def icon(value: bool | None) -> str:
    return {True: "✅", False: "⛔", None: "❓"}[value]


def render(report: dict) -> str:
    lines = [f"chain: {' -> '.join(r['branch'] for r in report['rows'])} -> {report['trunk']} @ {short(report['trunk_origin'])}", ""]
    hdr = ["L", "branch", "PR", "pushed", "contains parent", "PR base", "PR head"]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "|".join("---" for _ in hdr) + "|")
    for r in report["rows"]:
        pr = f"#{r['pr']}" + (" (draft)" if r["draft"] else "") if r["pr"] else "-"
        lines.append("| " + " | ".join([f"{r['layer']}/{len(report['rows'])}", r["branch"], pr,
                                        icon(r["pushed"]), icon(r["contains_parent"]),
                                        icon(r["pr_base_ok"]) if r["pr"] else "-",
                                        icon(r["pr_head_ok"]) if r["pr"] else "-"]) + " |")
    lines.append("")
    if report["problems"]:
        lines.append(f"VERDICT: ❌ NOT LINKABLE ({len(report['problems'])} issue(s))")
        lines.extend(f"- {p}" for p in report["problems"])
    else:
        lines.append("VERDICT: ✅ LINKABLE - every head pushed, chain linear, PR state consistent")
    land = report["landing"]
    lines.append(f"MERGE INTO TRUNK: {icon(land['clean'])} {land['reason']}")
    lines.extend(f"- note: {n}" for n in report["notes"])
    lines.append("")
    lines.append(f"next: gh stack link --base {report['trunk']} " + " ".join(
        f"#{r['pr']}" if r["pr"] else r["branch"] for r in report["rows"]) + "   (run from a worktree on a stack branch)")
    return "\n".join(lines)


def preflight(*, need_gh: bool) -> None:
    for tool in ("git",) + (("gh",) if need_gh else ()):
        if not shutil.which(tool):
            raise ToolError(f"`{tool}` not on PATH")
    if run(["git", "rev-parse", "--git-dir"], check=False).returncode != 0:
        raise ToolError("not inside a git repository")
    if run(["git", "remote", "get-url", "origin"], check=False).returncode != 0:
        raise ToolError("no `origin` remote; the check compares origin/* refs (`git remote add origin <url>`)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trunk", required=True, help="branch the stack lands on (e.g. develop, integrate/phase-bc)")
    ap.add_argument("layers", nargs="+", help="proposed order bottom to top: branch names or PR numbers")
    ap.add_argument("--no-fetch", action="store_true", help="skip `git fetch origin`; compare against the cached origin/* refs")
    ap.add_argument("--no-pr", action="store_true", help="skip the gh pr list call (local-only view)")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args()
    return guarded("gh-stack-chain-check", lambda: run_check(args))


def run_check(args: argparse.Namespace) -> int:
    preflight(need_gh=not args.no_pr)
    if not args.no_fetch:
        fetch = run(["git", "fetch", "--quiet", "origin"], check=False)
        if fetch.returncode != 0:
            tail = (fetch.stderr or fetch.stdout).strip().splitlines()
            sys.stderr.write(f"gh-stack-chain-check: warning: git fetch origin failed ({tail[-1] if tail else 'no output'}); comparing against cached origin/* refs\n")
    prs = [] if args.no_pr else list_prs()
    by_number, by_branch = index_prs(prs)
    layers = resolve_layers(args.layers, by_number, by_branch)
    report = evaluate(args.trunk, layers, by_branch, fetched=True, use_pr=not args.no_pr)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0 if report["linkable"] else 1


if __name__ == "__main__":
    sys.exit(main())
