#!/usr/bin/env python3
"""Common response envelope for sc-commit-push-pr agents.

All scripts return fenced JSON using this standard envelope format.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
import json


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
        data: Optional[Dict[str, Any]] = None
    ) -> "Envelope":
        """Create an error response."""
        return cls(
            success=False,
            data=data,
            error=ErrorPayload(
                code=code,
                message=message,
                recoverable=recoverable,
                suggested_action=suggested_action
            )
        )


# Error code constants
class ErrorCodes:
    """Namespaced error codes for sc-commit-push-pr."""
    # Git errors
    GIT_MERGE_CONFLICT = "GIT.MERGE_CONFLICT"
    GIT_AUTH = "GIT.AUTH"
    GIT_REMOTE = "GIT.REMOTE"
    GIT_NO_CHANGES = "GIT.NO_CHANGES"

    # PR errors
    PR_CREATE_FAILED = "PR.CREATE_FAILED"
    PR_NOT_FOUND = "PR.NOT_FOUND"
    PR_ALREADY_EXISTS = "PR.ALREADY_EXISTS"

    # Provider errors
    PROVIDER_DETECT_FAILED = "PROVIDER.DETECT_FAILED"
    PROVIDER_UNSUPPORTED = "PROVIDER.UNSUPPORTED"

    # Config errors
    CONFIG_MISSING = "CONFIG.MISSING"
    CONFIG_INVALID = "CONFIG.INVALID"
    CONFIG_PROTECTED_BRANCH = "CONFIG.PROTECTED_BRANCH_NOT_SET"
