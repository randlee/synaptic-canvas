#!/usr/bin/env python3
"""Create PR script for sc-commit-push-pr.

Creates a pull request using the appropriate provider (GitHub or Azure DevOps)
based on the repository's remote URL.

Usage:
    # Via command line argument (JSON string)
    python create_pr.py '{"title": "My PR", "body": "Description", "source": "feature", "destination": "main"}'

    # Via stdin (JSON)
    echo '{"title": "My PR", "body": "Description", "source": "feature", "destination": "main"}' | python create_pr.py

Output:
    Fenced JSON envelope with PR info or error details.
"""

import json
import sys
from typing import Optional

from pydantic import BaseModel, ValidationError

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
    from .provider_detect import ProviderInfo, detect_provider, get_remote_url
    from .pr_provider import PrProviderError, get_provider
except ImportError:
    from envelope import Envelope, ErrorCodes
    from provider_detect import ProviderInfo, detect_provider, get_remote_url
    from pr_provider import PrProviderError, get_provider


# =============================================================================
# Input/Output Models
# =============================================================================


class CreatePrInput(BaseModel):
    """Input schema for PR creation."""

    title: str
    body: str
    source: str
    destination: str


class CreatePrData(BaseModel):
    """Output data payload for successful PR creation."""

    pr: dict  # PullRequestInfo as dict


# =============================================================================
# Main Function
# =============================================================================


def main(
    title: str,
    body: str,
    source: str,
    destination: str,
    remote_url: Optional[str] = None,
) -> Envelope:
    """Create a pull request.

    Args:
        title: PR title
        body: PR description/body
        source: Source (head) branch name
        destination: Destination (base) branch name
        remote_url: Optional remote URL override. If not provided, detects from git.

    Returns:
        Envelope with PR info on success, or error details on failure.
    """
    # 1. Get remote URL (if not provided)
    if remote_url is None:
        remote_url = get_remote_url()

    if not remote_url:
        return Envelope.error_response(
            code=ErrorCodes.GIT_REMOTE,
            message="Could not get remote URL from git",
            recoverable=False,
            suggested_action="Ensure you are in a git repository with an 'origin' remote.",
        )

    # 2. Detect provider from remote URL
    provider_result = detect_provider(remote_url)
    if not provider_result.success:
        return provider_result

    # 3. Create provider instance
    try:
        provider_info = ProviderInfo(**provider_result.data)
        provider = get_provider(provider_info)
    except PrProviderError as e:
        return e.to_envelope()
    except Exception as e:
        return Envelope.error_response(
            code=ErrorCodes.PROVIDER_DETECT_FAILED,
            message=f"Failed to create provider: {e}",
            recoverable=False,
        )

    # 4. Create PR
    try:
        result = provider.create_pr(title, body, source, destination)
        return Envelope.success_response({"pr": result.pr.model_dump()})
    except PrProviderError as e:
        return e.to_envelope()
    except Exception as e:
        return Envelope.error_response(
            code=ErrorCodes.PR_CREATE_FAILED,
            message=f"Unexpected error creating PR: {e}",
            recoverable=False,
        )


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    # Accept JSON input from args or stdin
    try:
        if len(sys.argv) > 1:
            data = json.loads(sys.argv[1])
        else:
            data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_INVALID,
            message=f"Invalid JSON input: {e}",
            recoverable=False,
            suggested_action="Provide valid JSON with title, body, source, and destination fields.",
        )
        print(envelope.to_fenced_json())
        sys.exit(1)

    # Validate input
    try:
        input_data = CreatePrInput(**data)
    except ValidationError as e:
        envelope = Envelope.error_response(
            code=ErrorCodes.CONFIG_INVALID,
            message=f"Invalid input data: {e}",
            recoverable=False,
            suggested_action="Ensure all required fields (title, body, source, destination) are provided.",
        )
        print(envelope.to_fenced_json())
        sys.exit(1)

    # Execute and output result
    result = main(
        input_data.title, input_data.body, input_data.source, input_data.destination
    )
    print(result.to_fenced_json())
    sys.exit(0 if result.success else 1)
