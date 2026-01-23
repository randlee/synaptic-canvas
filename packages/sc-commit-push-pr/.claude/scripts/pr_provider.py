"""PR provider abstraction for GitHub and Azure DevOps.

Provides a unified interface for PR operations across different git hosting providers.
Uses `gh` CLI for GitHub and REST API for Azure DevOps.
"""

from abc import ABC, abstractmethod
from typing import Optional
import json
import os
import subprocess

from pydantic import BaseModel, Field
import requests

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
    from .provider_detect import ProviderInfo
except ImportError:
    from envelope import Envelope, ErrorCodes
    from provider_detect import ProviderInfo


# =============================================================================
# Pydantic Models
# =============================================================================

class PullRequestInfo(BaseModel):
    """Information about a pull request."""
    id: str
    url: str
    source_branch: str
    destination_branch: str
    provider: str


class PrCheckResult(BaseModel):
    """Result of checking if a PR exists."""
    exists: bool
    pr: Optional[PullRequestInfo] = None


class PrCreateResult(BaseModel):
    """Result of creating a PR."""
    pr: PullRequestInfo


# Re-export ProviderInfo for convenience (imported from provider_detect)


# =============================================================================
# Abstract Base Class
# =============================================================================

class PrProvider(ABC):
    """Abstract base class for PR provider operations."""

    @abstractmethod
    def check_pr_exists(self, source_branch: str, destination_branch: str) -> PrCheckResult:
        """Check if a PR exists for the given branches.

        Args:
            source_branch: The source (head) branch name
            destination_branch: The destination (base) branch name

        Returns:
            PrCheckResult with exists=True and pr info if found, otherwise exists=False
        """
        pass

    @abstractmethod
    def create_pr(
        self, title: str, body: str, source_branch: str, destination_branch: str
    ) -> PrCreateResult:
        """Create a new pull request.

        Args:
            title: PR title
            body: PR description/body
            source_branch: The source (head) branch name
            destination_branch: The destination (base) branch name

        Returns:
            PrCreateResult with the created PR info

        Raises:
            PrProviderError: If PR creation fails
        """
        pass

    @abstractmethod
    def get_pr_info(self, pr_id: str) -> PullRequestInfo:
        """Get information about a specific PR.

        Args:
            pr_id: The PR identifier (number for GitHub, ID for Azure)

        Returns:
            PullRequestInfo for the PR

        Raises:
            PrProviderError: If PR not found or lookup fails
        """
        pass


# =============================================================================
# Custom Exceptions
# =============================================================================

