"""Tests for create_pr.py.

Comprehensive test coverage for PR creation script including:
- Successful PR creation (GitHub and Azure DevOps)
- Provider detection failure handling
- PR creation failure (API errors)
- Input validation
- CLI interface
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "packages" / "sc-commit-push-pr" / "scripts"
sys.path.insert(0, str(scripts_dir))

from create_pr import CreatePrInput, CreatePrData, main
from envelope import Envelope, ErrorCodes
from pr_provider import (
    PrCreateResult,
    PrProviderError,
    PullRequestInfo,
    GitHubProvider,
    AzureDevOpsProvider,
)
from provider_detect import ProviderInfo


# =============================================================================
# Input Model Tests
# =============================================================================


class TestCreatePrInput:
    """Tests for CreatePrInput Pydantic model."""

    def test_valid_input(self):
        """Test creating valid input model."""
        input_data = CreatePrInput(
            title="My PR Title",
            body="PR description here",
            source="feature-branch",
            destination="main",
        )
        assert input_data.title == "My PR Title"
        assert input_data.body == "PR description here"
        assert input_data.source == "feature-branch"
        assert input_data.destination == "main"

    def test_input_from_dict(self):
        """Test creating input from dictionary."""
        data = {
            "title": "Test PR",
            "body": "Test body",
            "source": "develop",
            "destination": "main",
        }
        input_data = CreatePrInput(**data)
        assert input_data.title == "Test PR"
        assert input_data.source == "develop"

    def test_missing_title_raises(self):
        """Test that missing title raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            CreatePrInput(
                body="Body",
                source="feature",
                destination="main",
            )

    def test_missing_body_raises(self):
        """Test that missing body raises validation error."""
        with pytest.raises(Exception):
            CreatePrInput(
                title="Title",
                source="feature",
                destination="main",
            )

    def test_missing_source_raises(self):
        """Test that missing source raises validation error."""
        with pytest.raises(Exception):
            CreatePrInput(
                title="Title",
                body="Body",
                destination="main",
            )

    def test_missing_destination_raises(self):
        """Test that missing destination raises validation error."""
        with pytest.raises(Exception):
            CreatePrInput(
                title="Title",
                body="Body",
                source="feature",
            )

    def test_empty_strings_allowed(self):
        """Test that empty strings are allowed (validation is minimal)."""
        input_data = CreatePrInput(
            title="",
            body="",
            source="feature",
            destination="main",
        )
        assert input_data.title == ""
        assert input_data.body == ""

    def test_model_dump(self):
        """Test model serialization."""
        input_data = CreatePrInput(
            title="PR Title",
            body="Body text",
            source="src",
            destination="dest",
        )
        data = input_data.model_dump()
        assert data == {
            "title": "PR Title",
            "body": "Body text",
            "source": "src",
            "destination": "dest",
        }


# =============================================================================
# Successful PR Creation Tests
# =============================================================================


