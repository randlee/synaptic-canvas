#!/usr/bin/env python3
"""Convert N existing branches (each based on trunk) into one linear gh stack.

Usage: python3 gh_stack_convert.py <trunk> <bottom> ... <top> [--cwd PATH]

Arguments after trunk are branch names or PR numbers (resolved via `gh pr view`),
bottom to top. Each layer is rebased `--onto` the layer below with
`git rebase --onto <below> <remote>/<trunk> <layer>`, replaying only that
layer's own commits. Idempotent: layers already chained are skipped, so re-run
after resolving a conflict. Ends with `gh stack init` (nothing is pushed).

Exit codes:
  0  all layers chained and stack initialised; next step is `gh stack submit --auto`
  3  rebase conflict; data.conflict names the layer and files
  5  invalid input (arguments, missing branch, missing remote trunk)
  1  git fetch or gh stack init failed
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


@dataclass
class ChainResult:
    chained: List[Dict[str, str]] = field(default_factory=list)   # {"branch", "onto", "action"}
    conflict: Optional[Dict[str, Any]] = None                      # {"layer", "onto", "files"}


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


def chain(layers: List[str], trunk_ref: str, cwd: Optional[Path] = None) -> ChainResult:
    """Rebase each layer onto the one below, bottom-up. Stops at the first conflict.

    trunk_ref is the *remote* trunk tip (e.g. origin/main) so a stale local trunk
    can never be used as the upstream bound.
    """
    result = ChainResult()
    below = trunk_ref
    for layer in layers:
        if gs.is_ancestor(below, layer, cwd=cwd):
            result.chained.append({"branch": layer, "onto": below, "action": "skip"})
        else:
            rebase = gs.git(["rebase", "--onto", below, trunk_ref, layer], cwd=cwd)
            if rebase.returncode != 0:
                result.conflict = {"layer": layer, "onto": below, "files": gs.conflicted_files(cwd=cwd)}
                return result
            result.chained.append({"branch": layer, "onto": below, "action": "rebased"})
        below = layer
    return result


def init_stack(trunk: str, layers: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Adopt the chained branches with `gh stack init` unless a stack already exists here."""
    gs.git(["checkout", "-q", layers[-1]], cwd=cwd)
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

    remote = gs.resolve_remote(cwd=cwd)
    if not remote:
        return fail(EXIT_INPUT, "GIT.REMOTE", "no git remote configured", "git remote add origin <url>")

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
        ensure_local_branches(layers, remote, cwd=cwd)
    except ValueError as exc:
        return fail(EXIT_INPUT, "VALIDATION.INPUT", str(exc), "fix the layer list and re-run")

    base = {"trunk": trunk, "remote": remote, "layers": layers, "shape": stack_shape(trunk, layers)}
    result = chain(layers, trunk_ref, cwd=cwd)
    if result.conflict:
        data = {**base, "chained": result.chained, "conflict": result.conflict,
                "next_step": "resolve the listed files, `git add` them, `git rebase --continue`, "
                             "then re-run this command; finished layers are skipped"}
        return fail(EXIT_CONFLICT, "CONVERT.CONFLICT",
                    f"conflict rebasing {result.conflict['layer']} onto {result.conflict['onto']}",
                    data["next_step"], data)

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