class PrProviderError(Exception):
    """Base exception for PR provider errors."""

    def __init__(self, code: str, message: str, recoverable: bool = False,
                 suggested_action: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.suggested_action = suggested_action

    def to_envelope(self, data: Optional[dict] = None) -> Envelope:
        """Convert error to standard envelope format."""
        return Envelope.error_response(
            code=self.code,
            message=self.message,
            recoverable=self.recoverable,
            suggested_action=self.suggested_action,
            data=data
        )


# =============================================================================
# GitHub Implementation
# =============================================================================

class GitHubProvider(PrProvider):
    """GitHub PR provider using `gh` CLI."""

    def __init__(self, org: str, repo: str):
        """Initialize GitHub provider.

        Args:
            org: GitHub organization or user name
            repo: Repository name
        """
        self.org = org
        self.repo = repo
        self.provider_name = "github"

    def _run_gh_command(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a gh CLI command.

        Args:
            args: Arguments to pass to gh
            check: Whether to raise on non-zero exit code

        Returns:
            CompletedProcess result

        Raises:
            PrProviderError: If command fails and check=True
        """
        cmd = ["gh"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            if check and result.returncode != 0:
                raise PrProviderError(
                    code=ErrorCodes.PR_CREATE_FAILED,
                    message=f"gh command failed: {result.stderr.strip()}",
                    recoverable=False,
                    suggested_action="Check gh CLI authentication and permissions"
                )
            return result
        except FileNotFoundError:
            raise PrProviderError(
                code=ErrorCodes.PROVIDER_UNSUPPORTED,
                message="gh CLI not found. Please install GitHub CLI.",
                recoverable=False,
                suggested_action="Install gh CLI: https://cli.github.com/"
            )

    def check_pr_exists(self, source_branch: str, destination_branch: str) -> PrCheckResult:
        """Check if a PR exists for the given branches using gh CLI."""
        result = self._run_gh_command([
            "pr", "list",
            "--head", source_branch,
            "--base", destination_branch,
            "--json", "number,url,headRefName,baseRefName",
            "--limit", "1"
        ], check=False)

        if result.returncode != 0:
            # Command failed, but we don't want to error - just report no PR found
            return PrCheckResult(exists=False)

        try:
            prs = json.loads(result.stdout)
            if prs and len(prs) > 0:
                pr_data = prs[0]
                return PrCheckResult(
                    exists=True,
                    pr=PullRequestInfo(
                        id=str(pr_data["number"]),
                        url=pr_data["url"],
                        source_branch=pr_data["headRefName"],
                        destination_branch=pr_data["baseRefName"],
                        provider=self.provider_name
                    )
                )
        except (json.JSONDecodeError, KeyError):
            pass

        return PrCheckResult(exists=False)

    def create_pr(
        self, title: str, body: str, source_branch: str, destination_branch: str
    ) -> PrCreateResult:
        """Create a PR using gh CLI."""
        result = self._run_gh_command([
            "pr", "create",
            "--title", title,
            "--body", body,
            "--head", source_branch,
            "--base", destination_branch
        ], check=True)

        # gh pr create outputs the PR URL on success
        pr_url = result.stdout.strip()

        # Extract PR number from URL (format: https://github.com/org/repo/pull/123)
        try:
            pr_number = pr_url.split("/")[-1]
        except (ValueError, IndexError):
            pr_number = "unknown"

        return PrCreateResult(
            pr=PullRequestInfo(
                id=pr_number,
                url=pr_url,
                source_branch=source_branch,
                destination_branch=destination_branch,
                provider=self.provider_name
            )
        )

    def get_pr_info(self, pr_id: str) -> PullRequestInfo:
        """Get PR info using gh CLI."""
        result = self._run_gh_command([
            "pr", "view", pr_id,
            "--json", "number,url,headRefName,baseRefName"
        ], check=True)

        try:
            pr_data = json.loads(result.stdout)
            return PullRequestInfo(
                id=str(pr_data["number"]),
                url=pr_data["url"],
                source_branch=pr_data["headRefName"],
                destination_branch=pr_data["baseRefName"],
                provider=self.provider_name
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise PrProviderError(
                code=ErrorCodes.PR_NOT_FOUND,
                message=f"Failed to parse PR info: {e}",
                recoverable=False
            )


# =============================================================================
# Azure DevOps Implementation
# =============================================================================

class AzureDevOpsProvider(PrProvider):
    """Azure DevOps PR provider using REST API."""

    def __init__(self, org: str, project: str, repo: str):
        """Initialize Azure DevOps provider.

        Args:
            org: Azure DevOps organization name
            project: Project name
            repo: Repository name
        """
        self.org = org
        self.project = project
        self.repo = repo
        self.provider_name = "azuredevops"
        self.api_version = "7.0"
        self.base_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"

    def _get_pat(self) -> str:
        """Get the Azure DevOps PAT from environment.

        Returns:
            The PAT token

        Raises:
            PrProviderError: If PAT not found in environment
        """
        pat = os.environ.get("AZURE_DEVOPS_PAT")
        if not pat:
            raise PrProviderError(
                code=ErrorCodes.GIT_AUTH,
                message="AZURE_DEVOPS_PAT environment variable not set",
                recoverable=False,
                suggested_action="Set AZURE_DEVOPS_PAT environment variable with your Personal Access Token"
            )
        return pat

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make an authenticated request to Azure DevOps API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON body for POST/PUT requests
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            PrProviderError: If request fails
        """
        pat = self._get_pat()
        url = f"{self.base_url}/{endpoint}"

        # Add API version to params
        if params is None:
            params = {}
        params["api-version"] = self.api_version

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=("", pat),  # Azure DevOps uses empty username with PAT
                json=json_data,
                params=params,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 401:
                raise PrProviderError(
                    code=ErrorCodes.GIT_AUTH,
                    message="Azure DevOps authentication failed",
                    recoverable=False,
                    suggested_action="Check AZURE_DEVOPS_PAT has correct permissions"
                )

            if response.status_code == 404:
                raise PrProviderError(
                    code=ErrorCodes.PR_NOT_FOUND,
                    message=f"Resource not found: {endpoint}",
                    recoverable=False
                )

            if not response.ok:
                error_msg = response.text
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                except (json.JSONDecodeError, KeyError):
                    pass

                raise PrProviderError(
                    code=ErrorCodes.PR_CREATE_FAILED,
                    message=f"Azure DevOps API error: {error_msg}",
                    recoverable=False
                )

            return response.json()

        except requests.RequestException as e:
            raise PrProviderError(
                code=ErrorCodes.GIT_REMOTE,
                message=f"Failed to connect to Azure DevOps: {e}",
                recoverable=True,
                suggested_action="Check network connectivity and try again"
            )

    def _normalize_branch_ref(self, branch: str) -> str:
        """Normalize branch name to full ref format.

        Args:
            branch: Branch name (may or may not have refs/heads/ prefix)

        Returns:
            Full ref format (refs/heads/branch)
        """
        if branch.startswith("refs/heads/"):
            return branch
        return f"refs/heads/{branch}"

    def _extract_branch_name(self, ref: str) -> str:
        """Extract branch name from full ref.

        Args:
            ref: Full ref (refs/heads/branch)

        Returns:
            Branch name without refs/heads/ prefix
        """
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            return ref[len(prefix):]
        return ref

    def check_pr_exists(self, source_branch: str, destination_branch: str) -> PrCheckResult:
        """Check if a PR exists for the given branches using Azure DevOps API."""
        source_ref = self._normalize_branch_ref(source_branch)
        target_ref = self._normalize_branch_ref(destination_branch)

        try:
            # Query for PRs with matching source and target
            result = self._make_request(
                "GET",
                "pullrequests",
                params={
                    "searchCriteria.sourceRefName": source_ref,
                    "searchCriteria.targetRefName": target_ref,
                    "searchCriteria.status": "active",
                    "$top": "1"
                }
            )

            prs = result.get("value", [])
            if prs and len(prs) > 0:
                pr_data = prs[0]
                pr_id = str(pr_data["pullRequestId"])
                pr_url = f"https://dev.azure.com/{self.org}/{self.project}/_git/{self.repo}/pullrequest/{pr_id}"

                return PrCheckResult(
                    exists=True,
                    pr=PullRequestInfo(
                        id=pr_id,
                        url=pr_url,
                        source_branch=self._extract_branch_name(pr_data["sourceRefName"]),
                        destination_branch=self._extract_branch_name(pr_data["targetRefName"]),
                        provider=self.provider_name
                    )
                )
        except PrProviderError:
            # If we can't query, report no PR found
            pass

        return PrCheckResult(exists=False)

    def create_pr(
        self, title: str, body: str, source_branch: str, destination_branch: str
    ) -> PrCreateResult:
        """Create a PR using Azure DevOps API."""
        source_ref = self._normalize_branch_ref(source_branch)
        target_ref = self._normalize_branch_ref(destination_branch)

        result = self._make_request(
            "POST",
            "pullrequests",
            json_data={
                "sourceRefName": source_ref,
                "targetRefName": target_ref,
                "title": title,
                "description": body
            }
        )

        pr_id = str(result["pullRequestId"])
        pr_url = f"https://dev.azure.com/{self.org}/{self.project}/_git/{self.repo}/pullrequest/{pr_id}"

        return PrCreateResult(
            pr=PullRequestInfo(
                id=pr_id,
                url=pr_url,
                source_branch=self._extract_branch_name(result["sourceRefName"]),
                destination_branch=self._extract_branch_name(result["targetRefName"]),
                provider=self.provider_name
            )
        )

    def get_pr_info(self, pr_id: str) -> PullRequestInfo:
        """Get PR info using Azure DevOps API."""
        result = self._make_request("GET", f"pullrequests/{pr_id}")

        pr_url = f"https://dev.azure.com/{self.org}/{self.project}/_git/{self.repo}/pullrequest/{pr_id}"

        return PullRequestInfo(
            id=str(result["pullRequestId"]),
            url=pr_url,
            source_branch=self._extract_branch_name(result["sourceRefName"]),
            destination_branch=self._extract_branch_name(result["targetRefName"]),
            provider=self.provider_name
        )


# =============================================================================
# Factory Function
# =============================================================================

def get_provider(provider_info: ProviderInfo) -> PrProvider:
    """Factory function to create the appropriate PR provider.

    Args:
        provider_info: Information about the git provider

    Returns:
        A PrProvider instance for the detected provider

    Raises:
        PrProviderError: If provider is not supported
    """
    if provider_info.provider == "github":
        return GitHubProvider(org=provider_info.org, repo=provider_info.repo)

    elif provider_info.provider == "azuredevops":
        if not provider_info.project:
            raise PrProviderError(
                code=ErrorCodes.PROVIDER_DETECT_FAILED,
                message="Azure DevOps provider requires a project name",
                recoverable=False
            )
        return AzureDevOpsProvider(
            org=provider_info.org,
            project=provider_info.project,
            repo=provider_info.repo
        )

    else:
        raise PrProviderError(
            code=ErrorCodes.PROVIDER_UNSUPPORTED,
            message=f"Unsupported provider: {provider_info.provider}",
            recoverable=False,
            suggested_action="Supported providers: github, azuredevops"
        )
