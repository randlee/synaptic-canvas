"""Tests for PR provider abstraction.

Tests cover:
- Pydantic model validation
- GitHub provider using mocked gh CLI
- Azure DevOps provider using mocked requests
- Factory function
- Error handling for both providers
"""

import json
import os
import subprocess
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import requests

# Add the scripts directory to path for imports
import sys
sys.path.insert(0, str(__file__).replace("/tests/test_pr_provider.py", "/.claude/scripts"))

from pr_provider import (
    PullRequestInfo,
    PrCheckResult,
    PrCreateResult,
    ProviderInfo,
    PrProvider,
    PrProviderError,
    GitHubProvider,
    AzureDevOpsProvider,
    get_provider,
)
from envelope import ErrorCodes


# =============================================================================
# Pydantic Model Tests
# =============================================================================

class TestPullRequestInfo:
    """Tests for PullRequestInfo model."""

    def test_valid_pull_request_info(self):
        """Test creating a valid PullRequestInfo."""
        pr = PullRequestInfo(
            id="123",
            url="https://github.com/org/repo/pull/123",
            source_branch="feature-x",
            destination_branch="main",
            provider="github"
        )
        assert pr.id == "123"
        assert pr.url == "https://github.com/org/repo/pull/123"
        assert pr.source_branch == "feature-x"
        assert pr.destination_branch == "main"
        assert pr.provider == "github"

    def test_pull_request_info_serialization(self):
        """Test PullRequestInfo serializes to JSON correctly."""
        pr = PullRequestInfo(
            id="456",
            url="https://dev.azure.com/org/project/_git/repo/pullrequest/456",
            source_branch="feature-y",
            destination_branch="develop",
            provider="azuredevops"
        )
        data = pr.model_dump()
        assert data == {
            "id": "456",
            "url": "https://dev.azure.com/org/project/_git/repo/pullrequest/456",
            "source_branch": "feature-y",
            "destination_branch": "develop",
            "provider": "azuredevops"
        }


class TestPrCheckResult:
    """Tests for PrCheckResult model."""

    def test_pr_exists_with_info(self):
        """Test PrCheckResult when PR exists."""
        pr_info = PullRequestInfo(
            id="123",
            url="https://github.com/org/repo/pull/123",
            source_branch="feature-x",
            destination_branch="main",
            provider="github"
        )
        result = PrCheckResult(exists=True, pr=pr_info)
        assert result.exists is True
        assert result.pr is not None
        assert result.pr.id == "123"

    def test_pr_not_exists(self):
        """Test PrCheckResult when PR does not exist."""
        result = PrCheckResult(exists=False)
        assert result.exists is False
        assert result.pr is None


class TestPrCreateResult:
    """Tests for PrCreateResult model."""

    def test_create_result(self):
        """Test PrCreateResult with PR info."""
        pr_info = PullRequestInfo(
            id="789",
            url="https://github.com/org/repo/pull/789",
            source_branch="feature-z",
            destination_branch="main",
            provider="github"
        )
        result = PrCreateResult(pr=pr_info)
        assert result.pr.id == "789"


class TestProviderInfo:
    """Tests for ProviderInfo model."""

    def test_github_provider_info(self):
        """Test ProviderInfo for GitHub."""
        info = ProviderInfo(
            provider="github",
            org="myorg",
            repo="myrepo",
            remote_url="https://github.com/myorg/myrepo"
        )
        assert info.provider == "github"
        assert info.org == "myorg"
        assert info.repo == "myrepo"
        assert info.project is None

    def test_azure_provider_info(self):
        """Test ProviderInfo for Azure DevOps."""
        info = ProviderInfo(
            provider="azuredevops",
            org="myorg",
            project="myproject",
            repo="myrepo",
            remote_url="https://dev.azure.com/myorg/myproject/_git/myrepo"
        )
        assert info.provider == "azuredevops"
        assert info.org == "myorg"
        assert info.project == "myproject"
        assert info.repo == "myrepo"


# =============================================================================
# PrProviderError Tests
# =============================================================================

class TestPrProviderError:
    """Tests for PrProviderError exception."""

    def test_error_creation(self):
        """Test creating PrProviderError."""
        error = PrProviderError(
            code=ErrorCodes.PR_CREATE_FAILED,
            message="Failed to create PR",
            recoverable=False,
            suggested_action="Check permissions"
        )
        assert error.code == ErrorCodes.PR_CREATE_FAILED
        assert error.message == "Failed to create PR"
        assert error.recoverable is False
        assert error.suggested_action == "Check permissions"

    def test_error_to_envelope(self):
        """Test converting error to envelope format."""
        error = PrProviderError(
            code=ErrorCodes.GIT_AUTH,
            message="Auth failed",
            recoverable=True,
            suggested_action="Re-authenticate"
        )
        envelope = error.to_envelope(data={"extra": "info"})
        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.GIT_AUTH
        assert envelope.error.message == "Auth failed"
        assert envelope.error.recoverable is True
        assert envelope.data == {"extra": "info"}


