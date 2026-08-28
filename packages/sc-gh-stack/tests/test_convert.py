"""Tests for gh_stack_convert: unit tests with mocked git/gh, plus real-git integration tests."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import gh_stack_convert as cv  # noqa: E402
import gh_stack_shared as gs  # noqa: E402


def cp(returncode=0, stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def clean_repo_guards(monkeypatch):
    """Make convert()'s repo-state guards pass without touching a real repository."""
    monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: False)
    monkeypatch.setattr(gs, "working_tree_clean", lambda cwd=None: True)


class TestResolveLayers:
    def test_branch_names_pass_through(self):
        assert cv.resolve_layers(["a", "b"]) == ["a", "b"]

    def test_pr_numbers_resolved(self):
        with patch.object(gs, "resolve_pr_branch", side_effect=lambda n, cwd=None: f"pr-{n}"):
            assert cv.resolve_layers(["101", "feat/x", "102"]) == ["pr-101", "feat/x", "pr-102"]

    def test_unresolvable_pr_raises(self):
        with patch.object(gs, "resolve_pr_branch", return_value=None):
            with pytest.raises(ValueError, match="cannot resolve PR #7"):
                cv.resolve_layers(["7", "b"])

    def test_duplicates_raise(self):
        with pytest.raises(ValueError, match="duplicate"):
            cv.resolve_layers(["a", "a"])


