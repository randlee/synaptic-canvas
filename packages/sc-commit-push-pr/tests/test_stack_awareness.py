"""Tests for gh-stack awareness in sc-commit-push-pr.

sc-commit-push-pr is the general-purpose commit/push/PR package, but it is
also the critical junction where a stack-unaware pull-merge-push or PR
creation can corrupt a gh-stack's linearity. These tests verify:

1. `check_stack_prerequisites()` / `check_gh_cli_available()` /
   `check_gh_stack_extension_installed()` / `check_sc_gh_stack_skill()` --
   the unconditional hard prerequisite gate (gh CLI, gh-stack extension,
   managing-gh-stacks skill), fail-closed on every sub-check.
2. `check_gh_stack_marker()` -- state-based detection of whether the
   current worktree is a gh-stack layer, mirroring
   `check_gh_stack_tracked()` in packages/sc-git-worktree.
3. `commit_pull_merge_commit_push.run_pipeline()`:
   - non-stack branch, prerequisites present -> byte-compatible, unchanged
     shape and behavior (no probes visible, no new steps).
   - prerequisites missing -> refuses with PREFLIGHT.STACK_PREREQS_MISSING,
     on a non-stack branch too (the gate is unconditional).
   - stack layer detected -> pull/merge is skipped, push/PR creation is
     refused with STACK.USE_GH_STACK, and `committed`/`pushed` are
     reported accurately.
4. `create_pr.main()` standalone: same two gates, refusing PR creation.
5. Detection fails closed: a broken git dir resolves to "not a stack
   worktree" (legacy behavior), never to a false positive.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import commit_pull_merge_commit_push as cp
import create_pr as create_pr_module
import stack_guard
from envelope import ErrorCodes
from pr_provider import PrCreateResult, PullRequestInfo


# =============================================================================
# Real-git fixtures (for check_gh_stack_marker)
# =============================================================================


def _run(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal real git repo with one commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "-b", "main"], cwd=repo)
    _run(["config", "user.email", "test@example.com"], cwd=repo)
    _run(["config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("init\n")
    _run(["add", "."], cwd=repo)
    _run(["commit", "-m", "init"], cwd=repo)
    return repo


def _add_worktree(repo: Path, wt_path: Path, branch: str) -> None:
    _run(["worktree", "add", "-b", branch, str(wt_path), "main"], cwd=repo)


def _mark_gh_stack(wt_path: Path) -> None:
    """Simulate gh-stack having written its per-worktree tracking marker."""
    result = _run(["rev-parse", "--git-dir"], cwd=wt_path)
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (wt_path / git_dir).resolve()
    (git_dir / "gh-stack").touch()


# =============================================================================
# check_gh_stack_marker()
# =============================================================================


class TestCheckGhStackMarker:
    def test_marker_present(self, tmp_path):
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-tracked"
        _add_worktree(repo, wt_path, "feature/tracked")
        _mark_gh_stack(wt_path)

        assert stack_guard.check_gh_stack_marker(wt_path) is True

    def test_marker_absent(self, tmp_path):
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-plain"
        _add_worktree(repo, wt_path, "feature/plain")

        assert stack_guard.check_gh_stack_marker(wt_path) is False

    def test_relative_git_dir_resolved_against_worktree(self, tmp_path):
        real_git_dir = tmp_path / ".git" / "worktrees" / "feature-x"
        real_git_dir.mkdir(parents=True)
        (real_git_dir / "gh-stack").touch()
        rel = ".git/worktrees/feature-x"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=rel + "\n")
            assert stack_guard.check_gh_stack_marker(tmp_path) is True

    def test_git_error_fails_closed_to_false(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="")
            assert stack_guard.check_gh_stack_marker(tmp_path) is False

    def test_empty_git_dir_output_fails_closed_to_false(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="\n")
            assert stack_guard.check_gh_stack_marker(tmp_path) is False

    def test_nonexistent_directory_fails_closed(self):
        # A missing cwd makes subprocess raise OSError before git even runs.
        assert stack_guard.check_gh_stack_marker(Path("/nonexistent/path/sc-cpp-xyz")) is False


# =============================================================================
# check_stack_prerequisites() and friends -- unconditional hard gate
# =============================================================================


class TestCheckStackPrerequisites:
    @patch("stack_guard._run_gh")
    def test_gh_cli_available_true(self, mock_run_gh):
        mock_run_gh.return_value = MagicMock(returncode=0)
        assert stack_guard.check_gh_cli_available() is True

    @patch("stack_guard._run_gh")
    def test_gh_cli_available_false_when_missing(self, mock_run_gh):
        mock_run_gh.return_value = None
        assert stack_guard.check_gh_cli_available() is False

    @patch("stack_guard._run_gh")
    def test_gh_stack_extension_installed_true(self, mock_run_gh):
        mock_run_gh.return_value = MagicMock(returncode=0, stdout="github/gh-stack\nother/ext\n")
        assert stack_guard.check_gh_stack_extension_installed() is True

    @patch("stack_guard._run_gh")
    def test_gh_stack_extension_installed_false(self, mock_run_gh):
        mock_run_gh.return_value = MagicMock(returncode=0, stdout="other/ext\n")
        assert stack_guard.check_gh_stack_extension_installed() is False

    @patch("stack_guard._run_gh")
    def test_gh_stack_extension_fails_closed_on_gh_error(self, mock_run_gh):
        mock_run_gh.return_value = MagicMock(returncode=1, stdout="")
        assert stack_guard.check_gh_stack_extension_installed() is False

    def test_sc_gh_stack_skill_present_under_repo(self, tmp_path):
        skill_dir = tmp_path / ".claude" / "skills" / "managing-gh-stacks"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: managing-gh-stacks\n---\n")

        with patch("stack_guard._home_dir", return_value=tmp_path / "nonexistent-home"):
            assert stack_guard.check_sc_gh_stack_skill(tmp_path) is True

    def test_sc_gh_stack_skill_absent(self, tmp_path):
        with patch("stack_guard._home_dir", return_value=tmp_path / "nonexistent-home"):
            assert stack_guard.check_sc_gh_stack_skill(tmp_path) is False

    def test_check_stack_prerequisites_all_present(self, tmp_path):
        with patch("stack_guard.check_gh_cli_available", return_value=True), \
             patch("stack_guard.check_gh_stack_extension_installed", return_value=True), \
             patch("stack_guard.check_sc_gh_stack_skill", return_value=True):
            result = stack_guard.check_stack_prerequisites(tmp_path)
        assert result == {
            "gh_cli": True,
            "gh_stack_extension": True,
            "sc_gh_stack_skill": True,
            "ok": True,
        }

    def test_check_stack_prerequisites_skill_missing(self, tmp_path):
        with patch("stack_guard.check_gh_cli_available", return_value=True), \
             patch("stack_guard.check_gh_stack_extension_installed", return_value=True), \
             patch("stack_guard.check_sc_gh_stack_skill", return_value=False):
            result = stack_guard.check_stack_prerequisites(tmp_path)
        assert result["ok"] is False
        assert result["sc_gh_stack_skill"] is False

    def test_missing_prereq_actions_lists_exact_install_lines(self):
        prereqs = {"gh_cli": False, "gh_stack_extension": False, "sc_gh_stack_skill": False}
        actions = stack_guard.missing_prereq_actions(prereqs)
        assert any("cli.github.com" in a for a in actions)
        assert any("gh extension install github/gh-stack" == a for a in actions)
        assert any(
            "/plugin marketplace add randlee/synaptic-canvas" in a
            and "/plugin install sc-gh-stack@synaptic-canvas" in a
            for a in actions
        )

    def test_missing_prereq_actions_only_lists_whats_missing(self):
        prereqs = {"gh_cli": True, "gh_stack_extension": False, "sc_gh_stack_skill": True}
        actions = stack_guard.missing_prereq_actions(prereqs)
        assert len(actions) == 1
        assert "gh-stack" in actions[0]


# =============================================================================
# commit_pull_merge_commit_push.run_pipeline() -- prereq gate + stack refusal
# =============================================================================


def _ok_prereqs():
    return {"gh_cli": True, "gh_stack_extension": True, "sc_gh_stack_skill": True, "ok": True}


def _missing_prereqs():
    return {"gh_cli": True, "gh_stack_extension": False, "sc_gh_stack_skill": True, "ok": False}


class TestCommitPipelinePrereqGate:
    """The gh-stack toolchain gate is unconditional -- it must refuse even
    on a plain (non-stack) branch, before any git mutation happens."""

    @patch("commit_pull_merge_commit_push.check_gh_stack_marker")
    @patch("commit_pull_merge_commit_push.get_repo_root")
    @patch("commit_pull_merge_commit_push.check_stack_prerequisites")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.push_branch")
    def test_missing_prereqs_refuses_on_non_stack_branch(
        self, mock_push, mock_fetch, mock_prereqs, mock_repo_root, mock_marker
    ):
        mock_prereqs.return_value = _missing_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")
        # Even though this is NOT a stack branch, prereqs are checked first.
        mock_marker.return_value = False

        input_data = cp.CommitPushInput(source="feature-x", destination="main")
        envelope = cp.run_pipeline(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.PREFLIGHT_STACK_PREREQS_MISSING
        assert envelope.error.recoverable is True
        assert "gh extension install github/gh-stack" in envelope.error.suggested_action
        assert envelope.data == _missing_prereqs()

        # No git mutation must have happened.
        mock_fetch.assert_not_called()
        mock_push.assert_not_called()
        # Stack detection is never even consulted -- the gate is unconditional.
        mock_marker.assert_not_called()


class TestCommitPipelineStackRefusal:
    """On a gh-stack layer: pull/merge is skipped, push/PR is refused."""

    @patch("commit_pull_merge_commit_push.check_gh_stack_marker")
    @patch("commit_pull_merge_commit_push.get_repo_root")
    @patch("commit_pull_merge_commit_push.check_stack_prerequisites")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.push_branch")
    def test_stack_layer_refuses_push_and_skips_pull_merge(
        self, mock_push, mock_merge, mock_fetch, mock_prereqs, mock_repo_root, mock_marker
    ):
        mock_prereqs.return_value = _ok_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")
        mock_marker.return_value = True

        input_data = cp.CommitPushInput(source="feature/layer-2", destination="feature/layer-1")
        envelope = cp.run_pipeline(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.STACK_USE_GH_STACK
        assert envelope.error.recoverable is True
        assert "gh stack submit --auto" in envelope.error.suggested_action
        assert "managing-gh-stacks" in envelope.error.suggested_action

        # Accurate partial-success reporting: commit (done by the caller
        # before invoking this script) stands; nothing was pushed.
        assert envelope.data["committed"] is True
        assert envelope.data["pushed"] is False
        assert envelope.data["stack"]["detected"] is True
        assert envelope.data["stack"]["pull_merge_skipped"] is True
        assert envelope.data["source_branch"] == "feature/layer-2"
        assert envelope.data["destination_branch"] == "feature/layer-1"

        # Pull/merge/push must never have been attempted on a stack layer.
        mock_fetch.assert_not_called()
        mock_merge.assert_not_called()
        mock_push.assert_not_called()


class TestCommitPipelineNonStackByteCompat:
    """Non-stack worktrees: byte-identical behavior once prerequisites pass."""

    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.check_gh_stack_marker")
    @patch("commit_pull_merge_commit_push.get_repo_root")
    @patch("commit_pull_merge_commit_push.check_stack_prerequisites")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.push_branch")
    def test_non_stack_success_shape_unchanged(
        self,
        mock_push,
        mock_needs_commit,
        mock_merge,
        mock_fetch,
        mock_prereqs,
        mock_repo_root,
        mock_marker,
        mock_get_remote_url,
        mock_detect_provider,
        mock_get_provider,
    ):
        from envelope import Envelope

        mock_prereqs.return_value = _ok_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")
        mock_marker.return_value = False
        mock_fetch.return_value = None
        mock_merge.return_value = (True, [])
        mock_needs_commit.return_value = False
        mock_push.return_value = None
        mock_get_remote_url.return_value = "https://github.com/org/repo.git"
        mock_detect_provider.return_value = Envelope.success_response(
            {
                "provider": "github",
                "org": "org",
                "repo": "repo",
                "remote_url": "https://github.com/org/repo.git",
                "project": None,
            }
        )
        fake_provider = MagicMock()
        fake_provider.check_pr_exists.return_value = MagicMock(exists=False, pr=None)
        mock_get_provider.return_value = fake_provider

        input_data = cp.CommitPushInput(source="feature-x", destination="main")
        envelope = cp.run_pipeline(input_data)

        # Same shape as before this change: success, needs_pr_text context.
        assert envelope.success is True
        assert envelope.error is None
        assert envelope.data["pr_exists"] is False
        assert envelope.data["needs_pr_text"] is True
        assert envelope.data["context"]["source_branch"] == "feature-x"
        assert envelope.data["context"]["destination_branch"] == "main"
        assert "committed" not in envelope.data
        assert "stack" not in envelope.data

        mock_fetch.assert_called_once_with("main")
        mock_merge.assert_called_once_with("main")
        mock_push.assert_called_once_with("feature-x")


class TestCommitPipelineDetectionFailClosed:
    """If probing the current worktree's stack state fails, treat it like a
    plain branch (fail closed) -- legacy behavior, not a false STACK.USE_GH_STACK."""

    @patch("commit_pull_merge_commit_push.get_repo_root")
    @patch("commit_pull_merge_commit_push.check_stack_prerequisites")
    def test_broken_git_dir_falls_back_to_legacy_behavior(self, mock_prereqs, mock_repo_root, tmp_path, monkeypatch):
        mock_prereqs.return_value = _ok_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")

        # cwd that doesn't exist as a git repo at all -> check_gh_stack_marker
        # fails closed to False via the real (unmocked) implementation.
        monkeypatch.chdir(tmp_path)

        with patch("commit_pull_merge_commit_push.resolve_source_branch", side_effect=RuntimeError("boom")):
            input_data = cp.CommitPushInput(source=None, destination="main")
            envelope = cp.run_pipeline(input_data)

        # Falls through to the existing (pre-existing) branch-resolution
        # error path -- not a STACK.USE_GH_STACK refusal.
        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.GIT_REMOTE


# =============================================================================
# create_pr.main() -- prereq gate + stack refusal
# =============================================================================


class TestCreatePrPrereqGate:
    @patch("create_pr.check_gh_stack_marker")
    @patch("create_pr.get_repo_root")
    @patch("create_pr.check_stack_prerequisites")
    @patch("create_pr.get_remote_url")
    def test_missing_prereqs_refuses_before_any_pr_work(
        self, mock_get_remote_url, mock_prereqs, mock_repo_root, mock_marker
    ):
        mock_prereqs.return_value = _missing_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")

        envelope = create_pr_module.main(
            title="feat: x", body="body", source="feature-x", destination="main"
        )

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.PREFLIGHT_STACK_PREREQS_MISSING
        assert envelope.error.recoverable is True
        mock_get_remote_url.assert_not_called()
        mock_marker.assert_not_called()


class TestCreatePrStackRefusal:
    @patch("create_pr.check_gh_stack_marker")
    @patch("create_pr.get_repo_root")
    @patch("create_pr.check_stack_prerequisites")
    @patch("create_pr.get_remote_url")
    def test_stack_layer_refuses_pr_creation(
        self, mock_get_remote_url, mock_prereqs, mock_repo_root, mock_marker
    ):
        mock_prereqs.return_value = _ok_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")
        mock_marker.return_value = True

        envelope = create_pr_module.main(
            title="feat: x", body="body", source="feature/layer-2", destination="feature/layer-1"
        )

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.STACK_USE_GH_STACK
        assert envelope.error.recoverable is True
        assert "gh stack submit --auto" in envelope.error.suggested_action
        assert envelope.data["pr_created"] is False
        assert envelope.data["stack"]["detected"] is True

        # No PR created: remote URL / provider detection never reached.
        mock_get_remote_url.assert_not_called()


class TestCreatePrNonStackByteCompat:
    @patch("create_pr.get_provider")
    @patch("create_pr.detect_provider")
    @patch("create_pr.check_gh_stack_marker")
    @patch("create_pr.get_repo_root")
    @patch("create_pr.check_stack_prerequisites")
    def test_non_stack_success_shape_unchanged(
        self, mock_prereqs, mock_repo_root, mock_marker, mock_detect_provider, mock_get_provider
    ):
        from envelope import Envelope

        mock_prereqs.return_value = _ok_prereqs()
        mock_repo_root.return_value = Path("/tmp/repo")
        mock_marker.return_value = False
        mock_detect_provider.return_value = Envelope.success_response(
            {
                "provider": "github",
                "org": "org",
                "repo": "repo",
                "remote_url": "https://github.com/org/repo.git",
                "project": None,
            }
        )
        fake_provider = MagicMock()
        fake_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="123",
                url="https://github.com/org/repo/pull/123",
                source_branch="feature-x",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = fake_provider

        envelope = create_pr_module.main(
            title="feat: x",
            body="body",
            source="feature-x",
            destination="main",
            remote_url="https://github.com/org/repo.git",
        )

        assert envelope.success is True
        assert envelope.error is None
        assert envelope.data["pr"]["id"] == "123"
        assert envelope.data["pr"]["url"] == "https://github.com/org/repo/pull/123"
        assert "stack" not in envelope.data
        assert "pr_created" not in envelope.data


# =============================================================================
# preflight_utils.run_preflight_check() -- unconditional gate at hook level
# =============================================================================


class TestPreflightHookStackGate:
    def test_hook_blocks_when_stack_toolchain_missing(self, tmp_path, capsys):
        import preflight_utils

        with patch("preflight_utils.get_repo_root", return_value=tmp_path), \
             patch("preflight_utils.check_stack_prerequisites", return_value=_missing_prereqs()):
            exit_code = preflight_utils.run_preflight_check("test_hook")

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "gh-stack" in captured.err
        assert "gh extension install github/gh-stack" in captured.err

    def test_hook_proceeds_past_stack_gate_when_prereqs_ok(self, tmp_path):
        import preflight_utils

        with patch("preflight_utils.get_repo_root", return_value=tmp_path), \
             patch("preflight_utils.check_stack_prerequisites", return_value=_ok_prereqs()), \
             patch("preflight_utils.load_shared_settings", return_value={"git": {"protected_branches": ["main"]}}), \
             patch("preflight_utils.validate_git_auth", return_value=(True, "ok")):
            exit_code = preflight_utils.run_preflight_check("test_hook")

        assert exit_code == 0