# =============================================================================
# GitHub Provider Tests
# =============================================================================

class TestGitHubProvider:
    """Tests for GitHubProvider."""

    @pytest.fixture
    def provider(self):
        """Create a GitHub provider instance."""
        return GitHubProvider(org="testorg", repo="testrepo")

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.org == "testorg"
        assert provider.repo == "testrepo"
        assert provider.provider_name == "github"

    @patch("subprocess.run")
    def test_check_pr_exists_found(self, mock_run, provider):
        """Test check_pr_exists when PR is found."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps([{
                "number": 42,
                "url": "https://github.com/testorg/testrepo/pull/42",
                "headRefName": "feature-branch",
                "baseRefName": "main"
            }]),
            stderr=""
        )

        result = provider.check_pr_exists("feature-branch", "main")

        assert result.exists is True
        assert result.pr is not None
        assert result.pr.id == "42"
        assert result.pr.url == "https://github.com/testorg/testrepo/pull/42"
        assert result.pr.source_branch == "feature-branch"
        assert result.pr.destination_branch == "main"
        assert result.pr.provider == "github"

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "list" in call_args
        assert "--head" in call_args
        assert "feature-branch" in call_args

    @patch("subprocess.run")
    def test_check_pr_exists_not_found(self, mock_run, provider):
        """Test check_pr_exists when no PR exists."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="[]",
            stderr=""
        )

        result = provider.check_pr_exists("feature-branch", "main")

        assert result.exists is False
        assert result.pr is None

    @patch("subprocess.run")
    def test_check_pr_exists_command_fails(self, mock_run, provider):
        """Test check_pr_exists when gh command fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="gh auth error"
        )

        result = provider.check_pr_exists("feature-branch", "main")

        # Should return not found, not raise an error
        assert result.exists is False
        assert result.pr is None

    @patch("subprocess.run")
    def test_create_pr_success(self, mock_run, provider):
        """Test successful PR creation."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="https://github.com/testorg/testrepo/pull/99\n",
            stderr=""
        )

        result = provider.create_pr(
            title="My PR Title",
            body="PR description",
            source_branch="feature-x",
            destination_branch="main"
        )

        assert result.pr.id == "99"
        assert result.pr.url == "https://github.com/testorg/testrepo/pull/99"
        assert result.pr.source_branch == "feature-x"
        assert result.pr.destination_branch == "main"
        assert result.pr.provider == "github"

        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "create" in call_args
        assert "--title" in call_args
        assert "My PR Title" in call_args

    @patch("subprocess.run")
    def test_create_pr_failure(self, mock_run, provider):
        """Test PR creation failure."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Permission denied"
        )

        with pytest.raises(PrProviderError) as exc_info:
            provider.create_pr(
                title="My PR",
                body="Description",
                source_branch="feature",
                destination_branch="main"
            )

        assert exc_info.value.code == ErrorCodes.PR_CREATE_FAILED
        assert "Permission denied" in exc_info.value.message

    @patch("subprocess.run")
    def test_get_pr_info_success(self, mock_run, provider):
        """Test getting PR info."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({
                "number": 55,
                "url": "https://github.com/testorg/testrepo/pull/55",
                "headRefName": "bugfix",
                "baseRefName": "develop"
            }),
            stderr=""
        )

        result = provider.get_pr_info("55")

        assert result.id == "55"
        assert result.source_branch == "bugfix"
        assert result.destination_branch == "develop"

    @patch("subprocess.run")
    def test_get_pr_info_not_found(self, mock_run, provider):
        """Test get_pr_info when PR not found."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Could not resolve to a PullRequest"
        )

        with pytest.raises(PrProviderError) as exc_info:
            provider.get_pr_info("999")

        assert exc_info.value.code == ErrorCodes.PR_CREATE_FAILED

    @patch("subprocess.run")
    def test_gh_cli_not_found(self, mock_run, provider):
        """Test when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("gh not found")

        with pytest.raises(PrProviderError) as exc_info:
            provider.check_pr_exists("branch", "main")

        assert exc_info.value.code == ErrorCodes.PROVIDER_UNSUPPORTED
        assert "gh CLI not found" in exc_info.value.message