class TestConvertValidation:
    def test_requires_two_layers(self):
        code, env = cv.convert("main", ["only"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "VALIDATION.INPUT"

    def test_rebase_in_progress_fails_early(self, monkeypatch):
        monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: True)
        code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.REBASE_IN_PROGRESS"

    def test_dirty_tree_fails_early(self, monkeypatch):
        monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: False)
        monkeypatch.setattr(gs, "working_tree_clean", lambda cwd=None: False)
        code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.DIRTY_TREE"

    def test_no_remote(self, clean_repo_guards):
        with patch.object(gs, "remotes", return_value=[]):
            code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.REMOTE"

    def test_two_remotes_without_push_default(self, clean_repo_guards):
        with patch.object(gs, "remotes", return_value=["origin", "upstream"]), \
             patch.object(gs, "config_get", return_value=""):
            code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.REMOTE"
        assert "remote.pushDefault" in env["error"]["suggested_action"]

    def test_trunk_missing_on_remote(self, clean_repo_guards):
        with patch.object(gs, "remotes", return_value=["origin"]), \
             patch.object(gs, "git", return_value=cp(0)), \
             patch.object(gs, "remote_branch_exists", return_value=False):
            code, env = cv.convert("nope", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.TRUNK_NOT_FOUND"

    def test_trunk_as_layer_is_input_error(self, clean_repo_guards):
        with patch.object(gs, "remotes", return_value=["origin"]), \
             patch.object(gs, "git", return_value=cp(0)), \
             patch.object(gs, "remote_branch_exists", return_value=True):
            code, env = cv.convert("main", ["a", "main"])
        assert code == cv.EXIT_INPUT and "layer equals trunk" in env["error"]["message"]

    def test_fetch_failure_is_exit_1(self, clean_repo_guards):
        def fake_git(args, cwd=None):
            return cp(128, "", "could not resolve host") if args[0] == "fetch" else cp(0)

        with patch.object(gs, "remotes", return_value=["origin"]), patch.object(gs, "git", fake_git):
            code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_ERR and env["error"]["code"] == "GIT.FETCH"
        assert env["error"]["recoverable"] is False

    def test_init_stack_keeps_existing_stack(self):
        with patch.object(gs, "git", return_value=cp(0)), patch.object(gs, "gh", return_value=cp(0, "{}")):
            assert cv.init_stack("main", ["a", "b"])["action"] == "existing_stack_kept"

    def test_init_stack_calls_init_with_ordered_layers(self):
        gh_calls = []

        def fake_gh(args, cwd=None):
            gh_calls.append(args)
            return cp(2) if args[:2] == ["stack", "view"] else cp(0)

        with patch.object(gs, "git", return_value=cp(0)), patch.object(gs, "gh", fake_gh):
            assert cv.init_stack("main", ["a", "b", "c"])["action"] == "initialised"
        assert gh_calls[-1] == ["stack", "init", "--base", "main", "a", "b", "c"]

    def test_init_stack_surfaces_failed_checkout(self):
        with patch.object(gs, "git", return_value=cp(1, "", "would be overwritten")), \
             patch.object(gs, "gh", return_value=cp(0, "{}")):
            r = cv.init_stack("main", ["a", "b"])
        assert r["action"] == "init_failed" and r["stderr"] == "would be overwritten"

    def test_init_failure_is_stack_init_failed(self, clean_repo_guards):
        def fake_gh(args, cwd=None):
            if args[:2] == ["stack", "view"]:
                return cp(2)
            if args[:2] == ["stack", "init"]:
                return cp(1, "", "stack init boom")
            return cp(0)

        with patch.object(gs, "remotes", return_value=["origin"]), \
             patch.object(gs, "git", return_value=cp(0)), \
             patch.object(gs, "git_out", return_value=""), \
             patch.object(gs, "remote_branch_exists", return_value=True), \
             patch.object(gs, "local_branch_exists", return_value=True), \
             patch.object(gs, "is_ancestor", return_value=True), \
             patch.object(gs, "gh", fake_gh):
            code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_ERR
        assert env["error"]["code"] == "STACK.INIT_FAILED"
        assert env["data"]["stack_init"]["stderr"] == "stack init boom"


# --- integration: real git, stubbed gh -------------------------------------

def _sh(cwd, *args):
    return subprocess.run(list(args), cwd=cwd, check=True, capture_output=True, text=True).stdout


def _commit(cwd, name, content, msg):
    (cwd / name).write_text(content)
    _sh(cwd, "git", "add", ".")
    _sh(cwd, "git", "commit", "-q", "-m", msg)


GH_STUB = """#!/bin/sh
case "$*" in
  "stack view --json") exit 2;;
  "pr view 1 --json headRefName -q .headRefName") echo pr1;;
  "pr view 3 --json headRefName -q .headRefName") echo pr3;;
  *) echo "[stub gh $*]";;
esac
"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Bare origin + working clone with main and three parallel branches; pr1/pr2 conflict."""
    # Isolate from the developer's global/system git config (gpgsign, hooks, rerere, ...).
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    origin = tmp_path / "origin.git"
    _sh(tmp_path, "git", "init", "-q", "--bare", str(origin))
    work = tmp_path / "work"
    _sh(tmp_path, "git", "clone", "-q", str(origin), str(work))
    _sh(work, "git", "config", "user.email", "t@t")
    _sh(work, "git", "config", "user.name", "t")
    _commit(work, "base.txt", "base\n", "base")
    _sh(work, "git", "branch", "-M", "main")
    _sh(work, "git", "push", "-q", "origin", "main")
    for i in (1, 2, 3):
        _sh(work, "git", "checkout", "-qb", f"pr{i}", "main")
        _commit(work, f"l{i}.txt", f"layer {i}\n", f"layer {i}")
    _sh(work, "git", "checkout", "-q", "pr1")
    _commit(work, "shared.txt", "one\n", "pr1 shared")
    _sh(work, "git", "checkout", "-q", "pr2")
    _commit(work, "shared.txt", "two\n", "pr2 shared")
    for b in ("pr1", "pr2", "pr3"):
        _sh(work, "git", "push", "-q", "origin", b)
    _sh(work, "git", "checkout", "-q", "main")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "gh"
    stub.write_text(GH_STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GIT_EDITOR", "true")
    return work


def _orig_refs(repo):
    return _sh(repo, "git", "for-each-ref", "refs/sc-gh-stack/").strip()


class TestConvertIntegration:
    def test_conflict_resume_and_linear_chain(self, repo):
        # First run: pr1 already on trunk (skip), pr2 conflicts on shared.txt.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_CONFLICT
        assert env["error"]["code"] == "CONVERT.CONFLICT"
        assert env["data"]["conflict"] == {"layer": "pr2", "onto": "pr1", "files": ["shared.txt"]}
        assert [c["action"] for c in env["data"]["chained"]] == ["skip"]
        assert gs.rebase_in_progress(cwd=repo)

        # Re-running mid-rebase must refuse, not misattribute a conflict.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_INPUT
        assert env["error"]["code"] == "GIT.REBASE_IN_PROGRESS"

        # Resolve and continue the rebase the way the playbook instructs.
        (repo / "shared.txt").write_text("merged\n")
        _sh(repo, "git", "add", "shared.txt")
        _sh(repo, "git", "rebase", "--continue")

        # Second run is idempotent: pr1/pr2 skipped, pr3 rebased, stack initialised.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_OK, env
        assert [(c["branch"], c["action"]) for c in env["data"]["chained"]] == [
            ("pr1", "skip"), ("pr2", "skip"), ("pr3", "rebased")]
        assert env["data"]["stack_init"]["action"] == "initialised"
        assert env["data"]["shape"] == "(main) <- pr1 <- pr2 <- pr3"

        # Ancestry is a single linear chain, rerere was enabled, orig refs cleaned up.
        assert gs.is_ancestor("origin/main", "pr1", cwd=repo)
        assert gs.is_ancestor("pr1", "pr2", cwd=repo)
        assert gs.is_ancestor("pr2", "pr3", cwd=repo)
        assert gs.config_get("rerere.enabled", cwd=repo) == "true"
        assert _sh(repo, "git", "rev-parse", "--abbrev-ref", "HEAD").strip() == "pr3"
        assert _orig_refs(repo) == ""

        # Third run: everything skipped, stack already present.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_OK
        assert all(c["action"] == "skip" for c in env["data"]["chained"])

    def test_dirty_tree_refused_before_any_rebase(self, repo):
        (repo / "base.txt").write_text("edited\n")
        code, env = cv.convert("main", ["pr1", "pr3"], cwd=repo)
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.DIRTY_TREE"
        _sh(repo, "git", "checkout", "-q", "--", "base.txt")

    def test_dependent_layer_not_duplicated_after_conflict_resolution(self, repo):
        # dep is branched OFF pr1 (dependent-PR shape), adding its own commit.
        _sh(repo, "git", "checkout", "-qb", "dep", "pr1")
        _commit(repo, "dep.txt", "dep\n", "dep work")
        _sh(repo, "git", "push", "-q", "origin", "dep")
        # Trunk moves with a change conflicting with pr1's shared-file edit.
        _sh(repo, "git", "checkout", "-q", "main")
        _commit(repo, "shared.txt", "trunk\n", "trunk shared")
        _sh(repo, "git", "push", "-q", "origin", "main")
        _sh(repo, "git", "checkout", "-q", "main")

        # First run: pr1 conflicts against the moved trunk.
        code, env = cv.convert("main", ["pr1", "dep"], cwd=repo)
        assert code == cv.EXIT_CONFLICT
        assert env["data"]["conflict"]["layer"] == "pr1"
        (repo / "shared.txt").write_text("resolved\n")
        _sh(repo, "git", "add", "shared.txt")
        _sh(repo, "git", "rebase", "--continue")

        # Re-run: dep must replay ONLY its own commit on the rebased pr1 —
        # pr1's pre-rebase commits (recorded in refs/sc-gh-stack/orig/) are
        # excluded from the upstream bound, so nothing is duplicated.
        code, env = cv.convert("main", ["pr1", "dep"], cwd=repo)
        assert code == cv.EXIT_OK, env
        assert [(c["branch"], c["action"]) for c in env["data"]["chained"]] == [
            ("pr1", "skip"), ("dep", "rebased")]
        assert _sh(repo, "git", "rev-list", "--count", "pr1..dep").strip() == "1"
        assert (repo / "shared.txt").read_text() == "resolved\n"
        assert _orig_refs(repo) == ""

    def test_layer_with_trunk_merge_is_linearised(self, repo):
        # Trunk advances, then simulate GitHub's "Update branch": merge main into pr3.
        _sh(repo, "git", "checkout", "-q", "main")
        _commit(repo, "trunk.txt", "trunk\n", "trunk moves")
        _sh(repo, "git", "push", "-q", "origin", "main")
        _sh(repo, "git", "checkout", "-q", "pr3")
        _sh(repo, "git", "merge", "-q", "--no-edit", "main")
        assert _sh(repo, "git", "rev-list", "--merges", "main..pr3").strip() != ""
        _sh(repo, "git", "checkout", "-q", "main")
        code, env = cv.convert("main", ["pr1", "pr3"], cwd=repo)
        assert code == cv.EXIT_OK, env
        actions = {c["branch"]: c["action"] for c in env["data"]["chained"]}
        assert actions["pr3"] == "rebased"   # not skipped despite ancestry via the merge
        assert _sh(repo, "git", "rev-list", "--merges", "origin/main..pr3").strip() == ""
        assert gs.is_ancestor("pr1", "pr3", cwd=repo)

    def test_stale_local_branch_fast_forwarded(self, repo):
        # Remote pr3 gains a commit the local branch does not have.
        _sh(repo, "git", "checkout", "-q", "pr3")
        _commit(repo, "extra.txt", "extra\n", "remote-side extra")
        _sh(repo, "git", "push", "-q", "origin", "pr3")
        _sh(repo, "git", "reset", "-q", "--hard", "HEAD~1")   # local now strictly behind
        _sh(repo, "git", "checkout", "-q", "main")
        code, env = cv.convert("main", ["pr1", "pr3"], cwd=repo)
        assert code == cv.EXIT_OK, env
        merged = _sh(repo, "git", "log", "--format=%s", "origin/main..pr3")
        assert "remote-side extra" in merged

    def test_diverged_local_branch_refused(self, repo):
        # Remote pr3 and local pr3 each gain a different commit.
        _sh(repo, "git", "checkout", "-q", "pr3")
        _commit(repo, "remote-only.txt", "r\n", "remote only")
        _sh(repo, "git", "push", "-q", "origin", "pr3")
        _sh(repo, "git", "reset", "-q", "--hard", "HEAD~1")
        _commit(repo, "local-only.txt", "l\n", "local only")
        _sh(repo, "git", "checkout", "-q", "main")
        code, env = cv.convert("main", ["pr1", "pr3"], cwd=repo)
        assert code == cv.EXIT_INPUT
        assert env["error"]["code"] == "GIT.BRANCH_DIVERGED"
        assert "pr3" in env["error"]["message"]

    def test_pr_number_resolution_uses_gh_stub(self, repo):
        # No patching: the PATH gh stub answers `gh pr view <n> --json headRefName -q .headRefName`.
        code, env = cv.convert("main", ["1", "3"], cwd=repo)
        assert code == cv.EXIT_OK, env
        assert env["data"]["layers"] == ["pr1", "pr3"]

    def test_unknown_branch_is_input_error(self, repo):
        code, env = cv.convert("main", ["pr1", "nope"], cwd=repo)
        assert code == cv.EXIT_INPUT and "nope" in env["error"]["message"]

    def test_main_emits_fenced_json(self, repo, capsys):
        rc = cv.main(["main", "pr1", "pr3", "--cwd", str(repo)])
        out = capsys.readouterr().out
        assert rc == 0
        payload = json.loads(out.split("```json")[1].split("```")[0])
        assert payload["success"] is True
