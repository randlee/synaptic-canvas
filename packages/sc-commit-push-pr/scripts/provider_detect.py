#!/usr/bin/env python3
"""Provider detection for sc-commit-push-pr.

Parses git remote URLs to detect GitHub vs Azure DevOps and extract
organization, project, and repository information.
"""

import re
import subprocess
import sys
from typing import Optional

from pydantic import BaseModel

from envelope import Envelope, ErrorCodes


class ProviderInfo(BaseModel):
    """Detected provider information from git remote URL."""

    provider: str  # "github" or "azuredevops"
    org: str
    project: Optional[str] = None  # Azure DevOps only
    repo: str
    remote_url: str


# Regex patterns for URL parsing
GITHUB_HTTPS_PATTERN = re.compile(
    r"^https?://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)
GITHUB_SSH_PATTERN = re.compile(
    r"^git@github\.com:(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)

# Azure DevOps HTTPS: https://dev.azure.com/org/project/_git/repo
AZURE_HTTPS_PATTERN = re.compile(
    r"^https?://dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/]+?)(?:\.git)?/?$"
)

# Azure DevOps SSH: git@ssh.dev.azure.com:v3/org/project/repo
AZURE_SSH_PATTERN = re.compile(
    r"^git@ssh\.dev\.azure\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)

# Legacy Azure DevOps (visualstudio.com) HTTPS: https://org.visualstudio.com/project/_git/repo
AZURE_LEGACY_HTTPS_PATTERN = re.compile(
    r"^https?://(?P<org>[^.]+)\.visualstudio\.com/(?P<project>[^/]+)/_git/(?P<repo>[^/]+?)(?:\.git)?/?$"
)

# Legacy Azure DevOps (visualstudio.com) SSH: org@vs-ssh.visualstudio.com:v3/org/project/repo
AZURE_LEGACY_SSH_PATTERN = re.compile(
    r"^[^@]+@vs-ssh\.visualstudio\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)


def parse_github_url(url: str) -> Optional[ProviderInfo]:
    """Parse a GitHub URL and return ProviderInfo if valid."""
    # Try HTTPS format
    match = GITHUB_HTTPS_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="github",
            org=match.group("org"),
            repo=match.group("repo"),
            remote_url=url,
        )

    # Try SSH format
    match = GITHUB_SSH_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="github",
            org=match.group("org"),
            repo=match.group("repo"),
            remote_url=url,
        )

    return None


def parse_azure_url(url: str) -> Optional[ProviderInfo]:
    """Parse an Azure DevOps URL and return ProviderInfo if valid."""
    # Try modern HTTPS format (dev.azure.com)
    match = AZURE_HTTPS_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="azuredevops",
            org=match.group("org"),
            project=match.group("project"),
            repo=match.group("repo"),
            remote_url=url,
        )

    # Try modern SSH format (ssh.dev.azure.com)
    match = AZURE_SSH_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="azuredevops",
            org=match.group("org"),
            project=match.group("project"),
            repo=match.group("repo"),
            remote_url=url,
        )

    # Try legacy HTTPS format (visualstudio.com)
    match = AZURE_LEGACY_HTTPS_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="azuredevops",
            org=match.group("org"),
            project=match.group("project"),
            repo=match.group("repo"),
            remote_url=url,
        )

    # Try legacy SSH format (vs-ssh.visualstudio.com)
    match = AZURE_LEGACY_SSH_PATTERN.match(url)
    if match:
        return ProviderInfo(
            provider="azuredevops",
            org=match.group("org"),
            project=match.group("project"),
            repo=match.group("repo"),
            remote_url=url,
        )

    return None


def detect_provider(remote_url: str) -> Envelope:
    """Detect provider from a git remote URL.

    Args:
        remote_url: The git remote URL to parse

    Returns:
        Envelope with ProviderInfo data on success, or error on failure
    """
    if not remote_url or not remote_url.strip():
        return Envelope.error_response(
            code=ErrorCodes.PROVIDER_DETECT_FAILED,
            message="Empty or missing remote URL",
            recoverable=False,
            suggested_action="Ensure the repository has a valid git remote configured.",
        )

    url = remote_url.strip()

    # Try GitHub first
    provider_info = parse_github_url(url)
    if provider_info:
        return Envelope.success_response(provider_info.model_dump())

    # Try Azure DevOps
    provider_info = parse_azure_url(url)
    if provider_info:
        return Envelope.success_response(provider_info.model_dump())

    # Unknown provider
    return Envelope.error_response(
        code=ErrorCodes.PROVIDER_DETECT_FAILED,
        message=f"Could not detect provider from URL: {url}",
        recoverable=False,
        suggested_action="Supported providers are GitHub and Azure DevOps. "
        "Check that the remote URL is correctly formatted.",
    )


def get_remote_url(remote_name: str = "origin") -> Optional[str]:
    """Get the URL for a git remote.

    Args:
        remote_name: Name of the remote (default: "origin")

    Returns:
        The remote URL, or None if the remote doesn't exist
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def main(remote_url: Optional[str] = None) -> Envelope:
    """Main entry point for provider detection.

    Args:
        remote_url: Optional URL to parse. If not provided, detects from git remote.

    Returns:
        Envelope with ProviderInfo data on success, or error on failure
    """
    if remote_url:
        return detect_provider(remote_url)

    # Try to get from git remote
    url = get_remote_url()
    if not url:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message="Could not get remote URL from git",
            recoverable=False,
            suggested_action="Ensure you are in a git repository with an 'origin' remote.",
        )

    return detect_provider(url)


if __name__ == "__main__":
    # Accept remote URL as command line argument
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = main(url_arg)
    print(result.to_fenced_json())
