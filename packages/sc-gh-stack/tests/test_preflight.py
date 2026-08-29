"""Unit tests for gh_stack_shared and gh_stack_preflight (subprocess mocked)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import gh_stack_preflight as pf  # noqa: E402
import gh_stack_shared as gs  # noqa: E402


def cp(returncode=0, stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestShared:
    def test_resolve_remote_prefers_push_default(self):
        with patch.object(gs, "config_get", return_value="upstream"), \
             patch.object(gs, "remotes", return_value=["origin", "upstream"]):
            assert gs.resolve_remote() == "upstream"

    def test_resolve_remote_falls_back_to_first_remote(self):
        with patch.object(gs, "config_get", return_value=""), \
             patch.object(gs, "remotes", return_value=["origin", "fork"]):
            assert gs.resolve_remote() == "origin"

    def test_resolve_remote_none_when_no_remotes(self):
        with patch.object(gs, "config_get", return_value=""), patch.object(gs, "remotes", return_value=[]):
            assert gs.resolve_remote() is None

    def test_resolve_pr_branch_success_and_failure(self):
        with patch.object(gs, "gh", return_value=cp(0, "feat/api\n")):
            assert gs.resolve_pr_branch("101") == "feat/api"
        with patch.object(gs, "gh", return_value=cp(1, "", "not found")):
            assert gs.resolve_pr_branch("999") is None

    def test_conflicted_files_parses_lines(self):
        with patch.object(gs, "git", return_value=cp(0, "a.rs\nsrc/b.rs\n\n")):
            assert gs.conflicted_files() == ["a.rs", "src/b.rs"]

    def test_emit_is_fenced_json(self, capsys):
        gs.emit(gs.envelope(True, {"x": 1}))
        out = capsys.readouterr().out.strip().splitlines()
        assert out[0] == "```json" and out[-1] == "```"
        assert json.loads("\n".join(out[1:-1])) == {"success": True, "data": {"x": 1}, "error": None}

    def test_envelope_error_shape(self):
        env = gs.envelope(False, None, gs.error_obj("X.Y", "m", True, "do it"))
        assert env["error"] == {"code": "X.Y", "message": "m", "recoverable": True, "suggested_action": "do it"}


def _healthy_env(monkeypatch, **overrides):
    """Patch every probe preflight uses to a healthy default; overrides flip individual ones."""
    gh_map = {
        ("--version",): cp(0, "gh version 2.x"),
        ("extension", "list"): cp(0, "gh stack  github/gh-stack  v0.9.0"),
        ("auth", "status"): cp(0),
    }
    gh_map.update(overrides.pop("gh", {}))
    monkeypatch.setattr(gs, "gh", lambda args, cwd=None: gh_map[tuple(args)])
    cfg = {"rerere.enabled": "true", "remote.pushDefault": ""}
    cfg.update(overrides.pop("config", {}))
    monkeypatch.setattr(gs, "config_get", lambda key, cwd=None: cfg.get(key, ""))
    # Bind override values once at setup: popping inside the lambdas would hand
    # back the override on the first probe call only, then silently revert to
    # the healthy default on every later call.
    remotes_val = overrides.pop("remotes", ["origin"])
    clean_val = overrides.pop("clean", True)
    rebasing_val = overrides.pop("rebasing", False)
    monkeypatch.setattr(gs, "remotes", lambda cwd=None: remotes_val)
    monkeypatch.setattr(gs, "working_tree_clean", lambda cwd=None: clean_val)
    monkeypatch.setattr(gs, "rebase_in_progress", lambda cwd=None: rebasing_val)
    monkeypatch.setattr(gs, "in_git_repo", lambda cwd=None: True)
    assert not overrides, f"unknown overrides: {sorted(overrides)}"


def _status(checks, name):
    return next(c for c in checks if c["name"] == name)["status"]


class TestPreflight:
    def test_all_ok_only_warns_on_stacked_prs(self, monkeypatch):
        _healthy_env(monkeypatch)
        checks = pf.run_checks()
        assert [c["name"] for c in checks if c["status"] == "fail"] == []
        assert _status(checks, "stacked_prs_enabled") == "warn"
        assert pf.main([]) == 0

    def test_missing_extension_fails_with_fix(self, monkeypatch):
        _healthy_env(monkeypatch, gh={("extension", "list"): cp(0, "gh copilot github/gh-copilot")})
        checks = pf.run_checks()
        c = next(c for c in checks if c["name"] == "gh_stack_extension")
        assert c["status"] == "fail" and "gh extension install github/gh-stack" == c["fix"]

    def test_rerere_disabled_warns_not_fails(self, monkeypatch):
        # Warn only: gh_stack_convert.py enables rerere itself, so a first run
        # in a fresh repo must not be blocked on this check.
        _healthy_env(monkeypatch, config={"rerere.enabled": ""})
        checks = pf.run_checks()
        assert _status(checks, "rerere_enabled") == "warn"
        assert [c["name"] for c in checks if c["status"] == "fail"] == []

    def test_two_remotes_without_push_default_fails(self, monkeypatch):
        _healthy_env(monkeypatch, remotes=["origin", "upstream"])
        checks = pf.run_checks()
        assert _status(checks, "remote") == "fail"
        assert "remote.pushDefault" in next(c for c in checks if c["name"] == "remote")["fix"]

    def test_two_remotes_with_push_default_ok(self, monkeypatch):
        _healthy_env(monkeypatch, remotes=["origin", "upstream"], config={"remote.pushDefault": "origin"})
        assert _status(pf.run_checks(), "remote") == "ok"

    def test_dirty_tree_and_rebase_in_progress_fail(self, monkeypatch):
        _healthy_env(monkeypatch, clean=False, rebasing=True)
        checks = pf.run_checks()
        assert _status(checks, "working_tree_clean") == "fail"
        assert _status(checks, "no_rebase_in_progress") == "fail"

    def test_main_reports_failed_names_and_exit_1(self, monkeypatch, capsys):
        _healthy_env(monkeypatch, clean=False)
        assert pf.main([]) == 1
        out = capsys.readouterr().out
        payload = json.loads(out.split("```json")[1].split("```")[0])
        assert payload["success"] is False
        assert payload["error"]["code"] == "PREFLIGHT.FAILED"
        assert payload["data"]["failed"] == ["working_tree_clean"]

    def test_main_outside_repo(self, monkeypatch, capsys):
        monkeypatch.setattr(gs, "in_git_repo", lambda cwd=None: False)
        assert pf.main([]) == 1
        assert "PREFLIGHT.NOT_A_REPO" in capsys.readouterr().out
