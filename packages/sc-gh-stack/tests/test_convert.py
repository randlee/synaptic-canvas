"""Tests for gh_stack_convert: unit tests with mocked git/gh, plus a real-git integration test."""
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


class TestChain:
    """chain() drives git only through gs.is_ancestor / gs.git / gs.conflicted_files."""

    def test_skips_layers_already_chained(self):
        calls = []
        with patch.object(gs, "is_ancestor", return_value=True), \
             patch.object(gs, "git", side_effect=lambda a, cwd=None: calls.append(a) or cp(0)):
            r = cv.chain(["l1", "l2"], "origin/main")
        assert [c["action"] for c in r.chained] == ["skip", "skip"]
        assert r.conflict is None and calls == []

    def test_rebases_each_layer_onto_the_one_below(self):
        rebases = []

        def fake_git(args, cwd=None):
            rebases.append(args)
            return cp(0)

        with patch.object(gs, "is_ancestor", return_value=False), patch.object(gs, "git", fake_git):
            r = cv.chain(["l1", "l2", "l3"], "origin/main")
        assert rebases == [
            ["rebase", "--onto", "origin/main", "origin/main", "l1"],
            ["rebase", "--onto", "l1", "origin/main", "l2"],
            ["rebase", "--onto", "l2", "origin/main", "l3"],
        ]
        assert [(c["branch"], c["onto"]) for c in r.chained] == [("l1", "origin/main"), ("l2", "l1"), ("l3", "l2")]

    def test_stops_at_first_conflict_with_files(self):
        def fake_git(args, cwd=None):
            return cp(1) if args[-1] == "l2" else cp(0)

        with patch.object(gs, "is_ancestor", return_value=False), patch.object(gs, "git", fake_git), \
             patch.object(gs, "conflicted_files", return_value=["shared.txt"]):
            r = cv.chain(["l1", "l2", "l3"], "origin/main")
        assert r.conflict == {"layer": "l2", "onto": "l1", "files": ["shared.txt"]}
        assert [c["branch"] for c in r.chained] == ["l1"]   # l3 never attempted


class TestConvertValidation:
    def test_requires_two_layers(self):
        code, env = cv.convert("main", ["only"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "VALIDATION.INPUT"

    def test_no_remote(self):
        with patch.object(gs, "resolve_remote", return_value=None):
            code, env = cv.convert("main", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.REMOTE"

    def test_trunk_missing_on_remote(self):
        with patch.object(gs, "resolve_remote", return_value="origin"), \
             patch.object(gs, "git", return_value=cp(0)), \
             patch.object(gs, "remote_branch_exists", return_value=False):
            code, env = cv.convert("nope", ["a", "b"])
        assert code == cv.EXIT_INPUT and env["error"]["code"] == "GIT.TRUNK_NOT_FOUND"

    def test_fetch_failure_is_exit_1(self):
        def fake_git(args, cwd=None):
            return cp(128, "", "could not resolve host") if args[0] == "fetch" else cp(0)

        with patch.object(gs, "resolve_remote", return_value="origin"), patch.object(gs, "git", fake_git):
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


# --- integration: real git, stubbed gh -------------------------------------

def _sh(cwd, *args):
    return subprocess.run(list(args), cwd=cwd, check=True, capture_output=True, text=True).stdout


def _commit(cwd, name, content, msg):
    (cwd / name).write_text(content)
    _sh(cwd, "git", "add", ".")
    _sh(cwd, "git", "commit", "-q", "-m", msg)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Bare origin + working clone with main and three parallel branches; pr1/pr2 conflict."""
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
    stub.write_text('#!/bin/sh\ncase "$*" in "stack view --json") exit 2;; esac\necho "[stub gh $*]"\n')
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GIT_EDITOR", "true")
    return work


class TestConvertIntegration:
    def test_conflict_resume_and_linear_chain(self, repo):
        # First run: pr1 already on trunk (skip), pr2 conflicts on shared.txt.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_CONFLICT
        assert env["error"]["code"] == "CONVERT.CONFLICT"
        assert env["data"]["conflict"] == {"layer": "pr2", "onto": "pr1", "files": ["shared.txt"]}
        assert [c["action"] for c in env["data"]["chained"]] == ["skip"]
        assert gs.rebase_in_progress(cwd=repo)

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

        # Ancestry is a single linear chain and rerere was enabled.
        assert gs.is_ancestor("origin/main", "pr1", cwd=repo)
        assert gs.is_ancestor("pr1", "pr2", cwd=repo)
        assert gs.is_ancestor("pr2", "pr3", cwd=repo)
        assert gs.config_get("rerere.enabled", cwd=repo) == "true"
        assert _sh(repo, "git", "rev-parse", "--abbrev-ref", "HEAD").strip() == "pr3"

        # Third run: everything skipped, stack already present.
        code, env = cv.convert("main", ["pr1", "pr2", "pr3"], cwd=repo)
        assert code == cv.EXIT_OK
        assert all(c["action"] == "skip" for c in env["data"]["chained"])

    def test_pr_number_resolution_uses_gh(self, repo, monkeypatch):
        with patch.object(gs, "resolve_pr_branch", side_effect=lambda n, cwd=None: {"1": "pr1", "3": "pr3"}[n]):
            code, env = cv.convert("main", ["1", "3"], cwd=repo)
        assert code == cv.EXIT_OK and env["data"]["layers"] == ["pr1", "pr3"]

    def test_unknown_branch_is_input_error(self, repo):
        code, env = cv.convert("main", ["pr1", "nope"], cwd=repo)
        assert code == cv.EXIT_INPUT and "nope" in env["error"]["message"]

    def test_main_emits_fenced_json(self, repo, capsys):
        rc = cv.main(["main", "pr1", "pr3", "--cwd", str(repo)])
        out = capsys.readouterr().out
        assert rc == 0
        payload = json.loads(out.split("```json")[1].split("```")[0])
        assert payload["success"] is True