class TestSuccessfulPrCreationGitHub:
    """Tests for successful PR creation with GitHub provider."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_create_pr_github_success(self, mock_get_provider, mock_get_remote):
        """Test successful PR creation on GitHub."""
        # Setup mocks
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="123",
                url="https://github.com/myorg/myrepo/pull/123",
                source_branch="feature-branch",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        # Execute
        result = main(
            title="Add new feature",
            body="This PR adds a cool new feature",
            source="feature-branch",
            destination="main",
        )

        # Verify
        assert result.success is True
        assert result.data is not None
        assert "pr" in result.data
        assert result.data["pr"]["id"] == "123"
        assert result.data["pr"]["url"] == "https://github.com/myorg/myrepo/pull/123"
        assert result.data["pr"]["source_branch"] == "feature-branch"
        assert result.data["pr"]["destination_branch"] == "main"
        assert result.data["pr"]["provider"] == "github"

        # Verify provider was called correctly
        mock_provider.create_pr.assert_called_once_with(
            "Add new feature",
            "This PR adds a cool new feature",
            "feature-branch",
            "main",
        )

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_create_pr_with_explicit_remote_url(self, mock_get_provider, mock_get_remote):
        """Test PR creation with explicitly provided remote URL."""
        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="456",
                url="https://github.com/other/repo/pull/456",
                source_branch="hotfix",
                destination_branch="develop",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        # Execute with explicit remote URL
        result = main(
            title="Hotfix",
            body="Urgent fix",
            source="hotfix",
            destination="develop",
            remote_url="https://github.com/other/repo",
        )

        # Verify - get_remote_url should not be called
        mock_get_remote.assert_not_called()
        assert result.success is True
        assert result.data["pr"]["id"] == "456"

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_create_pr_ssh_url(self, mock_get_provider, mock_get_remote):
        """Test PR creation with SSH remote URL."""
        mock_get_remote.return_value = "git@github.com:myorg/myrepo.git"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="789",
                url="https://github.com/myorg/myrepo/pull/789",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="SSH Test",
            body="Testing SSH URL",
            source="feature",
            destination="main",
        )

        assert result.success is True
        assert result.data["pr"]["id"] == "789"


class TestSuccessfulPrCreationAzureDevOps:
    """Tests for successful PR creation with Azure DevOps provider."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_create_pr_azure_success(self, mock_get_provider, mock_get_remote):
        """Test successful PR creation on Azure DevOps."""
        mock_get_remote.return_value = (
            "https://dev.azure.com/myorg/myproject/_git/myrepo"
        )

        mock_provider = MagicMock(spec=AzureDevOpsProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="100",
                url="https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/100",
                source_branch="feature-azure",
                destination_branch="main",
                provider="azuredevops",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Azure PR",
            body="Testing Azure DevOps integration",
            source="feature-azure",
            destination="main",
        )

        assert result.success is True
        assert result.data["pr"]["id"] == "100"
        assert result.data["pr"]["provider"] == "azuredevops"
        assert "dev.azure.com" in result.data["pr"]["url"]

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_create_pr_azure_legacy_url(self, mock_get_provider, mock_get_remote):
        """Test PR creation with legacy Azure DevOps (visualstudio.com) URL."""
        mock_get_remote.return_value = (
            "https://myorg.visualstudio.com/myproject/_git/myrepo"
        )

        mock_provider = MagicMock(spec=AzureDevOpsProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="200",
                url="https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/200",
                source_branch="legacy-feature",
                destination_branch="develop",
                provider="azuredevops",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Legacy Azure PR",
            body="Testing legacy URL",
            source="legacy-feature",
            destination="develop",
        )

        assert result.success is True
        assert result.data["pr"]["id"] == "200"


# =============================================================================
# Provider Detection Failure Tests
# =============================================================================


class TestProviderDetectionFailure:
    """Tests for provider detection failure scenarios."""

    @patch("create_pr.get_remote_url")
    def test_no_remote_url(self, mock_get_remote):
        """Test error when no remote URL can be obtained."""
        mock_get_remote.return_value = None

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE
        assert "Could not get remote URL" in result.error.message
        assert result.error.suggested_action is not None

    @patch("create_pr.get_remote_url")
    def test_unsupported_provider(self, mock_get_remote):
        """Test error when remote URL is from unsupported provider."""
        mock_get_remote.return_value = "https://gitlab.com/myorg/myrepo"

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED
        assert "Could not detect provider" in result.error.message

    @patch("create_pr.get_remote_url")
    def test_malformed_remote_url(self, mock_get_remote):
        """Test error when remote URL is malformed."""
        mock_get_remote.return_value = "not-a-valid-url"

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    @patch("create_pr.get_remote_url")
    def test_empty_remote_url(self, mock_get_remote):
        """Test error when remote URL is empty string."""
        mock_get_remote.return_value = ""

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE


# =============================================================================
# PR Creation Failure Tests
# =============================================================================


