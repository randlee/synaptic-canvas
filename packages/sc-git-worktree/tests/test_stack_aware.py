"""Stack-aware behaviour: gh-stack layer worktrees.

Real git repositories (a bare origin plus a clone) exercise the create script's
stack mode, the --no-track fix, the cleanup/abort stack guards, and the scan
issues for layers whose parent moved or landed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from worktree_shared import (  # noqa: E402
    TrackingEntry,
    find_stack_children,
    is_landed_by_merge,
    load_tracking_jsonl,
)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def run_script(name, payload=None, *, cwd, args=()):
    cmd = [sys.executable, str(SCRIPTS / name)]
    if payload is not None:
        cmd.append(json.dumps(payload))
    cmd.extend(args)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    text = proc.stdout
    body = text[text.find("{"): text.rfind("}") + 1]
    assert body, f"no JSON in output:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    return json.loads(body)


@pytest.fixture
def stack_repo(tmp_path):
    """origin with develop (trunk) and a pushed layer l1 on top of it."""
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    git("init", "-q", "--bare", str(origin), cwd=tmp_path)
    git("clone", "-q", str(origin), str(repo), cwd=tmp_path)
    git("config", "user.email", "t@t", cwd=repo)
    git("config", "user.name", "t", cwd=repo)
    (repo / "a").write_text("a\n")
    git("add", "a", cwd=repo)
    git("commit", "-qm", "base", cwd=repo)
    git("branch", "-M", "develop", cwd=repo)
    git("push", "-q", "-u", "origin", "develop", cwd=repo)
    git("checkout", "-qb", "l1", cwd=repo)
    (repo / "l1").write_text("l1\n")
    git("add", "l1", cwd=repo)
    git("commit", "-qm", "l1", cwd=repo)
    git("push", "-q", "-u", "origin", "l1", cwd=repo)
    git("checkout", "-q", "develop", cwd=repo)
    (repo / ".sc").mkdir()
    (repo / ".sc" / "shared-settings.yaml").write_text("git:\n  protected_branches:\n    - develop\n")
    return repo


def create(repo, branch, base, stack=None, **extra):
    payload = {"branch": branch, "base": base, "purpose": f"work on {branch}", "owner": "t", "repo_root": str(repo)}
    if stack is not None:
        payload["stack"] = stack
    payload.update(extra)
    return run_script("worktree_create.py", payload, cwd=repo)


def upstream(worktree):
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=worktree, capture_output=True, text=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def tracking_path(repo):
    return repo.parent / f"{repo.name}-worktrees" / "worktree-tracking.jsonl"


# =============================================================================
# Create: stack mode
# =============================================================================


class TestStackCreate:
    def test_cut_from_pushed_parent_without_upstream(self, stack_repo):
        # Make the local l1 ref stale so a local-ref cut would be wrong
        git("branch", "-f", "l1", "develop", cwd=stack_repo)
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        assert result["success"], result
        data = result["data"]
        wt = Path(data["path"])
        assert git("rev-parse", "HEAD", cwd=wt) == git("rev-parse", "origin/l1", cwd=stack_repo)
        assert upstream(wt) is None, "a layer must not track its parent"
        assert data["stack"] == {
            "trunk": "develop",
            "parent": "l1",
            "parent_sha": git("rev-parse", "origin/l1", cwd=stack_repo),
            "above": None,
            "position": "top",
        }
        handoff = data["stack_handoff"]
        assert handoff["pr_base"] == "l1"
        assert handoff["commands"][0] == f"git -C {wt} push -u origin l2"
        assert "--base l1 --head l2" in handoff["commands"][1]
        assert any(cmd.startswith("gh stack link <stack#> <pr# of l2>") for cmd in handoff["commands"])
        assert any("gh stack link --base develop <bottom-pr#> ... <pr# of l1> <pr# of l2>" in c for c in handoff["commands"])
        assert handoff["commands"][-1] == "/sc-gh-stack-view"
        assert any("rebase --onto origin/l1" in rule for rule in handoff["rules"])
        # Tracking row carries the stack metadata
        entries = load_tracking_jsonl(tracking_path(stack_repo))
        assert entries[0].stack["parent_sha"] == data["stack"]["parent_sha"]

    def test_bottom_layer_handoff_has_nothing_below(self, stack_repo):
        result = create(stack_repo, "l0", "develop", stack={"trunk": "develop"})
        assert result["success"], result
        cmds = result["data"]["stack_handoff"]["commands"]
        assert "gh stack link --base develop <pr# of l0>   # first link, or full relink" in cmds
        assert not any("pr# of develop" in c for c in cmds)

    def test_insert_handoff(self, stack_repo):
        result = create(stack_repo, "l1b", "develop", stack={"trunk": "develop", "above": "l1"})
        assert result["success"], result
        data = result["data"]
        assert data["stack"]["position"] == "insert"
        cmds = data["stack_handoff"]["commands"]
        assert any("merge --no-ff origin/l1b" in c for c in cmds)
        assert "gh pr edit <pr# of l1> --base l1b" in cmds
        assert any(c.startswith("gh stack unstack <stack#>") for c in cmds)
        assert any("gh stack link --base develop <pr# of l1b> <pr# of l1> ... <top-pr#>" in c for c in cmds)
        assert data["stack_handoff"]["reference"].endswith("(insert)")

    def test_chain_check_command_only_when_installed(self, stack_repo):
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        assert not result["data"]["stack_handoff"]["chain_check_available"]
        assert not any("gh_stack_chain_check" in c for c in result["data"]["stack_handoff"]["commands"])
        (stack_repo / ".claude" / "scripts").mkdir(parents=True)
        (stack_repo / ".claude" / "scripts" / "gh_stack_chain_check.py").write_text("# stub\n")
        result = create(stack_repo, "l3", "l1", stack={"trunk": "develop"})
        handoff = result["data"]["stack_handoff"]
        assert handoff["chain_check_available"]
        assert any("gh_stack_chain_check.py --trunk develop <bottom> ... l1 l3" in c for c in handoff["commands"])

    def test_parent_behind_trunk_is_a_note_not_a_block(self, stack_repo):
        # Trunk moves on after l1 was cut: allowed, recorded in the transcript
        git("commit", "-q", "--allow-empty", "-m", "trunk moves", cwd=stack_repo)
        git("push", "-q", "origin", "develop", cwd=stack_repo)
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        assert result["success"], result
        steps = " ".join(s.get("message", "") or "" for s in result["metadata"]["transcript"])
        assert "parent behind trunk by 1 commit(s)" in steps


class TestStackCreateRefusals:
    def test_layer_must_be_new(self, stack_repo):
        git("branch", "-q", "l2", "l1", cwd=stack_repo)
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        assert not result["success"]
        assert result["error"]["code"] == "STACK.LAYER_EXISTS"
        assert "omit `stack`" in result["error"]["suggested_action"]

    def test_parent_must_be_pushed(self, stack_repo):
        git("branch", "-q", "local-only", "l1", cwd=stack_repo)
        result = create(stack_repo, "l2", "local-only", stack={"trunk": "develop"})
        assert result["error"]["code"] == "STACK.PARENT_NOT_PUSHED"
        assert "git push -u origin local-only" in result["error"]["suggested_action"]
        assert not (stack_repo.parent / "repo-worktrees" / "l2").exists()

    def test_trunk_must_exist(self, stack_repo):
        result = create(stack_repo, "l2", "l1", stack={"trunk": "nope"})
        assert result["error"]["code"] == "BRANCH.NOT_FOUND"
        assert "stack.trunk" in result["error"]["suggested_action"]

    def test_landed_parent_refused(self, stack_repo):
        git("merge", "-q", "--no-ff", "-m", "land l1", "l1", cwd=stack_repo)
        git("push", "-q", "origin", "develop", cwd=stack_repo)
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        assert result["error"]["code"] == "STACK.PARENT_LANDED"
        assert "/sc-gh-stack-view" in result["error"]["suggested_action"]

    def test_above_must_contain_parent(self, stack_repo):
        git("branch", "-q", "other", "develop", cwd=stack_repo)
        git("push", "-q", "origin", "other", cwd=stack_repo)
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop", "above": "other"})
        assert result["error"]["code"] == "STACK.ABOVE_INVALID"
        assert "does not contain origin/l1" in result["error"]["message"]

    def test_above_must_be_pushed(self, stack_repo):
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop", "above": "ghost"})
        assert result["error"]["code"] == "STACK.ABOVE_INVALID"
        assert "not on origin" in result["error"]["message"]

    def test_above_cannot_be_parent_or_self(self, stack_repo):
        result = create(stack_repo, "l2", "l1", stack={"trunk": "develop", "above": "l1"})
        assert result["error"]["code"] == "STACK.ABOVE_INVALID"

    def test_empty_trunk_rejected_at_input(self, stack_repo):
        result = create(stack_repo, "l2", "l1", stack={"trunk": "  "})
        assert not result["success"]
        assert result["error"]["code"] == "CONFIG.MISSING"


class TestPlainCreateNoTrack:
    def test_remote_only_base_does_not_become_upstream(self, stack_repo):
        git("branch", "-q", "-D", "l1", cwd=stack_repo)
        result = create(stack_repo, "feature/x", "l1")
        assert result["success"], result
        assert upstream(Path(result["data"]["path"])) is None
        assert "stack" not in result["data"]
        assert load_tracking_jsonl(tracking_path(stack_repo))[0].stack is None

    def test_local_base_still_used_in_plain_mode(self, stack_repo):
        git("branch", "-f", "l1", "develop", cwd=stack_repo)  # stale local ref
        result = create(stack_repo, "feature/y", "l1")
        assert result["success"], result
        assert git("rev-parse", "HEAD", cwd=Path(result["data"]["path"])) == git("rev-parse", "develop", cwd=stack_repo)


# =============================================================================
# Tracking schema
# =============================================================================


class TestTrackingStackField:
    def test_entry_without_stack_loads(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            '{"branch":"f","path":"/p","base":"main","owner":"o","created":"2024-01-01T00:00:00Z","last_checked":"2024-01-01T00:00:00Z"}\n'
        )
        entries = load_tracking_jsonl(p)
        assert entries[0].stack is None

    def test_find_stack_children_only_live(self):
        def entry(branch, parent=None, local=True, remote=False):
            return TrackingEntry(
                branch=branch, path="/p", base=parent or "main", owner="o",
                created="2024-01-01T00:00:00Z", last_checked="2024-01-01T00:00:00Z",
                local_worktree=local, remote_exists=remote,
                stack={"trunk": "main", "parent": parent, "parent_sha": "x", "above": None, "position": "top"} if parent else None,
            )
        entries = [
            entry("l1"),
            entry("l2", parent="l1"),
            entry("l3", parent="l1", local=False, remote=True),
            entry("gone", parent="l1", local=False, remote=False),
            entry("l4", parent="l2"),
        ]
        assert find_stack_children(entries, "l1") == ["l2", "l3"]
        assert find_stack_children(entries, "l2") == ["l4"]
        assert find_stack_children(entries, "l4") == []


class TestLandedByMerge:
    def test_empty_branch_on_trunk_is_not_landed(self, stack_repo):
        git("branch", "-q", "empty", "develop", cwd=stack_repo)
        assert not is_landed_by_merge("empty", "develop", cwd=stack_repo)

    def test_unmerged_layer_is_not_landed(self, stack_repo):
        assert not is_landed_by_merge("l1", "develop", cwd=stack_repo)

    def test_merge_commit_landing_is_landed(self, stack_repo):
        git("merge", "-q", "--no-ff", "-m", "land l1", "l1", cwd=stack_repo)
        assert is_landed_by_merge("l1", "develop", cwd=stack_repo)

    def test_fast_forward_is_not_landed(self, stack_repo):
        # A fast-forward puts the layer head on the trunk's first-parent line: indistinguishable
        # from an empty branch, so it is treated as not landed (fails closed).
        git("merge", "-q", "--ff-only", "l1", cwd=stack_repo)
        assert not is_landed_by_merge("l1", "develop", cwd=stack_repo)

    def test_unknown_branch(self, stack_repo):
        assert not is_landed_by_merge("ghost", "develop", cwd=stack_repo)


# =============================================================================
# Cleanup / abort guards
# =============================================================================


class TestStackGuards:
    @pytest.fixture
    def layered(self, stack_repo):
        """l1 has a worktree; l2 is a live layer cut from l1."""
        create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        git("worktree", "add", "-q", str(stack_repo.parent / "repo-worktrees" / "l1"), "l1", cwd=stack_repo)
        return stack_repo

    def test_abort_refuses_to_delete_parent(self, layered):
        result = run_script(
            "worktree_abort.py", {"branch": "l1", "allow_delete_branch": True, "repo_root": str(layered)}, cwd=layered
        )
        assert result["error"]["code"] == "STACK.HAS_CHILDREN"
        assert result["error"]["data"]["stack_children"] == ["l2"] if "data" in result["error"] else True
        assert (layered.parent / "repo-worktrees" / "l1").exists(), "nothing may be mutated before the guard"
        assert git("rev-parse", "--verify", "l1", cwd=layered)

    def test_abort_without_delete_removes_worktree_only(self, layered):
        result = run_script("worktree_abort.py", {"branch": "l1", "repo_root": str(layered)}, cwd=layered)
        assert result["success"], result
        assert result["data"]["branch_deleted_local"] is False

    def test_cleanup_override_refused(self, layered):
        result = run_script(
            "worktree_cleanup.py", {"branch": "l1", "merged": True, "repo_root": str(layered)}, cwd=layered
        )
        assert result["error"]["code"] == "STACK.HAS_CHILDREN"
        assert "gh stack merge" in result["error"]["suggested_action"]
        assert (layered.parent / "repo-worktrees" / "l1").exists()

    def test_cleanup_after_real_landing_is_allowed(self, layered):
        git("merge", "-q", "--no-ff", "-m", "land l1", "l1", cwd=layered)
        git("push", "-q", "origin", "develop", cwd=layered)
        result = run_script("worktree_cleanup.py", {"branch": "l1", "repo_root": str(layered)}, cwd=layered)
        assert result["success"], result
        assert result["data"]["branch_deleted_local"] is True

    def test_batch_cleanup_blocks_fast_forwarded_parent(self, layered):
        # A fast-forward puts l1's head on the trunk's first-parent line, which git cannot
        # tell apart from an empty branch: batch cleanup must fail closed while l2 is live.
        git("merge", "-q", "--ff-only", "l1", cwd=layered)
        git("push", "-q", "origin", "develop", cwd=layered)
        run_script("worktree_scan.py", cwd=layered, args=("--no-cache",))  # register l1's worktree
        result = run_script("worktree_cleanup.py", {"repo_root": str(layered)}, cwd=layered)
        assert result["success"], result
        blocked = {b["branch"]: b for b in (result["data"]["stack_blocked"] or [])}
        assert "l1" in blocked and blocked["l1"]["stack_children"] == ["l2"]
        assert "l1" not in {c["branch"] for c in result["data"]["cleaned"]}
        assert git("rev-parse", "--verify", "l1", cwd=layered)
        assert result["data"]["summary"]["stack_blocked"] == 1

    def test_batch_cleanup_cleans_parent_landed_by_merge(self, layered):
        git("merge", "-q", "--no-ff", "-m", "land l1", "l1", cwd=layered)
        git("push", "-q", "origin", "develop", cwd=layered)
        run_script("worktree_scan.py", cwd=layered, args=("--no-cache",))
        result = run_script("worktree_cleanup.py", {"repo_root": str(layered)}, cwd=layered)
        assert result["success"], result
        assert "l1" in {c["branch"] for c in result["data"]["cleaned"]}
        assert not result["data"]["stack_blocked"]
        # l2 has no commits of its own, so once l1 landed it is an empty worktree and is
        # swept by the pre-existing empty-branch rule; nothing stack-specific applies.

    def test_empty_parent_cannot_get_children(self, stack_repo):
        # The scenario the guard would otherwise need: a pushed empty branch as a parent.
        git("branch", "-q", "empty", "develop", cwd=stack_repo)
        git("push", "-q", "origin", "empty", cwd=stack_repo)
        result = create(stack_repo, "child", "empty", stack={"trunk": "develop"})
        assert result["error"]["code"] == "STACK.PARENT_LANDED"


# =============================================================================
# Scan
# =============================================================================


class TestScanStackIssues:
    def test_parent_advanced(self, stack_repo):
        create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        git("worktree", "add", "-q", str(stack_repo.parent / "repo-worktrees" / "l1"), "l1", cwd=stack_repo)
        wt1 = stack_repo.parent / "repo-worktrees" / "l1"
        git("commit", "-q", "--allow-empty", "-m", "more", cwd=wt1)
        git("push", "-q", "origin", "l1", cwd=wt1)
        result = run_script("worktree_scan.py", cwd=stack_repo, args=("--no-cache",))
        l2 = next(w for w in result["data"]["worktrees"] if w["branch"] == "l2")
        assert any(i.startswith("stack_parent_advanced: origin/l1") for i in l2["issues"])
        assert l2["tracking_entry"]["stack"]["parent"] == "l1"
        assert any("rebases once at task start" in r for r in result["data"]["recommendations"])

    def test_parent_landed(self, stack_repo):
        create(stack_repo, "l2", "l1", stack={"trunk": "develop"})
        git("merge", "-q", "--no-ff", "-m", "land l1", "l1", cwd=stack_repo)
        git("push", "-q", "origin", "develop", cwd=stack_repo)
        result = run_script("worktree_scan.py", cwd=stack_repo, args=("--no-cache",))
        l2 = next(w for w in result["data"]["worktrees"] if w["branch"] == "l2")
        assert "stack_parent_landed: l1 is contained in develop" in l2["issues"]

    def test_bottom_layer_has_no_stack_issue_when_trunk_moves(self, stack_repo):
        create(stack_repo, "l0", "develop", stack={"trunk": "develop"})
        git("commit", "-q", "--allow-empty", "-m", "trunk moves", cwd=stack_repo)
        git("push", "-q", "origin", "develop", cwd=stack_repo)
        result = run_script("worktree_scan.py", cwd=stack_repo, args=("--no-cache",))
        l0 = next(w for w in result["data"]["worktrees"] if w["branch"] == "l0")
        assert not any(i.startswith("stack_") for i in (l0["issues"] or []))
