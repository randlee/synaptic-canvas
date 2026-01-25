"""Tests for commit_pull_merge_commit_push pipeline.

Tests cover:
- No staged changes scenario (skips commit, continues pipeline)
- Successful commit and push
- Merge conflict detection
- PR exists scenario
- PR needed scenario
- Error handling (auth, remote failures)
- Branch resolution logic
"""

import json
import subprocess
from unittest import mock
from unittest.mock import MagicMock, patch, call
import os

import pytest

# Add the scripts directory to path for imports
import sys
from pathlib import Path
scripts_dir = Path(__file__).parent.parent / "packages" / "sc-commit-push-pr" / "scripts"
sys.path.insert(0, str(scripts_dir))

from commit_pull_merge_commit_push import (
    CommitPushInput,
    CommitPushData,
    run_git_command,
    get_current_branch,
    has_staged_changes,
    fetch_branch,
    merge_branch,
    push_branch,
    get_diff_stat,
    has_merge_commit_needed,
    commit_merge,
    abort_merge,
    resolve_destination_branch,
    resolve_source_branch,
    run_pipeline,
    main,
)
from envelope import ErrorCodes
from pr_provider import PullRequestInfo, PrCheckResult, PrProviderError


# =============================================================================
# Pydantic Model Tests
# =============================================================================

class TestCommitPushInput:
    """Tests for CommitPushInput model."""

    def test_default_values(self):
        """Test default values for input."""
        input_data = CommitPushInput()
        assert input_data.source is None
        assert input_data.destination is None

    def test_explicit_values(self):
        """Test setting explicit values."""
        input_data = CommitPushInput(source="feature-x", destination="main")
        assert input_data.source == "feature-x"
        assert input_data.destination == "main"

    def test_partial_values(self):
        """Test setting partial values."""
        input_data = CommitPushInput(source="feature-y")
        assert input_data.source == "feature-y"
        assert input_data.destination is None


class TestCommitPushData:
    """Tests for CommitPushData model."""

    def test_pr_exists_scenario(self):
        """Test data when PR exists."""
        pr_info = PullRequestInfo(
            id="123",
            url="https://github.com/org/repo/pull/123",
            source_branch="feature",
            destination_branch="main",
            provider="github"
        )
        data = CommitPushData(pr_exists=True, pr=pr_info)
        assert data.pr_exists is True
        assert data.pr is not None
        assert data.pr.id == "123"

    def test_needs_pr_text_scenario(self):
        """Test data when PR needs to be created."""
        data = CommitPushData(
            pr_exists=False,
            needs_pr_text=True,
            context={
                "source_branch": "feature",
                "destination_branch": "main",
                "diff_summary": "3 files changed"
            }
        )
        assert data.pr_exists is False
        assert data.needs_pr_text is True
        assert data.context["source_branch"] == "feature"

    def test_conflict_scenario(self):
        """Test data when merge conflicts exist."""
        data = CommitPushData(
            pr_exists=False,
            conflicts=["file1.py", "file2.py"]
        )
        assert data.pr_exists is False
        assert data.conflicts == ["file1.py", "file2.py"]


# =============================================================================
# Git Operation Tests
# =============================================================================

class TestRunGitCommand:
    """Tests for run_git_command helper."""

    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful git command."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout="On branch main\n",
            stderr=""
        )

        result = run_git_command(["status"])

        assert result.returncode == 0
        assert "On branch main" in result.stdout
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["git", "status"]

    @patch("subprocess.run")
    def test_failed_command_with_check(self, mock_run):
        """Test failed git command with check=True."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "bad-command"],
            stderr="error"
        )

        with pytest.raises(subprocess.CalledProcessError):
            run_git_command(["bad-command"])

    @patch("subprocess.run")
    def test_failed_command_without_check(self, mock_run):
        """Test failed git command with check=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "diff", "--quiet"],
            returncode=1,
            stdout="",
            stderr=""
        )

        result = run_git_command(["diff", "--quiet"], check=False)

        assert result.returncode == 1