class TestPrCreationFailure:
    """Tests for PR creation failure scenarios."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_pr_create_api_error(self, mock_get_provider, mock_get_remote):
        """Test handling of PR creation API error."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.side_effect = PrProviderError(
            code=ErrorCodes.PR_CREATE_FAILED,
            message="Permission denied - no push access",
            recoverable=False,
            suggested_action="Check repository permissions",
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PR_CREATE_FAILED
        assert "Permission denied" in result.error.message
        assert result.error.suggested_action == "Check repository permissions"

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_pr_already_exists_error(self, mock_get_provider, mock_get_remote):
        """Test handling when PR already exists."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.side_effect = PrProviderError(
            code=ErrorCodes.PR_ALREADY_EXISTS,
            message="A PR already exists for this branch",
            recoverable=False,
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PR_ALREADY_EXISTS

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_auth_failure(self, mock_get_provider, mock_get_remote):
        """Test handling of authentication failure."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.side_effect = PrProviderError(
            code=ErrorCodes.GIT_AUTH,
            message="Authentication failed",
            recoverable=False,
            suggested_action="Check your credentials or token",
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_AUTH
        assert "Authentication failed" in result.error.message

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_network_error_recoverable(self, mock_get_provider, mock_get_remote):
        """Test handling of network error (recoverable)."""
        mock_get_remote.return_value = "https://dev.azure.com/myorg/myproject/_git/myrepo"

        mock_provider = MagicMock(spec=AzureDevOpsProvider)
        mock_provider.create_pr.side_effect = PrProviderError(
            code=ErrorCodes.GIT_REMOTE,
            message="Connection timed out",
            recoverable=True,
            suggested_action="Check network connectivity and retry",
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.GIT_REMOTE
        assert result.error.recoverable is True

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_unexpected_exception(self, mock_get_provider, mock_get_remote):
        """Test handling of unexpected exception during PR creation."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.side_effect = RuntimeError("Unexpected error")
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PR_CREATE_FAILED
        assert "Unexpected error" in result.error.message


class TestProviderCreationFailure:
    """Tests for provider instantiation failure."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_provider_creation_error(self, mock_get_provider, mock_get_remote):
        """Test error when provider cannot be created."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_get_provider.side_effect = PrProviderError(
            code=ErrorCodes.PROVIDER_UNSUPPORTED,
            message="gh CLI not found",
            recoverable=False,
            suggested_action="Install gh CLI",
        )

        result = main(
            title="Test PR",
            body="Test body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_UNSUPPORTED
        assert "gh CLI" in result.error.message


# =============================================================================
# Envelope Output Format Tests
# =============================================================================


class TestEnvelopeOutput:
    """Tests for correct envelope output format."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_success_envelope_structure(self, mock_get_provider, mock_get_remote):
        """Test success envelope has correct structure."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="123",
                url="https://github.com/myorg/myrepo/pull/123",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test",
            body="Body",
            source="feature",
            destination="main",
        )

        assert result.success is True
        assert result.data is not None
        assert result.error is None
        assert "pr" in result.data
        assert "id" in result.data["pr"]
        assert "url" in result.data["pr"]
        assert "source_branch" in result.data["pr"]
        assert "destination_branch" in result.data["pr"]
        assert "provider" in result.data["pr"]

    @patch("create_pr.get_remote_url")
    def test_error_envelope_structure(self, mock_get_remote):
        """Test error envelope has correct structure."""
        mock_get_remote.return_value = None

        result = main(
            title="Test",
            body="Body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.code is not None
        assert result.error.message is not None

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_fenced_json_output(self, mock_get_provider, mock_get_remote):
        """Test fenced JSON output format."""
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="123",
                url="https://github.com/myorg/myrepo/pull/123",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Test",
            body="Body",
            source="feature",
            destination="main",
        )

        fenced = result.to_fenced_json()
        assert fenced.startswith("```json\n")
        assert fenced.endswith("\n```")
        assert '"success": true' in fenced
        assert '"pr"' in fenced


# =============================================================================
# CLI Interface Tests
# =============================================================================


class TestCLIInterface:
    """Tests for command-line interface."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_cli_with_json_arg(self, mock_get_provider, mock_get_remote):
        """Test CLI accepts JSON argument."""
        # This is tested by importing and calling the module directly
        # Full subprocess test would require actual environment setup
        mock_get_remote.return_value = "https://github.com/myorg/myrepo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="42",
                url="https://github.com/myorg/myrepo/pull/42",
                source_branch="cli-test",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        # Simulate CLI input parsing
        input_json = '{"title": "CLI Test", "body": "Testing CLI", "source": "cli-test", "destination": "main"}'
        data = json.loads(input_json)
        input_data = CreatePrInput(**data)

        result = main(
            input_data.title, input_data.body, input_data.source, input_data.destination
        )

        assert result.success is True
        assert result.data["pr"]["id"] == "42"

    def test_input_validation_missing_fields(self):
        """Test input validation catches missing required fields."""
        invalid_inputs = [
            {"body": "b", "source": "s", "destination": "d"},  # missing title
            {"title": "t", "source": "s", "destination": "d"},  # missing body
            {"title": "t", "body": "b", "destination": "d"},  # missing source
            {"title": "t", "body": "b", "source": "s"},  # missing destination
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(Exception):
                CreatePrInput(**invalid_input)

    def test_input_json_parsing(self):
        """Test JSON input parsing."""
        valid_json = json.dumps(
            {
                "title": "JSON Test",
                "body": "Body here",
                "source": "feature",
                "destination": "main",
            }
        )
        data = json.loads(valid_json)
        input_data = CreatePrInput(**data)

        assert input_data.title == "JSON Test"
        assert input_data.body == "Body here"
        assert input_data.source == "feature"
        assert input_data.destination == "main"

    def test_invalid_json_raises(self):
        """Test invalid JSON raises error."""
        invalid_json = "not valid json {"
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestIntegrationWorkflows:
    """Integration-style tests for typical workflows."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_full_workflow_github(self, mock_get_provider, mock_get_remote):
        """Test complete workflow from input to output for GitHub."""
        # Setup
        mock_get_remote.return_value = "git@github.com:company/project.git"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="999",
                url="https://github.com/company/project/pull/999",
                source_branch="feature/new-thing",
                destination_branch="develop",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        # Execute
        result = main(
            title="Add new feature",
            body="## Summary\n- Added new capability\n- Updated tests",
            source="feature/new-thing",
            destination="develop",
        )

        # Verify complete workflow
        assert result.success is True
        pr_data = result.data["pr"]
        assert pr_data["id"] == "999"
        assert pr_data["url"] == "https://github.com/company/project/pull/999"
        assert pr_data["source_branch"] == "feature/new-thing"
        assert pr_data["destination_branch"] == "develop"
        assert pr_data["provider"] == "github"

        # Verify provider was called with full markdown body
        mock_provider.create_pr.assert_called_once()
        call_args = mock_provider.create_pr.call_args
        assert call_args[0][0] == "Add new feature"
        assert "## Summary" in call_args[0][1]

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_full_workflow_azure(self, mock_get_provider, mock_get_remote):
        """Test complete workflow from input to output for Azure DevOps."""
        # Setup
        mock_get_remote.return_value = "https://dev.azure.com/enterprise/BigProject/_git/core-api"

        mock_provider = MagicMock(spec=AzureDevOpsProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="5000",
                url="https://dev.azure.com/enterprise/BigProject/_git/core-api/pullrequest/5000",
                source_branch="users/jdoe/hotfix",
                destination_branch="release/v2",
                provider="azuredevops",
            )
        )
        mock_get_provider.return_value = mock_provider

        # Execute
        result = main(
            title="Hotfix: Fix critical bug",
            body="Fixes issue ABC-1234",
            source="users/jdoe/hotfix",
            destination="release/v2",
        )

        # Verify
        assert result.success is True
        assert result.data["pr"]["provider"] == "azuredevops"
        assert "dev.azure.com" in result.data["pr"]["url"]

    @patch("create_pr.get_remote_url")
    def test_workflow_with_provider_not_found(self, mock_get_remote):
        """Test workflow when provider cannot be determined."""
        mock_get_remote.return_value = "https://bitbucket.org/team/repo.git"

        result = main(
            title="Test PR",
            body="Body",
            source="feature",
            destination="main",
        )

        assert result.success is False
        assert result.error is not None
        # Should fail at provider detection
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_pr_with_special_characters_in_title(self, mock_get_provider, mock_get_remote):
        """Test PR creation with special characters in title."""
        mock_get_remote.return_value = "https://github.com/org/repo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="1",
                url="https://github.com/org/repo/pull/1",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title='Fix: Handle "quotes" & <special> chars',
            body="Body with\nnewlines\nand\ttabs",
            source="feature",
            destination="main",
        )

        assert result.success is True

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_pr_with_unicode_content(self, mock_get_provider, mock_get_remote):
        """Test PR creation with unicode content."""
        mock_get_remote.return_value = "https://github.com/org/repo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="2",
                url="https://github.com/org/repo/pull/2",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="feat: Add internationalization support",
            body="Adds support for: cafe, resume, nino",
            source="feature",
            destination="main",
        )

        assert result.success is True

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_pr_with_long_body(self, mock_get_provider, mock_get_remote):
        """Test PR creation with very long body."""
        mock_get_remote.return_value = "https://github.com/org/repo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="3",
                url="https://github.com/org/repo/pull/3",
                source_branch="feature",
                destination_branch="main",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        long_body = "This is a very detailed description.\n" * 100

        result = main(
            title="Big changes",
            body=long_body,
            source="feature",
            destination="main",
        )

        assert result.success is True
        mock_provider.create_pr.assert_called_once()
        actual_body = mock_provider.create_pr.call_args[0][1]
        assert len(actual_body) == len(long_body)

    @patch("create_pr.get_remote_url")
    @patch("create_pr.get_provider")
    def test_branch_names_with_slashes(self, mock_get_provider, mock_get_remote):
        """Test branch names containing slashes."""
        mock_get_remote.return_value = "https://github.com/org/repo"

        mock_provider = MagicMock(spec=GitHubProvider)
        mock_provider.create_pr.return_value = PrCreateResult(
            pr=PullRequestInfo(
                id="4",
                url="https://github.com/org/repo/pull/4",
                source_branch="feature/user/jdoe/big-feature",
                destination_branch="release/v1.0",
                provider="github",
            )
        )
        mock_get_provider.return_value = mock_provider

        result = main(
            title="Release PR",
            body="Ready for release",
            source="feature/user/jdoe/big-feature",
            destination="release/v1.0",
        )

        assert result.success is True
        assert result.data["pr"]["source_branch"] == "feature/user/jdoe/big-feature"
        assert result.data["pr"]["destination_branch"] == "release/v1.0"