# =============================================================================
# Azure DevOps Provider Tests
# =============================================================================

class TestAzureDevOpsProvider:
    """Tests for AzureDevOpsProvider."""

    @pytest.fixture
    def provider(self):
        """Create an Azure DevOps provider instance."""
        return AzureDevOpsProvider(
            org="testorg",
            project="testproject",
            repo="testrepo"
        )

    @pytest.fixture
    def mock_env_pat(self):
        """Mock the AZURE_DEVOPS_PAT environment variable."""
        with patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat-token"}):
            yield

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.org == "testorg"
        assert provider.project == "testproject"
        assert provider.repo == "testrepo"
        assert provider.provider_name == "azuredevops"
        assert "dev.azure.com" in provider.base_url

    def test_get_pat_missing(self, provider):
        """Test error when PAT is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove AZURE_DEVOPS_PAT if present
            os.environ.pop("AZURE_DEVOPS_PAT", None)

            with pytest.raises(PrProviderError) as exc_info:
                provider._get_pat()

            assert exc_info.value.code == ErrorCodes.GIT_AUTH
            assert "AZURE_DEVOPS_PAT" in exc_info.value.message

    def test_normalize_branch_ref(self, provider):
        """Test branch ref normalization."""
        assert provider._normalize_branch_ref("main") == "refs/heads/main"
        assert provider._normalize_branch_ref("refs/heads/main") == "refs/heads/main"
        assert provider._normalize_branch_ref("feature/test") == "refs/heads/feature/test"

    def test_extract_branch_name(self, provider):
        """Test extracting branch name from ref."""
        assert provider._extract_branch_name("refs/heads/main") == "main"
        assert provider._extract_branch_name("refs/heads/feature/test") == "feature/test"
        assert provider._extract_branch_name("main") == "main"

    @patch("requests.request")
    def test_check_pr_exists_found(self, mock_request, provider, mock_env_pat):
        """Test check_pr_exists when PR is found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "value": [{
                "pullRequestId": 123,
                "sourceRefName": "refs/heads/feature-branch",
                "targetRefName": "refs/heads/main"
            }]
        }
        mock_request.return_value = mock_response

        result = provider.check_pr_exists("feature-branch", "main")

        assert result.exists is True
        assert result.pr is not None
        assert result.pr.id == "123"
        assert result.pr.source_branch == "feature-branch"
        assert result.pr.destination_branch == "main"
        assert result.pr.provider == "azuredevops"

    @patch("requests.request")
    def test_check_pr_exists_not_found(self, mock_request, provider, mock_env_pat):
        """Test check_pr_exists when no PR exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response

        result = provider.check_pr_exists("feature-branch", "main")

        assert result.exists is False
        assert result.pr is None

    @patch("requests.request")
    def test_create_pr_success(self, mock_request, provider, mock_env_pat):
        """Test successful PR creation."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.ok = True
        mock_response.json.return_value = {
            "pullRequestId": 456,
            "sourceRefName": "refs/heads/feature-x",
            "targetRefName": "refs/heads/main"
        }
        mock_request.return_value = mock_response

        result = provider.create_pr(
            title="My Azure PR",
            body="Description here",
            source_branch="feature-x",
            destination_branch="main"
        )

        assert result.pr.id == "456"
        assert result.pr.source_branch == "feature-x"
        assert result.pr.destination_branch == "main"
        assert result.pr.provider == "azuredevops"
        assert "dev.azure.com" in result.pr.url

        # Verify the request was made correctly
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "pullrequests" in call_kwargs["url"]
        assert call_kwargs["json"]["title"] == "My Azure PR"

    @patch("requests.request")
    def test_create_pr_auth_failure(self, mock_request, provider, mock_env_pat):
        """Test PR creation with auth failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.ok = False
        mock_request.return_value = mock_response

        with pytest.raises(PrProviderError) as exc_info:
            provider.create_pr(
                title="My PR",
                body="Desc",
                source_branch="feature",
                destination_branch="main"
            )

        assert exc_info.value.code == ErrorCodes.GIT_AUTH

    @patch("requests.request")
    def test_get_pr_info_success(self, mock_request, provider, mock_env_pat):
        """Test getting PR info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "pullRequestId": 789,
            "sourceRefName": "refs/heads/bugfix",
            "targetRefName": "refs/heads/develop"
        }
        mock_request.return_value = mock_response

        result = provider.get_pr_info("789")

        assert result.id == "789"
        assert result.source_branch == "bugfix"
        assert result.destination_branch == "develop"

    @patch("requests.request")
    def test_get_pr_info_not_found(self, mock_request, provider, mock_env_pat):
        """Test get_pr_info when PR not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_request.return_value = mock_response

        with pytest.raises(PrProviderError) as exc_info:
            provider.get_pr_info("999")

        assert exc_info.value.code == ErrorCodes.PR_NOT_FOUND

    @patch("requests.request")
    def test_network_error(self, mock_request, provider, mock_env_pat):
        """Test handling of network errors."""
        mock_request.side_effect = requests.RequestException("Connection failed")

        # Network errors should raise when creating PRs
        with pytest.raises(PrProviderError) as exc_info:
            provider.create_pr(
                title="Test PR",
                body="Description",
                source_branch="feature",
                destination_branch="main"
            )

        assert exc_info.value.code == ErrorCodes.GIT_REMOTE
        assert exc_info.value.recoverable is True

    @patch("requests.request")
    def test_check_pr_exists_network_error_returns_false(self, mock_request, provider, mock_env_pat):
        """Test that check_pr_exists returns False on network errors (graceful degradation)."""
        mock_request.side_effect = requests.RequestException("Connection failed")

        # check_pr_exists should gracefully return False on errors
        result = provider.check_pr_exists("branch", "main")
        assert result.exists is False


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestGetProvider:
    """Tests for the get_provider factory function."""

    def test_create_github_provider(self):
        """Test creating a GitHub provider."""
        info = ProviderInfo(
            provider="github",
            org="myorg",
            repo="myrepo",
            remote_url="https://github.com/myorg/myrepo"
        )
        provider = get_provider(info)

        assert isinstance(provider, GitHubProvider)
        assert provider.org == "myorg"
        assert provider.repo == "myrepo"

    def test_create_azure_provider(self):
        """Test creating an Azure DevOps provider."""
        info = ProviderInfo(
            provider="azuredevops",
            org="myorg",
            project="myproject",
            repo="myrepo",
            remote_url="https://dev.azure.com/myorg/myproject/_git/myrepo"
        )
        provider = get_provider(info)

        assert isinstance(provider, AzureDevOpsProvider)
        assert provider.org == "myorg"
        assert provider.project == "myproject"
        assert provider.repo == "myrepo"

    def test_azure_without_project_fails(self):
        """Test that Azure DevOps without project raises error."""
        info = ProviderInfo(
            provider="azuredevops",
            org="myorg",
            repo="myrepo",
            remote_url="https://dev.azure.com/myorg/_git/myrepo"  # Missing project
        )

        with pytest.raises(PrProviderError) as exc_info:
            get_provider(info)

        assert exc_info.value.code == ErrorCodes.PROVIDER_DETECT_FAILED
        assert "project" in exc_info.value.message.lower()

    def test_unsupported_provider(self):
        """Test unsupported provider raises error."""
        # ProviderInfo from provider_detect uses str for provider, so we can test directly
        info = ProviderInfo(
            provider="gitlab",  # Not supported
            org="myorg",
            repo="myrepo",
            remote_url="https://gitlab.com/myorg/myrepo"
        )

        with pytest.raises(PrProviderError) as exc_info:
            get_provider(info)

        assert exc_info.value.code == ErrorCodes.PROVIDER_UNSUPPORTED


# =============================================================================
# Integration-Style Tests
# =============================================================================

class TestProviderWorkflows:
    """Test common provider workflows."""

    @patch("subprocess.run")
    def test_github_check_then_create_workflow(self, mock_run):
        """Test typical GitHub workflow: check if exists, then create."""
        provider = GitHubProvider(org="acme", repo="project")

        # First call: check_pr_exists returns no PR
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr=""
        )
        check_result = provider.check_pr_exists("feature", "main")
        assert check_result.exists is False

        # Second call: create_pr succeeds
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="https://github.com/acme/project/pull/100\n",
            stderr=""
        )
        create_result = provider.create_pr(
            title="New Feature",
            body="Adds cool stuff",
            source_branch="feature",
            destination_branch="main"
        )
        assert create_result.pr.id == "100"

    @patch("requests.request")
    def test_azure_check_existing_pr_workflow(self, mock_request):
        """Test Azure workflow: check and find existing PR."""
        provider = AzureDevOpsProvider(org="acme", project="myproj", repo="myrepo")

        with patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-token"}):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = {
                "value": [{
                    "pullRequestId": 50,
                    "sourceRefName": "refs/heads/hotfix",
                    "targetRefName": "refs/heads/main"
                }]
            }
            mock_request.return_value = mock_response

            result = provider.check_pr_exists("hotfix", "main")

            assert result.exists is True
            assert result.pr.id == "50"
            # Workflow would stop here, no need to create PR
