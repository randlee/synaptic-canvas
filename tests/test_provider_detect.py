"""Tests for provider_detect.py.

Comprehensive test coverage for GitHub and Azure DevOps URL parsing.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "packages" / "sc-commit-push-pr" / "scripts"
sys.path.insert(0, str(scripts_dir))

from envelope import ErrorCodes
from provider_detect import (
    AZURE_HTTPS_PATTERN,
    AZURE_LEGACY_HTTPS_PATTERN,
    AZURE_LEGACY_SSH_PATTERN,
    AZURE_SSH_PATTERN,
    GITHUB_HTTPS_PATTERN,
    GITHUB_SSH_PATTERN,
    ProviderInfo,
    detect_provider,
    get_remote_url,
    main,
    parse_azure_url,
    parse_github_url,
)


class TestProviderInfoModel:
    """Tests for the ProviderInfo Pydantic model."""

    def test_github_provider_info(self):
        """Test creating ProviderInfo for GitHub."""
        info = ProviderInfo(
            provider="github",
            org="myorg",
            repo="myrepo",
            remote_url="https://github.com/myorg/myrepo",
        )
        assert info.provider == "github"
        assert info.org == "myorg"
        assert info.repo == "myrepo"
        assert info.project is None
        assert info.remote_url == "https://github.com/myorg/myrepo"

    def test_azure_provider_info(self):
        """Test creating ProviderInfo for Azure DevOps."""
        info = ProviderInfo(
            provider="azuredevops",
            org="myorg",
            project="myproject",
            repo="myrepo",
            remote_url="https://dev.azure.com/myorg/myproject/_git/myrepo",
        )
        assert info.provider == "azuredevops"
        assert info.org == "myorg"
        assert info.project == "myproject"
        assert info.repo == "myrepo"

    def test_model_dump(self):
        """Test model serialization."""
        info = ProviderInfo(
            provider="github",
            org="org",
            repo="repo",
            remote_url="https://github.com/org/repo",
        )
        data = info.model_dump()
        assert data["provider"] == "github"
        assert data["org"] == "org"
        assert data["repo"] == "repo"
        assert data["project"] is None


class TestGitHubHttpsUrls:
    """Tests for GitHub HTTPS URL parsing."""

    def test_basic_https_url(self):
        """Test basic GitHub HTTPS URL."""
        url = "https://github.com/myorg/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "github"
        assert result.data["org"] == "myorg"
        assert result.data["repo"] == "myrepo"
        assert result.data["project"] is None

    def test_https_url_with_git_suffix(self):
        """Test GitHub HTTPS URL with .git suffix."""
        url = "https://github.com/myorg/myrepo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "github"
        assert result.data["org"] == "myorg"
        assert result.data["repo"] == "myrepo"

    def test_https_url_with_trailing_slash(self):
        """Test GitHub HTTPS URL with trailing slash."""
        url = "https://github.com/myorg/myrepo/"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_https_url_with_git_suffix_and_trailing_slash(self):
        """Test GitHub HTTPS URL with .git suffix and trailing slash."""
        url = "https://github.com/myorg/myrepo.git/"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_http_url(self):
        """Test GitHub HTTP URL (non-secure)."""
        url = "http://github.com/myorg/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "github"

    def test_hyphenated_names(self):
        """Test GitHub URL with hyphenated org and repo names."""
        url = "https://github.com/my-org/my-repo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "my-org"
        assert result.data["repo"] == "my-repo"

    def test_underscored_names(self):
        """Test GitHub URL with underscored org and repo names."""
        url = "https://github.com/my_org/my_repo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "my_org"
        assert result.data["repo"] == "my_repo"

    def test_numeric_names(self):
        """Test GitHub URL with numeric characters in names."""
        url = "https://github.com/org123/repo456"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "org123"
        assert result.data["repo"] == "repo456"


class TestGitHubSshUrls:
    """Tests for GitHub SSH URL parsing."""

    def test_basic_ssh_url(self):
        """Test basic GitHub SSH URL."""
        url = "git@github.com:myorg/myrepo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "github"
        assert result.data["org"] == "myorg"
        assert result.data["repo"] == "myrepo"

    def test_ssh_url_without_git_suffix(self):
        """Test GitHub SSH URL without .git suffix."""
        url = "git@github.com:myorg/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_ssh_url_hyphenated_names(self):
        """Test GitHub SSH URL with hyphenated names."""
        url = "git@github.com:my-org/my-repo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "my-org"
        assert result.data["repo"] == "my-repo"


class TestAzureDevOpsHttpsUrls:
    """Tests for Azure DevOps HTTPS URL parsing."""

    def test_basic_https_url(self):
        """Test basic Azure DevOps HTTPS URL."""
        url = "https://dev.azure.com/myorg/myproject/_git/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "azuredevops"
        assert result.data["org"] == "myorg"
        assert result.data["project"] == "myproject"
        assert result.data["repo"] == "myrepo"

    def test_https_url_with_git_suffix(self):
        """Test Azure DevOps HTTPS URL with .git suffix."""
        url = "https://dev.azure.com/myorg/myproject/_git/myrepo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_https_url_with_trailing_slash(self):
        """Test Azure DevOps HTTPS URL with trailing slash."""
        url = "https://dev.azure.com/myorg/myproject/_git/myrepo/"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_http_url(self):
        """Test Azure DevOps HTTP URL (non-secure)."""
        url = "http://dev.azure.com/myorg/myproject/_git/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "azuredevops"

    def test_hyphenated_names(self):
        """Test Azure DevOps URL with hyphenated names."""
        url = "https://dev.azure.com/my-org/my-project/_git/my-repo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "my-org"
        assert result.data["project"] == "my-project"
        assert result.data["repo"] == "my-repo"

    def test_spaces_encoded(self):
        """Test Azure DevOps URL with space-containing project (URL encoded)."""
        url = "https://dev.azure.com/myorg/My%20Project/_git/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["project"] == "My%20Project"


class TestAzureDevOpsSshUrls:
    """Tests for Azure DevOps SSH URL parsing."""

    def test_basic_ssh_url(self):
        """Test basic Azure DevOps SSH URL."""
        url = "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "azuredevops"
        assert result.data["org"] == "myorg"
        assert result.data["project"] == "myproject"
        assert result.data["repo"] == "myrepo"

    def test_ssh_url_with_git_suffix(self):
        """Test Azure DevOps SSH URL with .git suffix."""
        url = "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_ssh_url_hyphenated_names(self):
        """Test Azure DevOps SSH URL with hyphenated names."""
        url = "git@ssh.dev.azure.com:v3/my-org/my-project/my-repo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == "my-org"
        assert result.data["project"] == "my-project"
        assert result.data["repo"] == "my-repo"


class TestAzureDevOpsLegacyUrls:
    """Tests for legacy Azure DevOps (visualstudio.com) URL parsing."""

    def test_legacy_https_url(self):
        """Test legacy Azure DevOps HTTPS URL."""
        url = "https://myorg.visualstudio.com/myproject/_git/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "azuredevops"
        assert result.data["org"] == "myorg"
        assert result.data["project"] == "myproject"
        assert result.data["repo"] == "myrepo"

    def test_legacy_https_url_with_git_suffix(self):
        """Test legacy Azure DevOps HTTPS URL with .git suffix."""
        url = "https://myorg.visualstudio.com/myproject/_git/myrepo.git"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["repo"] == "myrepo"

    def test_legacy_ssh_url(self):
        """Test legacy Azure DevOps SSH URL."""
        url = "myorg@vs-ssh.visualstudio.com:v3/myorg/myproject/myrepo"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["provider"] == "azuredevops"
        assert result.data["org"] == "myorg"
        assert result.data["project"] == "myproject"
        assert result.data["repo"] == "myrepo"


class TestInvalidUrls:
    """Tests for invalid URL handling."""

    def test_empty_url(self):
        """Test empty URL returns error."""
        result = detect_provider("")
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED
        assert "Empty or missing" in result.error.message

    def test_none_url(self):
        """Test None URL returns error."""
        result = detect_provider(None)
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_whitespace_only_url(self):
        """Test whitespace-only URL returns error."""
        result = detect_provider("   ")
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_unknown_provider(self):
        """Test unknown provider URL returns error."""
        url = "https://gitlab.com/myorg/myrepo"
        result = detect_provider(url)
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED
        assert "Could not detect provider" in result.error.message
        assert url in result.error.message

    def test_malformed_github_url(self):
        """Test malformed GitHub URL returns error."""
        url = "https://github.com/onlyorg"
        result = detect_provider(url)
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_malformed_azure_url_missing_git(self):
        """Test malformed Azure URL (missing _git) returns error."""
        url = "https://dev.azure.com/myorg/myproject/myrepo"
        result = detect_provider(url)
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_random_string(self):
        """Test random string returns error."""
        result = detect_provider("not a url at all")
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_bitbucket_url(self):
        """Test Bitbucket URL (unsupported) returns error."""
        url = "https://bitbucket.org/myorg/myrepo"
        result = detect_provider(url)
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED


class TestParseGitHubUrl:
    """Tests for parse_github_url helper function."""

    def test_returns_provider_info_for_valid_url(self):
        """Test returns ProviderInfo for valid GitHub URL."""
        info = parse_github_url("https://github.com/org/repo")
        assert info is not None
        assert isinstance(info, ProviderInfo)
        assert info.provider == "github"

    def test_returns_none_for_invalid_url(self):
        """Test returns None for non-GitHub URL."""
        info = parse_github_url("https://gitlab.com/org/repo")
        assert info is None

    def test_returns_none_for_azure_url(self):
        """Test returns None for Azure DevOps URL."""
        info = parse_github_url("https://dev.azure.com/org/project/_git/repo")
        assert info is None


class TestParseAzureUrl:
    """Tests for parse_azure_url helper function."""

    def test_returns_provider_info_for_valid_url(self):
        """Test returns ProviderInfo for valid Azure DevOps URL."""
        info = parse_azure_url("https://dev.azure.com/org/project/_git/repo")
        assert info is not None
        assert isinstance(info, ProviderInfo)
        assert info.provider == "azuredevops"

    def test_returns_none_for_invalid_url(self):
        """Test returns None for non-Azure URL."""
        info = parse_azure_url("https://github.com/org/repo")
        assert info is None

    def test_returns_none_for_github_url(self):
        """Test returns None for GitHub URL."""
        info = parse_azure_url("git@github.com:org/repo.git")
        assert info is None


class TestGetRemoteUrl:
    """Tests for get_remote_url function."""

    def test_returns_url_when_remote_exists(self):
        """Test returns URL when git remote exists."""
        with patch("provider_detect.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://github.com/org/repo\n", returncode=0
            )
            url = get_remote_url()
            assert url == "https://github.com/org/repo"
            mock_run.assert_called_once_with(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_returns_none_when_remote_not_found(self):
        """Test returns None when git remote doesn't exist."""
        with patch("provider_detect.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            url = get_remote_url()
            assert url is None

    def test_uses_custom_remote_name(self):
        """Test uses custom remote name when specified."""
        with patch("provider_detect.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://github.com/org/repo\n", returncode=0
            )
            get_remote_url("upstream")
            mock_run.assert_called_once_with(
                ["git", "remote", "get-url", "upstream"],
                capture_output=True,
                text=True,
                check=True,
            )


class TestMainFunction:
    """Tests for main entry point function."""

    def test_with_explicit_url(self):
        """Test main function with explicit URL argument."""
        result = main("https://github.com/org/repo")
        assert result.success is True
        assert result.data["provider"] == "github"

    def test_with_invalid_explicit_url(self):
        """Test main function with invalid explicit URL."""
        result = main("https://invalid.com/org/repo")
        assert result.success is False
        assert result.error.code == ErrorCodes.PROVIDER_DETECT_FAILED

    def test_detects_from_git_remote(self):
        """Test main function detects from git remote when no URL provided."""
        with patch("provider_detect.get_remote_url") as mock_get:
            mock_get.return_value = "https://github.com/org/repo"
            result = main()
            assert result.success is True
            assert result.data["provider"] == "github"

    def test_error_when_no_git_remote(self):
        """Test main function returns error when no git remote found."""
        with patch("provider_detect.get_remote_url") as mock_get:
            mock_get.return_value = None
            result = main()
            assert result.success is False
            assert result.error.code == ErrorCodes.GIT_REMOTE
            assert "Could not get remote URL" in result.error.message


class TestEnvelopeOutput:
    """Tests for envelope output format."""

    def test_success_envelope_format(self):
        """Test success envelope has correct structure."""
        result = detect_provider("https://github.com/org/repo")
        assert result.success is True
        assert result.data is not None
        assert result.error is None
        assert "provider" in result.data
        assert "org" in result.data
        assert "repo" in result.data
        assert "remote_url" in result.data

    def test_error_envelope_format(self):
        """Test error envelope has correct structure."""
        result = detect_provider("invalid")
        assert result.success is False
        assert result.error is not None
        assert result.error.code is not None
        assert result.error.message is not None
        assert result.error.suggested_action is not None

    def test_to_fenced_json(self):
        """Test fenced JSON output format."""
        result = detect_provider("https://github.com/org/repo")
        fenced = result.to_fenced_json()
        assert fenced.startswith("```json\n")
        assert fenced.endswith("\n```")
        assert '"success": true' in fenced
        assert '"provider": "github"' in fenced


class TestRegexPatterns:
    """Tests for regex pattern matching."""

    def test_github_https_pattern_matches(self):
        """Test GitHub HTTPS pattern matches valid URLs."""
        assert GITHUB_HTTPS_PATTERN.match("https://github.com/org/repo")
        assert GITHUB_HTTPS_PATTERN.match("https://github.com/org/repo.git")
        assert GITHUB_HTTPS_PATTERN.match("http://github.com/org/repo")

    def test_github_https_pattern_non_matches(self):
        """Test GitHub HTTPS pattern doesn't match invalid URLs."""
        assert GITHUB_HTTPS_PATTERN.match("https://gitlab.com/org/repo") is None
        assert GITHUB_HTTPS_PATTERN.match("git@github.com:org/repo.git") is None

    def test_github_ssh_pattern_matches(self):
        """Test GitHub SSH pattern matches valid URLs."""
        assert GITHUB_SSH_PATTERN.match("git@github.com:org/repo.git")
        assert GITHUB_SSH_PATTERN.match("git@github.com:org/repo")

    def test_github_ssh_pattern_non_matches(self):
        """Test GitHub SSH pattern doesn't match invalid URLs."""
        assert GITHUB_SSH_PATTERN.match("https://github.com/org/repo") is None
        assert GITHUB_SSH_PATTERN.match("git@gitlab.com:org/repo.git") is None

    def test_azure_https_pattern_matches(self):
        """Test Azure HTTPS pattern matches valid URLs."""
        assert AZURE_HTTPS_PATTERN.match(
            "https://dev.azure.com/org/project/_git/repo"
        )
        assert AZURE_HTTPS_PATTERN.match(
            "https://dev.azure.com/org/project/_git/repo.git"
        )

    def test_azure_ssh_pattern_matches(self):
        """Test Azure SSH pattern matches valid URLs."""
        assert AZURE_SSH_PATTERN.match("git@ssh.dev.azure.com:v3/org/project/repo")
        assert AZURE_SSH_PATTERN.match("git@ssh.dev.azure.com:v3/org/project/repo.git")

    def test_azure_legacy_https_pattern_matches(self):
        """Test Azure legacy HTTPS pattern matches valid URLs."""
        assert AZURE_LEGACY_HTTPS_PATTERN.match(
            "https://org.visualstudio.com/project/_git/repo"
        )

    def test_azure_legacy_ssh_pattern_matches(self):
        """Test Azure legacy SSH pattern matches valid URLs."""
        assert AZURE_LEGACY_SSH_PATTERN.match(
            "user@vs-ssh.visualstudio.com:v3/org/project/repo"
        )


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_url_with_leading_whitespace(self):
        """Test URL with leading whitespace is trimmed."""
        result = detect_provider("  https://github.com/org/repo")
        assert result.success is True
        assert result.data["org"] == "org"

    def test_url_with_trailing_whitespace(self):
        """Test URL with trailing whitespace is trimmed."""
        result = detect_provider("https://github.com/org/repo  ")
        assert result.success is True
        assert result.data["org"] == "org"

    def test_single_char_org_and_repo(self):
        """Test single character org and repo names."""
        result = detect_provider("https://github.com/a/b")
        assert result.success is True
        assert result.data["org"] == "a"
        assert result.data["repo"] == "b"

    def test_very_long_names(self):
        """Test very long org and repo names."""
        long_name = "a" * 100
        url = f"https://github.com/{long_name}/{long_name}"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["org"] == long_name
        assert result.data["repo"] == long_name

    def test_remote_url_preserved(self):
        """Test that remote_url field preserves original URL."""
        url = "https://github.com/org/repo.git"
        result = detect_provider(url)
        assert result.data["remote_url"] == url

    def test_case_sensitivity_in_domain(self):
        """Test that domain matching is case-sensitive (lowercase expected)."""
        # GitHub with uppercase should fail
        result = detect_provider("https://GitHub.com/org/repo")
        assert result.success is False

    def test_azure_project_can_differ_from_repo(self):
        """Test Azure project and repo can have different names."""
        url = "https://dev.azure.com/myorg/ProjectName/_git/RepoName"
        result = detect_provider(url)
        assert result.success is True
        assert result.data["project"] == "ProjectName"
        assert result.data["repo"] == "RepoName"
