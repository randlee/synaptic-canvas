#!/usr/bin/env python3
"""Sync the current stack after trunk moved or a layer merged. Wraps `gh stack sync`.

Usage: python3 gh_stack_sync.py [--cwd PATH]

Run with a stack branch checked out (typically in the stack's worktree).
`gh stack sync` fetches, reconciles with GitHub, fast-forwards trunk,
cascade-rebases when needed (merged PRs handled automatically), and pushes all
active branches atomically. On a rebase conflict it restores EVERY branch to
its pre-sync state and exits 3 — the repository is never left half-synced.

Envelope contract: success is a minimal decision log (per-branch before/after
SHAs and pushed state); every failure carries the exact command that failed,
its stderr, and one recovery action — replaying the tool call shows what
happened without further investigation.

Exit codes:
  0  synced and pushed; data.branches shows per-branch before/after/pushed
  3  rebase conflict; all branches were restored; resolve via `gh stack rebase`
  5  guard refused (not a repo, no stack here, dirty tree, rebase in progress),
     or sync deliberately did nothing (SYNC.ABORTED: local/remote stacks
     diverged — `gh stack sync` exits 0 with "Sync aborted" in that case)
  1  sync failed for another reason (stderr included)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gh_stack_shared as gs  # noqa: E402

EXIT_OK, EXIT_ERR, EXIT_CONFLICT, EXIT_INPUT = 0, 1, 3, 5


def stack_branches(cwd: Optional[Path] = None) -> Optional[Tuple[str, List[str]]]:
    """(trunk, branch names) from `gh stack view --json`, or None if no stack here."""
    view = gs.gh(["stack", "view", "--json"], cwd=cwd)
    if view.returncode != 0:
        return None
    try:
        payload = json.loads(view.stdout)
        return payload.get("trunk", ""), [b["name"] for b in payload.get("branches", [])]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def branch_states(branches: List[str], remote: str, before: Dict[str, Optional[str]],
                  cwd: Optional[Path] = None) -> List[Dict[str, Any]]:
    states = []
    for b in branches:
        local = gs.git_out(["rev-parse", "--verify", "--quiet", f"refs/heads/{b}"], cwd=cwd) or None
        remote_sha = gs.git_out(["rev-parse", "--verify", "--quiet",
                                 f"refs/remotes/{remote}/{b}"], cwd=cwd) or None
        states.append({"name": b, "before": before.get(b), "after": local,
                       "remote": remote_sha, "pushed": local is not None and local == remote_sha})
    return states


def sync(cwd: Optional[Path] = None) -> Tuple[int, Dict[str, Any]]:
    def fail(code: int, err_code: str, msg: str, action: str,
             data: Optional[Dict[str, Any]] = None, recoverable: bool = True):
        return code, gs.envelope(False, data, gs.error_obj(err_code, msg, recoverable, action))

    if not gs.in_git_repo(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.NOT_A_REPO", "not inside a git repository",
                    "cd into the stack's worktree (or pass --cwd)", recoverable=False)
    if gs.rebase_in_progress(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.REBASE_IN_PROGRESS", "a rebase is already in progress",
                    "finish it (`gh stack rebase --continue` after resolving, or `--abort`), then re-run")
    if not gs.working_tree_clean(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.DIRTY_TREE", "the working tree has uncommitted changes",
                    "commit or stash them, then re-run")

    found = stack_branches(cwd=cwd)
    if not found:
        return fail(EXIT_INPUT, "SYNC.NO_STACK", "the current branch is not part of a tracked stack",
                    "run in the stack's worktree with a stack branch checked out "
                    "(`gh stack checkout <branch>`)")
    trunk, branches = found
    remote = gs.resolve_remote(cwd=cwd) or "origin"
    before = {b: gs.git_out(["rev-parse", "--verify", "--quiet", f"refs/heads/{b}"], cwd=cwd) or None
              for b in branches}

    run = gs.gh(["stack", "sync"], cwd=cwd)
    data: Dict[str, Any] = {"trunk": trunk, "remote": remote,
                            "branches": branch_states(branches, remote, before, cwd=cwd)}
    if run.returncode == 3:
        data["next_step"] = ("all branches were restored to their pre-sync state; run "
                            "`gh stack rebase`, resolve + `git add` + `gh stack rebase --continue` "
                            "until it finishes, then re-run this script")
        return fail(EXIT_CONFLICT, "SYNC.CONFLICT",
                    f"`gh stack sync` hit a rebase conflict: {run.stderr.strip()}",
                    data["next_step"], data)
    if run.returncode != 0:
        return fail(EXIT_ERR, "SYNC.FAILED",
                    f"`gh stack sync` exited {run.returncode}: {run.stderr.strip()}",
                    "read the message, fix the reported problem, and re-run", data,
                    recoverable=False)
    # Non-interactive `gh stack sync` exits 0 WITHOUT syncing when the local and
    # remote stacks diverged: it prints both chains plus "Sync aborted" and
    # changes nothing (references/troubleshooting.md, "Local and remote stacks
    # have diverged"). Exit 0 alone is therefore not proof the sync happened.
    if "sync aborted" in (run.stdout + run.stderr).lower():
        data["next_step"] = ("local and remote stacks diverged; nothing was fetched, rebased, or "
                             "pushed — choose one: keep remote (`gh stack unstack --local`, then "
                             "`gh stack checkout <stack-or-pr-number>`) or keep local (see "
                             "references/troubleshooting.md, 'Local and remote stacks have diverged')")
        return fail(EXIT_INPUT, "SYNC.ABORTED",
                    "`gh stack sync` aborted without syncing: local and remote stacks diverged",
                    data["next_step"], data, recoverable=False)

    data["next_step"] = None
    return EXIT_OK, gs.envelope(True, data)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="sync the current gh stack (wraps `gh stack sync`)")
    parser.add_argument("--cwd", type=Path, default=None)
    args = parser.parse_args(argv)
    code, payload = sync(cwd=args.cwd)
    gs.emit(payload)
    return code


if __name__ == "__main__":
    sys.exit(main())
