"""Unit tests for gh_stack_sync (gh/git mocked; sync itself needs a live stack)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from subprocess import CompletedProcess

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import gh_stack_shared as gs  # noqa: E402
import gh_stack_sync as sy  # noqa: E402


def cp(returncode=0, stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


VIEW = json.dumps({"trunk": "main", "branches": [{"name": "l1"}, {"name": "l2"}]})


@pytest.fixture
def healthy(monkeypatch):
    monkeypatch.setattr(gs, "in_git_repo", lambda cwd=None: True)
    monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: False)
    monkeypatch.setattr(gs, "working_tree_clean", lambda cwd=None: True)
    monkeypatch.setattr(gs, "resolve_remote", lambda cwd=None: "origin")


def _gh(view_rc=0, view_out=VIEW, sync_rc=0, sync_err="", sync_out=""):
    def fake_gh(args, cwd=None):
        if args[:2] == ["stack", "view"]:
            return cp(view_rc, view_out)
        if args[:2] == ["stack", "sync"]:
            return cp(sync_rc, sync_out, sync_err)
        return cp(0)
    return fake_gh


def _shas(shas):
    """git_out returning per-ref shas; refs/heads/<b> and refs/remotes/origin/<b>."""
    def fake(args, cwd=None):
        return shas.get(args[-1], "")
    return fake


class TestSync:
    def test_success_reports_pushed_branches(self, healthy, monkeypatch):
        monkeypatch.setattr(gs, "gh", _gh())
        monkeypatch.setattr(gs, "git_out", _shas({
            "refs/heads/l1": "aaa", "refs/remotes/origin/l1": "aaa",
            "refs/heads/l2": "bbb", "refs/remotes/origin/l2": "bbb"}))
        code, env = sy.sync()
        assert code == sy.EXIT_OK and env["success"] is True
        assert [(b["name"], b["pushed"]) for b in env["data"]["branches"]] == [("l1", True), ("l2", True)]
        assert env["data"]["next_step"] is None

    def test_conflict_reports_restored_state(self, healthy, monkeypatch):
        monkeypatch.setattr(gs, "gh", _gh(sync_rc=3, sync_err="conflict in l2"))
        monkeypatch.setattr(gs, "git_out", _shas({
            "refs/heads/l1": "aaa", "refs/remotes/origin/l1": "aaa",
            "refs/heads/l2": "bbb", "refs/remotes/origin/l2": "ccc"}))
        code, env = sy.sync()
        assert code == sy.EXIT_CONFLICT
        assert env["error"]["code"] == "SYNC.CONFLICT"
        assert "conflict in l2" in env["error"]["message"]
        assert "gh stack rebase" in env["error"]["suggested_action"]
        # Per-branch state is present even on failure (forensic contract).
        assert [b["name"] for b in env["data"]["branches"]] == ["l1", "l2"]
        assert env["data"]["branches"][1]["pushed"] is False

    def test_divergence_abort_with_exit_0_is_not_success(self, healthy, monkeypatch):
        # Non-interactive `gh stack sync` on a diverged local/remote stack
        # prints "Sync aborted" and exits 0 WITHOUT syncing anything
        # (troubleshooting.md). Exit 0 alone must not be reported as synced.
        monkeypatch.setattr(gs, "gh", _gh(
            sync_rc=0, sync_out="local:  l1 <- l2\nremote: l1 <- l3\nSync aborted\n"))
        monkeypatch.setattr(gs, "git_out", _shas({
            "refs/heads/l1": "aaa", "refs/remotes/origin/l1": "aaa",
            "refs/heads/l2": "bbb", "refs/remotes/origin/l2": "ccc"}))
        code, env = sy.sync()
        assert code == sy.EXIT_INPUT and env["success"] is False
        assert env["error"]["code"] == "SYNC.ABORTED"
        assert env["error"]["recoverable"] is False
        assert "diverged" in env["error"]["message"]
        assert "unstack --local" in env["error"]["suggested_action"]
        # Forensic contract still holds: per-branch state present.
        assert [b["name"] for b in env["data"]["branches"]] == ["l1", "l2"]

    def test_abort_detection_checks_stderr_too(self, healthy, monkeypatch):
        monkeypatch.setattr(gs, "gh", _gh(sync_rc=0, sync_err="Sync aborted\n"))
        monkeypatch.setattr(gs, "git_out", _shas({}))
        code, env = sy.sync()
        assert code == sy.EXIT_INPUT and env["error"]["code"] == "SYNC.ABORTED"

    def test_other_failure_carries_stderr(self, healthy, monkeypatch):
        monkeypatch.setattr(gs, "gh", _gh(sync_rc=1, sync_err="network down"))
        monkeypatch.setattr(gs, "git_out", _shas({}))
        code, env = sy.sync()
        assert code == sy.EXIT_ERR
        assert env["error"]["code"] == "SYNC.FAILED"
        assert "network down" in env["error"]["message"]

    def test_no_stack_here(self, healthy, monkeypatch):
        monkeypatch.setattr(gs, "gh", _gh(view_rc=2, view_out=""))
        code, env = sy.sync()
        assert code == sy.EXIT_INPUT and env["error"]["code"] == "SYNC.NO_STACK"

    def test_guards(self, monkeypatch):
        monkeypatch.setattr(gs, "in_git_repo", lambda cwd=None: True)
        monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: True)
        code, env = sy.sync()
        assert code == sy.EXIT_INPUT and env["error"]["code"] == "GIT.REBASE_IN_PROGRESS"
        monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: False)
        monkeypatch.setattr(gs, "working_tree_clean", lambda cwd=None: False)
        code, env = sy.sync()
        assert code == sy.EXIT_INPUT and env["error"]["code"] == "GIT.DIRTY_TREE"

    def test_main_emits_fenced_json(self, healthy, monkeypatch, capsys):
        monkeypatch.setattr(gs, "gh", _gh())
        monkeypatch.setattr(gs, "git_out", _shas({}))
        rc = sy.main([])
        out = capsys.readouterr().out
        assert rc == 0
        payload = json.loads(out.split("```json")[1].split("```")[0])
        assert payload["success"] is True