class TestGetCurrentBranch:
    """Tests for get_current_branch."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_returns_branch_name(self, mock_run):
        """Test successful branch detection."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="feature-branch\n",
            stderr=""
        )

        branch = get_current_branch()

        assert branch == "feature-branch"
        mock_run.assert_called_once_with(["rev-parse", "--abbrev-ref", "HEAD"])

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_detached_head_raises(self, mock_run):
        """Test error on detached HEAD."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="HEAD\n",
            stderr=""
        )

        with pytest.raises(RuntimeError) as exc_info:
            get_current_branch()

        assert "Detached HEAD" in str(exc_info.value)

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_command_failure_raises(self, mock_run):
        """Test error on command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "rev-parse"],
            stderr="not a git repository"
        )

        with pytest.raises(RuntimeError) as exc_info:
            get_current_branch()

        assert "Failed to get current branch" in str(exc_info.value)


class TestHasStagedChanges:
    """Tests for has_staged_changes."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_no_changes(self, mock_run):
        """Test when no staged changes."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,  # 0 = no changes
            stdout="",
            stderr=""
        )

        assert has_staged_changes() is False

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_has_changes(self, mock_run):
        """Test when staged changes exist."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,  # 1 = changes exist
            stdout="",
            stderr=""
        )

        assert has_staged_changes() is True


class TestFetchBranch:
    """Tests for fetch_branch."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_successful_fetch(self, mock_run):
        """Test successful branch fetch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr=""
        )

        fetch_branch("main")

        mock_run.assert_called_once_with(["fetch", "origin", "main"])

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_fetch_failure(self, mock_run):
        """Test fetch failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "fetch"],
            stderr="Connection refused"
        )

        with pytest.raises(RuntimeError) as exc_info:
            fetch_branch("main")

        assert "Failed to fetch" in str(exc_info.value)


class TestMergeBranch:
    """Tests for merge_branch."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_successful_merge(self, mock_run):
        """Test successful fast-forward merge."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Updating abc123..def456\nFast-forward\n",
            stderr=""
        )

        success, conflicts = merge_branch("main")

        assert success is True
        assert conflicts == []
        mock_run.assert_called_once_with(["merge", "origin/main"], check=False)

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_merge_with_conflicts(self, mock_run):
        """Test merge with conflicts."""
        # First call: merge command fails
        # Second call: get conflict files
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="CONFLICT (content): ...",
                stderr=""
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="file1.py\nfile2.py\n",
                stderr=""
            )
        ]

        success, conflicts = merge_branch("main")

        assert success is False
        assert conflicts == ["file1.py", "file2.py"]
        assert mock_run.call_count == 2


class TestPushBranch:
    """Tests for push_branch."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_successful_push(self, mock_run):
        """Test successful push."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr=""
        )

        push_branch("feature")

        mock_run.assert_called_once_with(["push", "origin", "feature"])

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_push_failure(self, mock_run):
        """Test push failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "push"],
            stderr="Permission denied"
        )

        with pytest.raises(RuntimeError) as exc_info:
            push_branch("feature")

        assert "Failed to push" in str(exc_info.value)


class TestGetDiffStat:
    """Tests for get_diff_stat."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_returns_diff_stat(self, mock_run):
        """Test returns diff statistics."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=" file1.py | 10 ++++\n file2.py | 5 +++--\n 2 files changed\n",
            stderr=""
        )

        stat = get_diff_stat("main", "feature")

        assert "2 files changed" in stat
        mock_run.assert_called_once_with(
            ["diff", "--stat", "main..feature"],
            check=False
        )

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_returns_empty_on_error(self, mock_run):
        """Test returns empty string on error."""
        mock_run.side_effect = Exception("git error")

        stat = get_diff_stat("main", "feature")

        assert stat == ""


class TestHasMergeCommitNeeded:
    """Tests for has_merge_commit_needed."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_merge_in_progress(self, mock_run):
        """Test when merge is in progress."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,  # MERGE_HEAD exists
            stdout="abc123\n",
            stderr=""
        )

        assert has_merge_commit_needed() is True

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_no_merge_in_progress(self, mock_run):
        """Test when no merge in progress."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,  # MERGE_HEAD doesn't exist
            stdout="",
            stderr=""
        )

        assert has_merge_commit_needed() is False


