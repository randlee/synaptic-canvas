#!/usr/bin/env python3
"""One-call status table for a `gh stack`.

Installed as ``.claude/scripts/gh_stack_view.py`` by the sc-gh-stack package
(command: ``/sc-gh-stack-view``, skill: ``sc-gh-stack-view``).

Combines exactly three data sources into one table:

1. ``gh stack view --json``  - local stack tracking: layer order, head/base
   SHAs, needsRebase, PR number.
2. ``git rev-parse origin/<branch>`` (after one ``git fetch``) - what is
   actually pushed.
3. One batched GraphQL query - per-PR ``mergeable``, ``mergeStateStatus``,
   ``baseRefName``, ``headRefOid``, ``isDraft`` and CI rollup.

Coherence checks (the two metrics conventional per-branch calls never show):

* ``base ok``  - each layer's base == the layer below's head (bottom == trunk).
* ``origin ok`` - local head == origin head == PR head.
* ``needsRebase`` straight from gh stack, plus GitHub's ``mergeable`` /
  ``mergeStateStatus`` which reveal CONFLICTING / BEHIND / DIRTY layers.

Read-only. Never runs ``gh stack sync`` or ``gh stack rebase``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_stack_shared import ToolError, guarded, is_ancestor, origin_sha, run, short  # noqa: E402


SKIPPED: list[str] = []  # worktrees the discovery could not read, reported once as warnings


def stack_json_at(path: str) -> dict | None:
    """None when this worktree is not on a stack; unreadable worktrees are recorded in SKIPPED."""
    try:
        proc = run(["gh", "stack", "view", "--json"], check=False, cwd=path)
    except ToolError as exc:
        SKIPPED.append(f"{path}: {exc} (`git worktree prune` removes stale entries)")
        return None
    if proc.returncode == 2:
        return None  # not in a stack: the normal case for develop/main worktrees
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        why = tail[-1] if tail else "no output"
        if proc.returncode == 6:
            why += " (branch belongs to several stacks; `gh stack checkout <specific-branch>` there)"
        elif proc.returncode == 8:
            why += " (stack file locked by another gh stack process; retry in a few seconds)"
        elif proc.returncode == 10:
            why += " (interrupted `gh stack modify`; run `gh stack modify --abort` there)"
        SKIPPED.append(f"{path}: gh stack view exit {proc.returncode}: {why}")
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        SKIPPED.append(f"{path}: gh stack view --json returned non-JSON ({proc.stdout[:80]!r}); upgrade gh-stack")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("branches"), list) or not data["branches"]:
        return None
    if not isinstance(data.get("trunk"), str) or not all(
        isinstance(b, dict) and isinstance(b.get("name"), str) for b in data["branches"]
    ):
        raise ToolError(f"gh stack view --json in {path} returned an unexpected shape; "
                        "upgrade gh-stack (`gh extension upgrade stack`) or report the output")
    return data


def worktree_paths() -> list[str]:
    """Every worktree of this repo that is checked out on a branch (cwd first)."""
    out = run(["git", "worktree", "list", "--porcelain"]).stdout
    paths: list[str] = []
    cur: str | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            cur = line[len("worktree "):]
        elif line.startswith("branch ") and cur:
            paths.append(cur)
            cur = None
        elif line == "" :
            cur = None
    cwd = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    paths.sort(key=lambda p: p != cwd)
    return paths


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


def discover_stacks(trunk_filter: str | None, *, include_all: bool) -> tuple[list[dict], int]:
    """Run `gh stack view --json` once per worktree, dedupe by branch set.

    Works from any branch not part of a stack (e.g. develop/main): every
    stack that has at least one worktree checked out is found. Concurrent,
    read-only. Filtering/sorting of the deduped list is delegated to
    ``select_stacks``. Returns (stacks, hidden_count).
    """
    paths = worktree_paths()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(stack_json_at, paths))
    found: list[dict] = []
    for path, data in zip(paths, results):
        if data:
            data["worktree"] = path
            found.append(data)

    # Each worktree only knows the layers linked from it; the same stack seen
    # from a lower layer is a prefix of the view from the top. Keep the longest.
    def names(d: dict) -> tuple[str, ...]:
        return tuple(b["name"] for b in d["branches"])
    found = [d for d in found if not any(
        o is not d and len(names(o)) > len(names(d)) and names(o)[: len(names(d))] == names(d)
        for o in found)]
    uniq: dict[tuple[str, ...], dict] = {}
    for d in found:
        uniq.setdefault(names(d), d)
    found = list(uniq.values())

    return select_stacks(found, trunk_filter, include_all=include_all)


def pr_details(numbers: list[int]) -> dict[int, dict]:
    """One GraphQL round-trip for every PR in the stack."""
    if not numbers:
        return {}
    remote = run(["gh", "repo", "view", "--json", "owner,name"]).stdout
    try:
        repo = json.loads(remote)
    except json.JSONDecodeError as exc:
        raise ToolError(f"gh repo view returned non-JSON: {remote[:200]!r}") from exc
    try:
        owner, name = repo["owner"]["login"], repo["name"]
    except (KeyError, TypeError) as exc:
        raise ToolError(f"gh repo view returned an unexpected shape: {remote[:200]!r}; run `gh auth status`") from exc
    if not all(isinstance(n, int) and n > 0 for n in numbers):
        raise ToolError(f"non-integer PR number in gh stack view output: {numbers!r}; upgrade gh-stack")
    fields = (
        "number isDraft mergeable mergeStateStatus baseRefName headRefOid "
        "reviewDecision state "
        "commits(last:1){nodes{commit{statusCheckRollup{state}}}}"
    )
    aliases = " ".join(f"pr{n}: pullRequest(number:{n}) {{ {fields} }}" for n in numbers)
    query = f'query($owner:String!,$name:String!){{ repository(owner:$owner,name:$name) {{ {aliases} }} }}'
    proc = run(["gh", "api", "graphql", "-f", f"query={query}", "-F", f"owner={owner}", "-F", f"name={name}"])
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(f"gh api graphql returned non-JSON: {proc.stdout[:200]!r}") from exc
    data = (payload.get("data") or {}).get("repository")
    if payload.get("errors"):
        msgs = "; ".join(str(e.get("message", "?")) for e in payload["errors"][:3])
        if not data:
            raise ToolError(f"GraphQL errors: {msgs} (PRs {numbers}; use --no-pr for a local-only view)")
        sys.stderr.write(f"gh-stack-view: warning: GraphQL reported: {msgs}; affected PRs show as unknown\n")
    if not data:
        raise ToolError("GraphQL returned no repository data; run `gh auth status` or use --no-pr")
    out: dict[int, dict] = {}
    for n in numbers:
        pr = data.get(f"pr{n}") or {}
        nodes = ((pr.get("commits") or {}).get("nodes") or [{}])
        rollup = ((nodes[0].get("commit") or {}).get("statusCheckRollup") or {}).get("state")
        pr["ci"] = rollup or "NONE"
        out[n] = pr
    return out


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


def build_rows(stack: dict, prs: dict[int, dict], *, fetched: bool) -> tuple[list[dict], list[str], list[str]]:
    trunk = stack["trunk"]
    trunk_origin = origin_sha(trunk) if fetched else None
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
        if br.get("isMerged"):
            rows.append({"layer": idx, "branch": name, "pr": (br.get("pr") or {}).get("number"),
                         "head": br.get("head"), "base": br.get("base"), "merged": True, "queued": False,
                         "draft": False, "mergeable": None, "merge_state": "MERGED", "ci": pr.get("ci"),
                         "base_ok": None, "origin_ok": None, "needs_rebase": False, "origin": None,
                         "pr_head": pr.get("headRefOid"), "expected_base": expected_base, "pr_base": pr.get("baseRefName")})
            # Merged: its head is (an ancestor of) the trunk head now.  The next
            # open layer must sit on the trunk; ``parent`` stays at the trunk.
            expected_base = trunk_origin or br.get("head") or expected_base
            continue
        # gh stack omits ``head``/``base`` for a layer that has no local branch
        # (e.g. viewed from a sibling worktree before the branch was fetched).
        # Never subscript them directly: a missing key must degrade to ❓, not crash.
        head = br.get("head")
        base = br.get("base")
        origin = origin_sha(name) if fetched else None
        base_ok = (base == expected_base) if (expected_base and base) else None
        origin_ok = None
        if origin:
            if head:
                origin_ok = head == origin and (not pr or pr.get("headRefOid") == origin)
            elif pr:
                # No local head to compare; the remote side (origin vs PR) can still be checked.
                origin_ok = pr.get("headRefOid") == origin
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
        }
        parent_is_trunk = parent == trunk
        if pr and pr.get("baseRefName") not in (None, parent):
            problems.append(f"L{idx} {name}: PR #{row['pr']} base is {pr['baseRefName']}, expected {parent}")
        if base_ok is False:
            # The lowest OPEN layer (idx 1, or any layer whose lower layers are
            # all merged) may sit on an older trunk commit: that is a note, not
            # a rebase order.  Against an open parent it is a real mismatch.
            if parent_is_trunk and is_ancestor(base or "", expected_base):
                notes.append(f"L{idx} {name}: behind trunk ({short(base)} < {short(expected_base)}); fine unless CONFLICTING, do not restart CI just to catch up")
            else:
                problems.append(f"L{idx} {name}: base {short(base)} != parent head {short(expected_base)} -> needs rebase")
        if origin_ok is False:
            problems.append(
                f"L{idx} {name}: local {short(head)} / origin {short(origin)} / PR {short(pr.get('headRefOid'))} differ"
                " -> local tracking stale or unpushed; owner must fetch+reset or push"
            )
        if br.get("needsRebase"):
            problems.append(f"L{idx} {name}: gh stack reports needsRebase")
        if pr.get("mergeable") == "CONFLICTING":
            problems.append(f"L{idx} {name}: PR #{row['pr']} CONFLICTING")
        if pr.get("isDraft"):
            problems.append(f"L{idx} {name}: PR #{row['pr']} is DRAFT (blocks stack merge)")
        rows.append(row)
        # The next layer must be based on THIS layer's pushed head (fall back to local, then PR).
        expected_base = origin or head or pr.get("headRefOid") or expected_base
        parent = name
    return rows, problems, notes


ICON_SYNC = {"ok": "✅", "stale": "🔄", "rebase": "⚠️", "unknown": "❓"}
ICON_MERGE = {"MERGED": "\U0001f3c1", "OK": "✅", "BLOCKED": "\U0001f6a7"}
ICON_CI = {"SUCCESS": "✅", "FAILURE": "⛔", "ERROR": "⛔", "PENDING": "\U0001f300",
           "EXPECTED": "\U0001f300", "NONE": "—"}


def sync_icon(r: dict) -> str:
    if r["merged"]:
        return ICON_MERGE["MERGED"]
    if r["origin_ok"] is False:
        return ICON_SYNC["stale"]
    if r["base_ok"] is False or r["needs_rebase"]:
        return ICON_SYNC["rebase"]
    if r["base_ok"] is None or r["origin_ok"] is None:
        return ICON_SYNC["unknown"]
    return ICON_SYNC["ok"]


def merge_icon(r: dict) -> str:
    """✅ only when GitHub says the PR can merge now; anything else is 🚧."""
    if r["merged"]:
        return ICON_MERGE["MERGED"]
    if r["draft"] or r["queued"] or r["mergeable"] != "MERGEABLE":
        return ICON_MERGE["BLOCKED"]
    return ICON_MERGE["OK"] if r["merge_state"] in ("CLEAN", "HAS_HOOKS", "UNSTABLE") else ICON_MERGE["BLOCKED"]


def ci_icon(r: dict) -> str:
    return ICON_CI.get(r["ci"] or "NONE", ICON_CI["NONE"])


def render_landing(landing: dict) -> str:
    if landing["landable"] is None:
        return f"LANDING: ❓ not judged - {landing['reason']}"
    if landing["landable"]:
        return f"LANDING: ✅ one merge of {landing['top']} @ {short(landing['top_sha'])} lands the stack - {landing['reason']}"
    return f"LANDING: ❌ {landing['top']} @ {short(landing.get('top_sha'))} cannot land as one merge - {landing['reason']}"


def render_table(stack: dict, rows: list[dict], problems: list[str], notes: list[str], landing: dict, *, trunk_origin: str | None) -> str:
    hdr = ["L", "PR", "rebase", "merge", "CI"]
    lines = [f"stack: {stack['branches'][-1]['name']} -> {stack['trunk']} @ {short(trunk_origin)}", ""]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "|".join("---" for _ in hdr) + "|")
    for r in rows:
        pr = f"#{r['pr']}" if r["pr"] else "-"
        lines.append("| " + " | ".join([
            f"{r['layer']}/{len(rows)}", pr, sync_icon(r), merge_icon(r), ci_icon(r),
        ]) + " |")
    lines.append("")
    if problems:
        lines.append(f"VERDICT: ❌ NOT COHERENT ({len(problems)} issue(s))")
        lines.extend(f"- {p}" for p in problems)
    else:
        lines.append("VERDICT: ✅ COHERENT - every base == parent head, every head pushed and on its PR")
    lines.append(render_landing(landing))
    lines.extend(f"- note: {n}" for n in notes)
    return "\n".join(lines)


def legend() -> str:
    lines = []
    lines.append("rebase: ✅ not needed (base==parent head, local==origin==PR)  ⚠️ needed  🔄 local tracking stale: fetch+reset before any sync  ❓ unknown (--no-fetch)  🏁 merged")
    lines.append("merge: ✅ mergeable now  🚧 blocked (conflicting, behind, draft, queued, required checks, or still computing)  🏁 merged")
    lines.append("CI: ✅ green  🌀 running  ⛔ failed, do not enter  — none")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trunk", help="only stacks whose trunk is this branch (e.g. develop, integrate/phase-bc)")
    ap.add_argument("--phase", help="shorthand for --trunk integrate/phase-<PHASE>")
    ap.add_argument("--all", action="store_true", help="show every stack, including merged/closed ones and other trunks")
    ap.add_argument("--no-fetch", action="store_true", help="skip `git fetch origin` and origin comparison")
    ap.add_argument("--no-pr", action="store_true", help="skip the GraphQL PR query (offline / local-only view)")
    ap.add_argument("--json", action="store_true", help="emit the merged rows as JSON instead of tables")
    args = ap.parse_args()
    trunk_filter = args.trunk or (f"integrate/phase-{args.phase.lower()}" if args.phase else None)

    return guarded("gh-stack-view", lambda: run_report(args, trunk_filter))


def preflight() -> None:
    for tool in ("git", "gh"):
        if not shutil.which(tool):
            raise ToolError(f"`{tool}` not on PATH")
    if run(["gh", "stack", "--help"], check=False).returncode != 0:
        raise ToolError("gh-stack extension missing: `gh extension install github/gh-stack`")
    if run(["git", "rev-parse", "--git-dir"], check=False).returncode != 0:
        raise ToolError("not inside a git repository")


def run_report(args: argparse.Namespace, trunk_filter: str | None) -> int:
    preflight()
    stacks, hidden = discover_stacks(trunk_filter, include_all=args.all)
    if not stacks:
        where = f" with trunk {trunk_filter}" if trunk_filter else ""
        hint = f" ({hidden} merged/closed/other-trunk stack(s) hidden; --all to show)" if hidden else ""
        sys.stderr.write(
            f"no open gh stack found{where}{hint}. Stacks are discovered through `git worktree list`; a stack "
            "needs at least one of its layers checked out in a worktree (never `git checkout` in the main repo).\n"
        )
        return 2
    fetched = not args.no_fetch
    if fetched:
        fetch = run(["git", "fetch", "--quiet", "origin"], check=False)
        if fetch.returncode != 0:
            fetched = False
            sys.stderr.write("gh-stack-view: git fetch origin failed; rebase column reported as unknown (❓)\n")
    numbers = sorted({(b.get("pr") or {}).get("number") for st in stacks for b in st["branches"] if (b.get("pr") or {}).get("number") is not None})
    prs = {} if args.no_pr else pr_details(numbers)

    report: list[dict] = []
    blocks: list[str] = []
    any_problem = False
    for st in stacks:
        rows, problems, notes = build_rows(st, prs, fetched=fetched)
        trunk_origin = origin_sha(st["trunk"]) if fetched else None
        if fetched and trunk_origin is None:
            notes.append(f"trunk {st['trunk']} is not on origin; base coherence for L1 and LANDING cannot be judged (push the trunk or check its name)")
        any_problem |= bool(problems)
        landing = landing_verdict(st, rows, trunk_origin)
        report.append({"trunk": st["trunk"], "trunk_origin": trunk_origin, "worktree": st["worktree"],
                       "rows": rows, "problems": problems, "notes": notes, "coherent": not problems,
                       "landing": landing})
        blocks.append(render_table(st, rows, problems, notes, landing, trunk_origin=trunk_origin))
    for line in SKIPPED:
        sys.stderr.write(f"gh-stack-view: warning: skipped worktree {line}\n")
    if args.json:
        print(json.dumps({"stacks": report, "hidden": hidden, "coherent": not any_problem, "skipped_worktrees": SKIPPED}, indent=2))
    else:
        print("\n\n".join(blocks))
        print()
        if hidden:
            print(f"hidden: {hidden} merged/closed/other-trunk stack(s); --all to show")
        print(legend())
    return 1 if any_problem else 0


if __name__ == "__main__":
    sys.exit(main())
