#!/usr/bin/env python3
"""Convert N existing branches (each based on trunk) into one linear gh stack.

Usage: python3 gh_stack_convert.py <trunk> <bottom> ... <top> [--cwd PATH]

Arguments after trunk are branch names or PR numbers (resolved via `gh pr view`),
bottom to top. Each layer is rebased `--onto` the layer below, replaying only
that layer's own commits: the rebase upstream bound is the layer's recorded
pre-conversion base (see below), falling back to `<remote>/<trunk>`. Idempotent:
layers already chained are skipped, so re-run after resolving a conflict. Ends
with `gh stack init` (nothing is pushed).

Before each layer is first rebased, its pre-rebase tip is recorded under
`refs/sc-gh-stack/orig/<branch>`. These refs let a layer that was branched off
the layer below (rather than off trunk) rebase with an exact upstream bound —
even across conflict-resume re-runs — so the lower layer's commits are never
replayed twice. All such refs are deleted when the whole chain succeeds.

Exit codes:
  0  all layers chained and stack initialised; next step is `gh stack submit --auto`
  3  rebase conflict; data.conflict names the layer and files
  5  invalid input (arguments, missing branch, missing remote trunk, dirty tree,
     rebase already in progress, diverged branch)
  1  git fetch, a non-conflict rebase failure, or gh stack init failed
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gh_stack_shared as gs  # noqa: E402

EXIT_OK, EXIT_ERR, EXIT_CONFLICT, EXIT_INPUT = 0, 1, 3, 5
ORIG_REF_PREFIX = "refs/sc-gh-stack/orig/"


@dataclass
class ChainResult:
    chained: List[Dict[str, str]] = field(default_factory=list)   # {"branch", "onto", "action"}
    conflict: Optional[Dict[str, Any]] = None                      # {"layer", "onto", "files"}
    failure: Optional[Dict[str, Any]] = None                       # {"code", "exit", "layer", "message", "action"}


def resolve_layers(args: List[str], cwd: Optional[Path] = None) -> List[str]:
    """Map PR numbers to head branches; pass branch names through. Raises ValueError."""
    layers: List[str] = []
    for a in args:
        if gs.PR_NUMBER.match(a):
            branch = gs.resolve_pr_branch(a, cwd=cwd)
            if not branch:
                raise ValueError(f"cannot resolve PR #{a} to a branch")
            layers.append(branch)
        else:
            layers.append(a)
    if len(set(layers)) != len(layers):
        raise ValueError(f"duplicate layers: {layers}")
    return layers


def ensure_local_branches(layers: List[str], remote: str, cwd: Optional[Path] = None) -> None:
    """Create tracking branches for layers that exist only on the remote. Raises ValueError."""
    for b in layers:
        if gs.local_branch_exists(b, cwd=cwd):
            continue
        if gs.remote_branch_exists(remote, b, cwd=cwd):
            gs.git(["branch", "--track", b, f"{remote}/{b}"], cwd=cwd)
            continue
        raise ValueError(f"branch not found locally or on {remote}: {b}")


def stack_shape(trunk: str, layers: List[str]) -> str:
    return f"({trunk}) <- " + " <- ".join(layers)


def _orig_ref(branch: str) -> str:
    return f"{ORIG_REF_PREFIX}{branch}"


def _orig_tip(branch: str, cwd: Optional[Path] = None) -> Optional[str]:
    r = gs.git(["rev-parse", "--verify", "--quiet", _orig_ref(branch)], cwd=cwd)
    tip = r.stdout.strip()
    return tip if r.returncode == 0 and tip else None


def _has_merges(upstream: str, layer: str, cwd: Optional[Path] = None) -> bool:
    return gs.git_out(["rev-list", "--merges", f"{upstream}..{layer}"], cwd=cwd) != ""


def _fast_forward(branch: str, target: str, cwd: Optional[Path] = None) -> bool:
    if gs.git_out(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd) == branch:
        return gs.git(["merge", "--ff-only", target], cwd=cwd).returncode == 0
    return gs.git(["branch", "-f", branch, target], cwd=cwd).returncode == 0


def clear_orig_refs(layers: List[str], cwd: Optional[Path] = None) -> None:
    for b in layers:
        if _orig_tip(b, cwd=cwd):
            gs.git(["update-ref", "-d", _orig_ref(b)], cwd=cwd)


def chain(layers: List[str], trunk_ref: str, remote: str, cwd: Optional[Path] = None) -> ChainResult:
    """Rebase each layer onto the one below, bottom-up. Stops at the first conflict.

    Skip rule: a layer is already chained only if the layer below is its ancestor
    AND no merge commits sit between them (a merge from trunk — GitHub's "Update
    branch" — must be linearised, not kept).

    Upstream bound per rebase, most exact first: the below layer's recorded
    pre-rebase tip (if this layer descends from it), the below layer's current
    tip (merge-flattening case), else trunk_ref. A stale local trunk can never
    be used: trunk_ref is always the remote trunk tip.
    """
    result = ChainResult()
    below = trunk_ref
    below_name: Optional[str] = None
    for layer in layers:
        if gs.is_ancestor(below, layer, cwd=cwd) and not _has_merges(below, layer, cwd=cwd):
            result.chained.append({"branch": layer, "onto": below, "action": "skip"})
            below, below_name = layer, layer
            continue

        # First touch of this layer: refuse to chain a local branch that is
        # missing remote commits (PR updated elsewhere) — submit would
        # force-with-lease them away. Fast-forward if strictly behind.
        remote_ref = f"{remote}/{layer}"
        if _orig_tip(layer, cwd=cwd) is None and gs.remote_branch_exists(remote, layer, cwd=cwd) \
                and not gs.is_ancestor(remote_ref, layer, cwd=cwd):
            if gs.is_ancestor(layer, remote_ref, cwd=cwd):
                if not _fast_forward(layer, remote_ref, cwd=cwd):
                    result.failure = {"code": "CONVERT.REBASE_FAILED", "exit": EXIT_ERR, "layer": layer,
                                      "message": f"could not fast-forward {layer} to {remote_ref}",
                                      "action": "inspect the branch state and re-run"}
                    return result
            else:
                result.failure = {"code": "GIT.BRANCH_DIVERGED", "exit": EXIT_INPUT, "layer": layer,
                                  "message": f"{layer} and {remote_ref} have diverged; converting the "
                                             f"local branch would drop the remote's commits on submit",
                                  "action": f"reconcile first (e.g. `git checkout {layer} && git rebase "
                                            f"{remote_ref}`), then re-run"}
                return result

        upstream = trunk_ref
        if below_name is not None:
            orig_below = _orig_tip(below_name, cwd=cwd)
            if orig_below and gs.is_ancestor(orig_below, layer, cwd=cwd):
                upstream = orig_below
            elif gs.is_ancestor(below, layer, cwd=cwd):
                upstream = below
        if _orig_tip(layer, cwd=cwd) is None:
            gs.git(["update-ref", _orig_ref(layer), layer], cwd=cwd)

        rebase = gs.git(["rebase", "--onto", below, upstream, layer], cwd=cwd)
        if rebase.returncode != 0:
            files = gs.conflicted_files(cwd=cwd)
            if files and gs.rebase_in_progress(cwd=cwd):
                result.conflict = {"layer": layer, "onto": below, "files": files}
            else:
                result.failure = {"code": "CONVERT.REBASE_FAILED", "exit": EXIT_ERR, "layer": layer,
                                  "message": f"rebase of {layer} failed without a conflict: "
                                             f"{rebase.stderr.strip()}",
                                  "action": "fix the reported problem and re-run; finished layers are skipped"}
            return result
        result.chained.append({"branch": layer, "onto": below, "action": "rebased"})
        below, below_name = layer, layer
    return result


def init_stack(trunk: str, layers: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Adopt the chained branches with `gh stack init` unless a stack already exists here."""
    co = gs.git(["checkout", "-q", layers[-1]], cwd=cwd)
    if co.returncode != 0:
        return {"action": "init_failed", "exit_code": co.returncode, "stderr": co.stderr.strip()}
    if gs.gh(["stack", "view", "--json"], cwd=cwd).returncode == 0:
        return {"action": "existing_stack_kept",
                "note": "a local stack already exists; if its composition differs, run "
                        "`gh stack unstack --local` and re-run"}
    init = gs.gh(["stack", "init", "--base", trunk, *layers], cwd=cwd)
    if init.returncode != 0:
        return {"action": "init_failed", "exit_code": init.returncode, "stderr": init.stderr.strip()}
    return {"action": "initialised"}


def convert(trunk: str, raw_layers: List[str], cwd: Optional[Path] = None) -> tuple[int, Dict[str, Any]]:
    """Full workflow. Returns (exit_code, envelope). Testable without argparse."""
    def fail(code: int, err_code: str, msg: str, action: str, data: Optional[Dict[str, Any]] = None):
        return code, gs.envelope(False, data, gs.error_obj(err_code, msg, code != EXIT_ERR, action))

    if len(raw_layers) < 2:
        return fail(EXIT_INPUT, "VALIDATION.INPUT", "a stack needs at least two layers",
                    "pass <trunk> <bottom> ... <top>, bottom to top")

    if gs.rebase_in_progress(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.REBASE_IN_PROGRESS", "a rebase is already in progress",
                    "finish it (`git rebase --continue` after resolving, or `git rebase --abort`), then re-run")
    if not gs.working_tree_clean(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.DIRTY_TREE", "the working tree has uncommitted changes",
                    "commit or stash them, then re-run")

    remote_names = gs.remotes(cwd=cwd)
    if not remote_names:
        return fail(EXIT_INPUT, "GIT.REMOTE", "no git remote configured", "git remote add origin <url>")
    if len(remote_names) > 1 and not gs.config_get("remote.pushDefault", cwd=cwd):
        return fail(EXIT_INPUT, "GIT.REMOTE",
                    f"{len(remote_names)} remotes and remote.pushDefault unset",
                    "git config remote.pushDefault origin")
    remote = gs.resolve_remote(cwd=cwd)

    gs.git(["config", "rerere.enabled", "true"], cwd=cwd)
    fetch = gs.git(["fetch", remote, "--prune"], cwd=cwd)
    if fetch.returncode != 0:
        return fail(EXIT_ERR, "GIT.FETCH", f"git fetch {remote} failed: {fetch.stderr.strip()}",
                    "check network/auth and re-run")

    trunk_ref = f"{remote}/{trunk}"
    if not gs.remote_branch_exists(remote, trunk, cwd=cwd):
        return fail(EXIT_INPUT, "GIT.TRUNK_NOT_FOUND", f"trunk not on remote: {trunk_ref}",
                    "check the trunk name")

    try:
        layers = resolve_layers(raw_layers, cwd=cwd)
        if trunk in layers:
            raise ValueError(f"layer equals trunk: {trunk}")
        ensure_local_branches(layers, remote, cwd=cwd)
    except ValueError as exc:
        return fail(EXIT_INPUT, "VALIDATION.INPUT", str(exc), "fix the layer list and re-run")

    base = {"trunk": trunk, "remote": remote, "layers": layers, "shape": stack_shape(trunk, layers)}
    result = chain(layers, trunk_ref, remote, cwd=cwd)
    if result.conflict:
        data = {**base, "chained": result.chained, "conflict": result.conflict,
                "next_step": "resolve the listed files, `git add` them, `git rebase --continue` "
                             "(repeat if it conflicts again), then re-run this command; finished "
                             "layers are skipped"}
        return fail(EXIT_CONFLICT, "CONVERT.CONFLICT",
                    f"conflict rebasing {result.conflict['layer']} onto {result.conflict['onto']}",
                    data["next_step"], data)
    if result.failure:
        f = result.failure
        data = {**base, "chained": result.chained, "conflict": None, "failure": f}
        return fail(f["exit"], f["code"], f["message"], f["action"], data)

    clear_orig_refs(layers, cwd=cwd)
    init = init_stack(trunk, layers, cwd=cwd)
    data = {**base, "chained": result.chained, "conflict": None, "stack_init": init,
            "next_step": "review `gh stack view --json` (all layers, given order, needsRebase=false), "
                         "then `gh stack submit --auto`"}
    if init["action"] == "init_failed":
        return fail(EXIT_ERR, "STACK.INIT_FAILED", "gh stack init failed", "see stack_init.stderr", data)
    return EXIT_OK, gs.envelope(True, data)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="convert existing branches/PRs into a gh stack")
    parser.add_argument("trunk")
    parser.add_argument("layers", nargs="+", help="branch names or PR numbers, bottom to top")
    parser.add_argument("--cwd", type=Path, default=None)
    args = parser.parse_args(argv)
    code, payload = convert(args.trunk, args.layers, cwd=args.cwd)
    gs.emit(payload)
    return code


if __name__ == "__main__":
    sys.exit(main())