class TestCommitMerge:
    """Tests for commit_merge."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_successful_commit(self, mock_run):
        """Test successful merge commit."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="[main abc123] Merge branch 'feature'\n",
            stderr=""
        )

        commit_merge()

        mock_run.assert_called_once_with(["commit", "--no-edit"])

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_commit_failure(self, mock_run):
        """Test commit failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "commit"],
            stderr="nothing to commit"
        )

        with pytest.raises(RuntimeError) as exc_info:
            commit_merge()

        assert "Failed to commit merge" in str(exc_info.value)


class TestAbortMerge:
    """Tests for abort_merge."""

    @patch("commit_pull_merge_commit_push.run_git_command")
    def test_successful_abort(self, mock_run):
        """Test successful merge abort."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr=""
        )

        abort_merge()

        mock_run.assert_called_once_with(["merge", "--abort"])


# =============================================================================
# Branch Resolution Tests
# =============================================================================

class TestResolveDestinationBranch:
    """Tests for resolve_destination_branch."""

    def test_explicit_branch(self):
        """Test using explicit branch."""
        assert resolve_destination_branch("develop") == "develop"

    @patch("commit_pull_merge_commit_push.load_shared_settings")
    @patch("commit_pull_merge_commit_push.get_protected_branches")
    def test_from_settings(self, mock_protected, mock_settings):
        """Test getting from settings."""
        mock_settings.return_value = {"git": {"protected_branches": ["main", "develop"]}}
        mock_protected.return_value = ["main", "develop"]

        branch = resolve_destination_branch()

        assert branch == "main"

    @patch("commit_pull_merge_commit_push.load_shared_settings")
    @patch("commit_pull_merge_commit_push.get_protected_branches")
    def test_no_settings_raises(self, mock_protected, mock_settings):
        """Test error when no settings."""
        mock_settings.return_value = None
        mock_protected.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            resolve_destination_branch()

        assert "No destination branch" in str(exc_info.value)


class TestResolveSourceBranch:
    """Tests for resolve_source_branch."""

    def test_explicit_branch(self):
        """Test using explicit branch."""
        assert resolve_source_branch("feature-x") == "feature-x"

    @patch("commit_pull_merge_commit_push.get_current_branch")
    def test_from_current(self, mock_current):
        """Test getting current branch."""
        mock_current.return_value = "my-feature"

        branch = resolve_source_branch()

        assert branch == "my-feature"


# =============================================================================
# Pipeline Tests
# =============================================================================

class TestRunPipelineNoStagedChanges:
    """Tests for pipeline when no staged changes."""

    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_pipeline_continues_without_staged_changes(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect, mock_provider
    ):
        """Test pipeline continues when no staged changes."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False  # No staged changes
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False

        # Mock PR check returning no existing PR
        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(exists=False)
        mock_provider.return_value = mock_pr_provider

        result = run_pipeline(CommitPushInput())

        assert result.success is True
        assert result.data["pr_exists"] is False
        assert result.data["needs_pr_text"] is True
        # Verify pipeline continued despite no staged changes
        mock_fetch.assert_called_once()
        mock_merge.assert_called_once()
        mock_push.assert_called_once()


class TestRunPipelineSuccessful:
    """Tests for successful pipeline execution."""

    @patch("commit_pull_merge_commit_push.get_diff_stat")
    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_successful_push_pr_needed(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect, mock_provider, mock_diff
    ):
        """Test successful push when PR needs to be created."""
        mock_source.return_value = "feature-x"
        mock_dest.return_value = "main"
        mock_staged.return_value = True
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False
        mock_diff.return_value = "3 files changed"

        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(exists=False)
        mock_provider.return_value = mock_pr_provider

        result = run_pipeline(CommitPushInput(source="feature-x", destination="main"))

        assert result.success is True
        assert result.data["pr_exists"] is False
        assert result.data["needs_pr_text"] is True
        assert result.data["context"]["source_branch"] == "feature-x"
        assert result.data["context"]["destination_branch"] == "main"


class TestRunPipelinePrExists:
    """Tests for pipeline when PR already exists."""

    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_returns_existing_pr(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect, mock_provider
    ):
        """Test returns existing PR info when PR exists."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False

        existing_pr = PullRequestInfo(
            id="42",
            url="https://github.com/org/repo/pull/42",
            source_branch="feature",
            destination_branch="main",
            provider="github"
        )
        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(
            exists=True,
            pr=existing_pr
        )
        mock_provider.return_value = mock_pr_provider

        result = run_pipeline(CommitPushInput())

        assert result.success is True
        assert result.data["pr_exists"] is True
        assert result.data["pr"]["id"] == "42"
        assert result.data["pr"]["url"] == "https://github.com/org/repo/pull/42"


