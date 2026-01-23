#!/usr/bin/env python3
"""Common response envelope for sc-git-worktree agents.

All scripts return fenced JSON using this standard envelope format.
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ErrorPayload(BaseModel):
    """Structured error information."""

    code: str
    message: str
    recoverable: bool = False
    suggested_action: Optional[str] = None


class Envelope(BaseModel):
    """Standard response envelope for agent outputs."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorPayload] = None

    def to_fenced_json(self) -> str:
        """Return the envelope as fenced JSON for agent output."""
        return f"```json\n{self.model_dump_json(indent=2)}\n```"

    @classmethod
    def success_response(cls, data: Dict[str, Any]) -> "Envelope":
        """Create a success response with data."""
        return cls(success=True, data=data, error=None)

    @classmethod
    def error_response(
        cls,
        code: str,
        message: str,
        recoverable: bool = False,
        suggested_action: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> "Envelope":
        """Create an error response."""
        return cls(
            success=False,
            data=data,
            error=ErrorPayload(
                code=code,
                message=message,
                recoverable=recoverable,
                suggested_action=suggested_action,
            ),
        )


class ErrorCodes:
    """Namespaced error codes for sc-git-worktree."""

    # Worktree errors
    WORKTREE_DIRTY = "WORKTREE.DIRTY"
    WORKTREE_NOT_FOUND = "WORKTREE.NOT_FOUND"
    WORKTREE_EXISTS = "WORKTREE.EXISTS"
    WORKTREE_UNMERGED = "WORKTREE.UNMERGED"

    # Branch errors
    BRANCH_NOT_PROTECTED = "BRANCH.NOT_PROTECTED"
    BRANCH_PROTECTED = "BRANCH.PROTECTED"
    BRANCH_NOT_FOUND = "BRANCH.NOT_FOUND"

    # Tracking errors
    TRACKING_MISSING = "TRACKING.MISSING"
    TRACKING_STALE = "TRACKING.STALE"

    # Merge errors
    MERGE_CONFLICTS = "MERGE.CONFLICTS"

    # Git errors
    GIT_ERROR = "GIT.ERROR"
    GIT_NOT_REPO = "GIT.NOT_REPO"

    # Config errors
    CONFIG_MISSING = "CONFIG.MISSING"
    CONFIG_PROTECTED_BRANCH_NOT_SET = "CONFIG.PROTECTED_BRANCH_NOT_SET"
