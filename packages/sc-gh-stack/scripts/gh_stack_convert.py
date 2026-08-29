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
replayed twice. The conversion's identity (trunk + layer list) is stored in the
local git config key `sc-gh-stack.conversion`; the orig refs are kept until a
conversion with a DIFFERENT identity starts, at which point all of them are
deleted. Keeping them after success is what makes re-runs idempotent while the
branches still await `gh stack submit`.

Exit codes:
  0  all layers chained and stack initialised; next step is `gh stack submit --auto`
  3  rebase conflict; data.conflict names the layer and files
  5  invalid input (arguments, missing branch, missing remote trunk, not a repo,
     dirty tree, rebase already in progress, diverged branch)
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


def branch_states(layers: List[str], remote: str, before: Dict[str, Optional[str]],
                  cwd: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Per-branch state for the report: local/remote tips and pushed-ness.

    `pushed` is true only when the local tip equals the remote tip — after a
    rebase it goes false until `gh stack submit` runs.
    """
    states = []
    for b in layers:
        local = _rev(_head(b), cwd=cwd)
        remote_sha = _rev(f"refs/remotes/{remote}/{b}", cwd=cwd)
        states.append({"name": b, "before": before.get(b), "after": local,
                       "remote": remote_sha, "pushed": local is not None and local == remote_sha})
    return states


def _head(branch: str) -> str:
    """Unambiguous ref for a local branch (a same-named tag must never win)."""
    return f"refs/heads/{branch}"


def _orig_ref(branch: str) -> str:
    return f"{ORIG_REF_PREFIX}{branch}"


def _rev(ref: str, cwd: Optional[Path] = None) -> Optional[str]:
    r = gs.git(["rev-parse", "--verify", "--quiet", ref], cwd=cwd)
    tip = r.stdout.strip()
    return tip if r.returncode == 0 and tip else None


def _orig_tip(branch: str, cwd: Optional[Path] = None) -> Optional[str]:
    return _rev(_orig_ref(branch), cwd=cwd)


def _has_merges(upstream: str, layer_ref: str, cwd: Optional[Path] = None) -> bool:
    return gs.git_out(["rev-list", "--merges", f"{upstream}..{layer_ref}"], cwd=cwd) != ""


def _fast_forward(branch: str, target: str, cwd: Optional[Path] = None):
    """Returns the CompletedProcess of the attempted update (caller checks rc/stderr)."""
    if gs.git_out(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd) == branch:
        return gs.git(["merge", "--ff-only", target], cwd=cwd)
    return gs.git(["branch", "-f", branch, target], cwd=cwd)


def begin_conversion(trunk: str, layers: List[str], cwd: Optional[Path] = None) -> None:
    """Clear ALL orig refs left by a conversion with a different identity.

    Stale refs from an abandoned conversion must never suppress the divergence
    guard or serve as upstream bounds for a different layer set.
    """
    conv_id = " ".join([trunk, *layers])
    if gs.config_get("sc-gh-stack.conversion", cwd=cwd) != conv_id:
        out = gs.git_out(["for-each-ref", "--format=%(refname)", ORIG_REF_PREFIX.rstrip("/")], cwd=cwd)
        for ref in out.splitlines():
            if ref.strip():
                gs.git(["update-ref", "-d", ref.strip()], cwd=cwd)
        gs.git(["config", "sc-gh-stack.conversion", conv_id], cwd=cwd)


def _check_remote_freshness(layer: str, remote: str, cwd: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Refuse to chain a local branch missing remote commits; ff if merely behind.

    A layer already adopted by this conversion (orig ref recorded and the branch
    tip has moved off it) is judged against its recorded pre-rebase tip instead:
    the rebase rewrote local history, so plain ancestry against the remote no
    longer means anything — but any commit the remote gained AFTER adoption
    shows up as the remote tip no longer being an ancestor of the recorded tip.
    Returns a failure dict, or None when the layer is safe to chain.
    """
    if not gs.remote_branch_exists(remote, layer, cwd=cwd):
        return None
    remote_ref = f"{remote}/{layer}"
    orig = _orig_tip(layer, cwd=cwd)
    adopted = orig is not None and orig != _rev(_head(layer), cwd=cwd)
    if adopted:
        # Safe when the remote gained nothing since adoption (ancestor of the
        # recorded tip) OR the local tip already contains every remote commit —
        # the post-submit state, and the state after the documented reconcile
        # (`git rebase <remote>/<layer>`), both of which must pass.
        if gs.is_ancestor(remote_ref, orig, cwd=cwd) \
                or gs.is_ancestor(remote_ref, _head(layer), cwd=cwd):
            return None
    elif gs.is_ancestor(remote_ref, _head(layer), cwd=cwd):
        return None
    elif gs.is_ancestor(_head(layer), remote_ref, cwd=cwd):
        ff = _fast_forward(layer, remote_ref, cwd=cwd)
        if ff.returncode == 0:
            return None
        return {"code": "CONVERT.FF_FAILED", "exit": EXIT_ERR, "layer": layer,
                "message": f"could not fast-forward {layer} to {remote_ref}: {ff.stderr.strip()}",
                "action": "inspect the branch state (is it checked out in another worktree?) and re-run"}
    return {"code": "GIT.BRANCH_DIVERGED", "exit": EXIT_INPUT, "layer": layer,
            "message": f"{layer} and {remote_ref} have diverged; converting the "
                       f"local branch would drop the remote's commits on submit",
            "action": f"reconcile first (e.g. `git checkout {layer} && git rebase "
                      f"{remote_ref}`) — do not push afterwards — then re-run"}


def chain(layers: List[str], trunk_ref: str, remote: str, cwd: Optional[Path] = None) -> ChainResult:
    """Rebase each layer onto the one below, bottom-up. Stops at the first conflict.

    Every layer passes the remote-freshness guard BEFORE the skip test, so a
    branch the remote has advanced can never be silently skipped. Skip rule: a
    layer is already chained only if the layer below is its ancestor AND no
    merge commits sit between them (a merge from trunk — GitHub's "Update
    branch" — must be linearised, not kept).

    Upstream bound per rebase, most exact first: the below layer's recorded
    pre-rebase tip (if this layer descends from it), the below layer's current
    tip (merge-flattening case), else trunk_ref. A stale local trunk can never
    be used: trunk_ref is always the remote trunk tip.
    """
    result = ChainResult()
    below = trunk_ref            # commit-ish the current layer must sit on
    below_name: Optional[str] = None
    for layer in layers:
        result.failure = _check_remote_freshness(layer, remote, cwd)
        if result.failure:
            return result

        layer_ref = _head(layer)
        if gs.is_ancestor(below, layer_ref, cwd=cwd) and not _has_merges(below, layer_ref, cwd=cwd):
            result.chained.append({"branch": layer, "onto": below if below_name is None else below_name,
                                   "action": "skip"})
            below, below_name = layer_ref, layer
            continue

        upstream = trunk_ref
        if below_name is not None:
            orig_below = _orig_tip(below_name, cwd=cwd)
            if orig_below and gs.is_ancestor(orig_below, layer_ref, cwd=cwd):
                upstream = orig_below
            elif gs.is_ancestor(below, layer_ref, cwd=cwd):
                upstream = below
            else:
                # Layer cut from an OLDER tip of the layer below: bound the
                # rebase at the fork point so the below layer's shared commits
                # are never re-replayed. Degenerates to the trunk fork point
                # (same replay set as trunk_ref) for layers cut from trunk.
                fork = gs.git_out(["merge-base", orig_below or below, layer_ref], cwd=cwd)
                if fork:
                    upstream = fork
        if _orig_tip(layer, cwd=cwd) is None:
            gs.git(["update-ref", _orig_ref(layer), layer_ref], cwd=cwd)

        rebase_cmd = ["rebase", "--onto", below, upstream, layer]
        rebase = gs.git(rebase_cmd, cwd=cwd)
        onto_label = below if below_name is None else below_name
        if rebase.returncode != 0:
            cmd_str = "git " + " ".join(rebase_cmd)
            if gs.rebase_in_progress(cwd=cwd):
                # Unmerged paths may be empty when rerere.autoUpdate already
                # staged every resolution; the rebase still awaits --continue.
                result.conflict = {"layer": layer, "onto": onto_label, "cmd": cmd_str,
                                   "files": gs.conflicted_files(cwd=cwd)}
            else:
                result.failure = {"code": "CONVERT.REBASE_FAILED", "exit": EXIT_ERR, "layer": layer,
                                  "cmd": cmd_str,
                                  "message": f"rebase of {layer} failed without a conflict: "
                                             f"{rebase.stderr.strip()}",
                                  "action": "fix the reported problem (is the branch checked out in "
                                            "another worktree?) and re-run; finished layers are skipped"}
            return result
        action = "rebased"
        if gs.git_out(["rev-list", f"{below}..{layer_ref}"], cwd=cwd) == "":
            action = "rebased_empty"   # only merge commits were flattened away — verify no content was lost
        result.chained.append({"branch": layer, "onto": onto_label, "action": action})
        below, below_name = layer_ref, layer
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
    init_cmd = ["stack", "init", "--base", trunk, *layers]
    init = gs.gh(init_cmd, cwd=cwd)
    if init.returncode != 0:
        return {"action": "init_failed", "cmd": "gh " + " ".join(init_cmd),
                "exit_code": init.returncode, "stderr": init.stderr.strip()}
    return {"action": "initialised"}


def convert(trunk: str, raw_layers: List[str], cwd: Optional[Path] = None) -> tuple[int, Dict[str, Any]]:
    """Full workflow. Returns (exit_code, envelope). Testable without argparse."""
    def fail(code: int, err_code: str, msg: str, action: str,
             data: Optional[Dict[str, Any]] = None, recoverable: bool = True):
        # recoverable means: apply suggested_action, re-run, and it succeeds by
        # design (finished layers are skipped). Input/repo errors are not — a
        # bare retry with unchanged inputs cannot fix them.
        return code, gs.envelope(False, data, gs.error_obj(err_code, msg, recoverable, action))

    if len(raw_layers) < 2:
        return fail(EXIT_INPUT, "VALIDATION.INPUT", "a stack needs at least two layers",
                    "pass <trunk> <bottom> ... <top>, bottom to top", recoverable=False)

    if not gs.in_git_repo(cwd=cwd):
        return fail(EXIT_INPUT, "GIT.NOT_A_REPO", "not inside a git repository",
                    "cd into the repository (or pass --cwd)", recoverable=False)
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
    # autoUpdate stages rerere's replayed resolutions, so a fully-rerere-resolved
    # stop reports conflict.files == [] and needs only `git rebase --continue`.
    gs.git(["config", "rerere.autoUpdate", "true"], cwd=cwd)
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
        return fail(EXIT_INPUT, "VALIDATION.INPUT", str(exc), "fix the layer list and re-run",
                    recoverable=False)

    before = {b: _rev(_head(b), cwd=cwd) for b in layers}
    base = {"trunk": trunk, "remote": remote, "layers": layers, "shape": stack_shape(trunk, layers)}
    begin_conversion(trunk, layers, cwd=cwd)
    result = chain(layers, trunk_ref, remote, cwd=cwd)
    base["branches"] = branch_states(layers, remote, before, cwd=cwd)
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

    init = init_stack(trunk, layers, cwd=cwd)
    data = {**base, "chained": result.chained, "conflict": None, "stack_init": init}
    if init["action"] == "init_failed":
        data["next_step"] = "read data.stack_init.stderr, fix the reported problem (is the top " \
                            "branch checked out in another worktree?), and re-run; " \
                            "chained layers are skipped — do NOT run `gh stack submit`"
        return fail(EXIT_ERR, "STACK.INIT_FAILED", "gh stack init failed", data["next_step"], data)
    data["next_step"] = "review `gh stack view --json` (all layers, given order, needsRebase=false), " \
                        "then `gh stack submit --auto`"
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