class TestRunPipelineMergeConflict:
    """Tests for pipeline with merge conflicts."""

    @patch("commit_pull_merge_commit_push.abort_merge")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_returns_conflict_error(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_url, mock_detect, mock_abort
    ):
        """Test returns error with conflict list on merge conflict."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = True
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (False, ["file1.py", "file2.py"])

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_MERGE_CONFLICT
        assert result.error.recoverable is True
        assert result.data["conflicts"] == ["file1.py", "file2.py"]
        mock_abort.assert_called_once()


class TestRunPipelineErrors:
    """Tests for various error scenarios."""

    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_source_branch_error(self, mock_source):
        """Test error resolving source branch."""
        mock_source.side_effect = RuntimeError("Not on a branch")

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE

    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_destination_branch_error(self, mock_source, mock_dest):
        """Test error resolving destination branch."""
        mock_source.return_value = "feature"
        mock_dest.side_effect = RuntimeError("No protected branches configured")

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.CONFIG_PROTECTED_BRANCH

    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_no_remote_url(self, mock_source, mock_dest, mock_staged, mock_url):
        """Test error when no remote URL."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = None

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE

    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_fetch_failure(self, mock_source, mock_dest, mock_staged, mock_fetch, mock_url, mock_detect):
        """Test fetch failure."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_fetch.side_effect = RuntimeError("Network error")

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE
        assert result.error.recoverable is True

    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_push_auth_failure(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect
    ):
        """Test push authentication failure."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False
        mock_push.side_effect = RuntimeError("Authentication failed")

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_AUTH

    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_push_network_failure(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect
    ):
        """Test push network failure (recoverable)."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False
        mock_push.side_effect = RuntimeError("Connection timeout")

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE
        assert result.error.recoverable is True


class TestRunPipelineProviderDetection:
    """Tests for provider detection in pipeline."""

    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_provider_detection_failure(
        self, mock_source, mock_dest, mock_staged, mock_url, mock_detect
    ):
        """Test provider detection failure."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = False
        mock_url.return_value = "https://unknown.host/org/repo"
        mock_detect.return_value = MagicMock(
            success=False,
            error=MagicMock(code=ErrorCodes.PROVIDER_DETECT_FAILED)
        )

        result = run_pipeline(CommitPushInput())

        assert result.success is False


class TestRunPipelineWithMergeCommit:
    """Tests for pipeline requiring merge commit."""

    @patch("commit_pull_merge_commit_push.get_diff_stat")
    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.commit_merge")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_commits_merge_when_needed(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_commit, mock_push, mock_url, mock_detect,
        mock_provider, mock_diff
    ):
        """Test commits merge when MERGE_HEAD exists."""
        mock_source.return_value = "feature"
        mock_dest.return_value = "main"
        mock_staged.return_value = True
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = True  # Merge commit needed
        mock_diff.return_value = ""

        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(exists=False)
        mock_provider.return_value = mock_pr_provider

        result = run_pipeline(CommitPushInput())

        assert result.success is True
        mock_commit.assert_called_once()


# =============================================================================
# Main Entry Point Tests
# =============================================================================

class TestMain:
    """Tests for main entry point."""

    @patch("commit_pull_merge_commit_push.run_pipeline")
    def test_main_with_input(self, mock_pipeline):
        """Test main with explicit input."""
        mock_pipeline.return_value = MagicMock(success=True)

        input_data = CommitPushInput(source="feature", destination="main")
        result = main(input_data)

        mock_pipeline.assert_called_once_with(input_data)

    @patch("commit_pull_merge_commit_push.run_pipeline")
    @patch("commit_pull_merge_commit_push.parse_args")
    def test_main_parses_args(self, mock_parse, mock_pipeline):
        """Test main parses args when no input provided."""
        mock_parse.return_value = CommitPushInput(source="cli-feature")
        mock_pipeline.return_value = MagicMock(success=True)

        result = main()

        mock_parse.assert_called_once()
        mock_pipeline.assert_called_once()


# =============================================================================
# Integration-Style Tests
# =============================================================================

