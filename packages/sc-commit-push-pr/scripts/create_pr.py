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
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

# Support both relative import (when used as package) and absolute import (when used standalone)
try:
    from .envelope import Envelope, ErrorCodes
    from .provider_detect import ProviderInfo, detect_provider, get_remote_url
    from .pr_provider import PrProviderError, get_provider
    from .stack_guard import (
        check_gh_stack_marker,
        check_stack_prerequisites,
        get_repo_root,
        missing_prereq_actions,
        STACK_PREREQS_MISSING_MESSAGE,
        STACK_USE_GH_STACK_SUGGESTED_ACTION,
    )
except ImportError:
    from envelope import Envelope, ErrorCodes
    from provider_detect import ProviderInfo, detect_provider, get_remote_url
    from pr_provider import PrProviderError, get_provider
    from stack_guard import (
        check_gh_stack_marker,
        check_stack_prerequisites,
        get_repo_root,
        missing_prereq_actions,
        STACK_PREREQS_MISSING_MESSAGE,
        STACK_USE_GH_STACK_SUGGESTED_ACTION,
    )


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
    # 0. Mandatory gh-stack toolchain prerequisites (unconditional). This
    # package is the critical junction where a stack-unaware PR creation
    # can corrupt gh-stack linearity, so the full toolchain is required on
    # every invocation, regardless of branch or provider.
    repo_root = get_repo_root()
    prereqs = check_stack_prerequisites(repo_root)
    if not prereqs["ok"]:
        return Envelope.error_response(
            code=ErrorCodes.PREFLIGHT_STACK_PREREQS_MISSING,
            message=STACK_PREREQS_MISSING_MESSAGE,
            recoverable=True,
            suggested_action="; ".join(missing_prereq_actions(prereqs)),
            data=prereqs,
        )

    # 0b. gh-stack layer detection (state-based, current worktree). A
    # stack layer's PR is owned by `gh stack submit --auto` (correct base
    # = the layer below, with stack object linkage) -- refuse rather than
    # opening a PR with an arbitrary base here.
    if check_gh_stack_marker(Path.cwd()):
        return Envelope.error_response(
            code=ErrorCodes.STACK_USE_GH_STACK,
            message=(
                f"Branch '{source}' is a layer of a gh stack; PR "
                "creation is owned by `gh stack submit --auto`, not "
                "sc-commit-push-pr."
            ),
            recoverable=True,
            suggested_action=STACK_USE_GH_STACK_SUGGESTED_ACTION,
            data={
                "pr_created": False,
                "source_branch": source,
                "destination_branch": destination,
                "stack": {
                    "detected": True,
                    "reason": (
                        "a gh-stack layer's PR base must be the layer "
                        "below it with stack object linkage -- only "
                        "`gh stack submit --auto` can create it correctly."
                    ),
                },
            },
        )

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