class TestPipelineIntegration:
    """Integration-style tests for common workflows."""

    @patch("commit_pull_merge_commit_push.get_diff_stat")
    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_full_workflow_github_new_pr(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect, mock_provider, mock_diff
    ):
        """Test complete workflow for GitHub with new PR needed."""
        # Setup
        mock_source.return_value = "feature/awesome"
        mock_dest.return_value = "main"
        mock_staged.return_value = True
        mock_url.return_value = "https://github.com/myorg/myrepo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={
                "provider": "github",
                "org": "myorg",
                "repo": "myrepo",
                "remote_url": "https://github.com/myorg/myrepo"
            }
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False
        mock_diff.return_value = " 5 files changed, 100 insertions(+), 20 deletions(-)"

        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(exists=False)
        mock_provider.return_value = mock_pr_provider

        # Execute
        result = run_pipeline(CommitPushInput())

        # Verify
        assert result.success is True
        data = result.data
        assert data["pr_exists"] is False
        assert data["needs_pr_text"] is True
        assert data["context"]["source_branch"] == "feature/awesome"
        assert data["context"]["destination_branch"] == "main"
        assert data["context"]["provider"] == "github"

        # Verify call sequence
        mock_fetch.assert_called_once_with("main")
        mock_merge.assert_called_once_with("main")
        mock_push.assert_called_once_with("feature/awesome")

    @patch("commit_pull_merge_commit_push.get_provider")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.push_branch")
    @patch("commit_pull_merge_commit_push.has_merge_commit_needed")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_full_workflow_azure_existing_pr(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_merge_needed, mock_push, mock_url, mock_detect, mock_provider
    ):
        """Test complete workflow for Azure DevOps with existing PR."""
        mock_source.return_value = "feature/ticket-123"
        mock_dest.return_value = "develop"
        mock_staged.return_value = True
        mock_url.return_value = "https://dev.azure.com/myorg/myproj/_git/myrepo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={
                "provider": "azuredevops",
                "org": "myorg",
                "project": "myproj",
                "repo": "myrepo",
                "remote_url": "https://dev.azure.com/myorg/myproj/_git/myrepo"
            }
        )
        mock_merge.return_value = (True, [])
        mock_merge_needed.return_value = False

        existing_pr = PullRequestInfo(
            id="789",
            url="https://dev.azure.com/myorg/myproj/_git/myrepo/pullrequest/789",
            source_branch="feature/ticket-123",
            destination_branch="develop",
            provider="azuredevops"
        )
        mock_pr_provider = MagicMock()
        mock_pr_provider.check_pr_exists.return_value = PrCheckResult(
            exists=True,
            pr=existing_pr
        )
        mock_provider.return_value = mock_pr_provider

        result = run_pipeline(CommitPushInput())

        assert result.success is True
        data = result.data
        assert data["pr_exists"] is True
        assert data["pr"]["id"] == "789"
        assert data["pr"]["provider"] == "azuredevops"

    @patch("commit_pull_merge_commit_push.abort_merge")
    @patch("commit_pull_merge_commit_push.detect_provider")
    @patch("commit_pull_merge_commit_push.get_remote_url")
    @patch("commit_pull_merge_commit_push.merge_branch")
    @patch("commit_pull_merge_commit_push.fetch_branch")
    @patch("commit_pull_merge_commit_push.has_staged_changes")
    @patch("commit_pull_merge_commit_push.resolve_destination_branch")
    @patch("commit_pull_merge_commit_push.resolve_source_branch")
    def test_full_workflow_conflict_recovery(
        self, mock_source, mock_dest, mock_staged, mock_fetch, mock_merge,
        mock_url, mock_detect, mock_abort
    ):
        """Test complete workflow with conflict requiring user resolution."""
        mock_source.return_value = "feature/conflicting"
        mock_dest.return_value = "main"
        mock_staged.return_value = True
        mock_url.return_value = "https://github.com/org/repo"
        mock_detect.return_value = MagicMock(
            success=True,
            data={"provider": "github", "org": "org", "repo": "repo", "remote_url": "https://github.com/org/repo"}
        )
        mock_merge.return_value = (False, ["src/main.py", "tests/test_main.py", "README.md"])

        result = run_pipeline(CommitPushInput())

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_MERGE_CONFLICT
        assert result.error.recoverable is True
        assert "Resolve conflicts" in result.error.suggested_action

        conflicts = result.data["conflicts"]
        assert len(conflicts) == 3
        assert "src/main.py" in conflicts
        assert "tests/test_main.py" in conflicts
        assert "README.md" in conflicts

        # Verify abort was called
        mock_abort.assert_called_once()
