#!/usr/bin/env python3
"""Common response envelope for sc-git-worktree agents.

All scripts return fenced JSON using this standard envelope format.
Includes operation transcript for debugging and agent visibility.
"""

import json
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TranscriptEntry(BaseModel):
    """A single operation in the transcript."""

    step: str = Field(..., description="Operation name/identifier")
    status: str = Field(..., description="ok, failed, skipped")
    message: Optional[str] = Field(None, description="Human-readable description")
    value: Optional[Any] = Field(None, description="Return value or key data")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Operation duration in ms")


class Transcript(BaseModel):
    """Operation transcript for debugging and visibility."""

    entries: List[TranscriptEntry] = Field(default_factory=list)

    def step_ok(
        self,
        step: str,
        message: Optional[str] = None,
        value: Optional[Any] = None,
        duration_ms: Optional[int] = None,
    ) -> "Transcript":
        """Record a successful step."""
        self.entries.append(
            TranscriptEntry(
                step=step,
                status="ok",
                message=message,
                value=value,
                duration_ms=duration_ms,
            )
        )
        return self

    def step_failed(
        self,
        step: str,
        error: str,
        message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> "Transcript":
        """Record a failed step."""
        self.entries.append(
            TranscriptEntry(
                step=step,
                status="failed",
                message=message,
                error=error,
                duration_ms=duration_ms,
            )
        )
        return self

    def step_skipped(
        self,
        step: str,
        message: Optional[str] = None,
    ) -> "Transcript":
        """Record a skipped step."""
        self.entries.append(
            TranscriptEntry(
                step=step,
                status="skipped",
                message=message,
            )
        )
        return self

    @contextmanager
    def timed_step(self, step: str, message: Optional[str] = None):
        """Context manager for timing an operation.

        Usage:
            with transcript.timed_step("fetch_all", "Fetching remotes") as t:
                fetch_all()
                t.value = {"remotes": 2}  # Optional: set return value
        """
        entry = TranscriptEntry(step=step, status="ok", message=message)
        start = time.perf_counter()
        try:
            yield entry
        except Exception as e:
            entry.status = "failed"
            entry.error = str(e)
            raise
        finally:
            entry.duration_ms = int((time.perf_counter() - start) * 1000)
            self.entries.append(entry)

    def last_step(self) -> Optional[str]:
        """Get the name of the last step."""
        return self.entries[-1].step if self.entries else None

    def failed_step(self) -> Optional[TranscriptEntry]:
        """Get the first failed step, if any."""
        for entry in self.entries:
            if entry.status == "failed":
                return entry
        return None

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dicts for JSON serialization."""
        return [e.model_dump(exclude_none=True) for e in self.entries]


class ErrorPayload(BaseModel):
    """Structured error information."""

    code: str
    message: str
    recoverable: bool = False
    suggested_action: Optional[str] = None
    step: Optional[str] = Field(None, description="Which step failed")


class Envelope(BaseModel):
    """Standard response envelope for agent outputs.

    Follows the standard envelope spec with:
    - success: bool
    - data: optional payload
    - error: optional structured error
    - metadata: optional metadata including transcript
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorPayload] = None
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadata including operation transcript"
    )

    def to_fenced_json(self) -> str:
        """Return the envelope as fenced JSON for agent output."""
        return f"```json\n{self.model_dump_json(indent=2, exclude_none=True)}\n```"

    @classmethod
    def success_response(
        cls,
        data: Dict[str, Any],
        transcript: Optional[Transcript] = None,
    ) -> "Envelope":
        """Create a success response with data."""
        metadata = None
        if transcript:
            metadata = {"transcript": transcript.to_list()}

        return cls(
            success=True,
            data=data,
            error=None,
            metadata=metadata,
        )

    @classmethod
    def error_response(
        cls,
        code: str,
        message: str,
        recoverable: bool = False,
        suggested_action: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        transcript: Optional[Transcript] = None,
        step: Optional[str] = None,
    ) -> "Envelope":
        """Create an error response.

        If transcript is provided and step is not, step is inferred from
        the last failed entry or the last entry in the transcript.
        """
        # Infer step from transcript if not provided
        if step is None and transcript:
            failed = transcript.failed_step()
            if failed:
                step = failed.step
            elif transcript.last_step():
                step = transcript.last_step()

        metadata = None
        if transcript:
            metadata = {"transcript": transcript.to_list()}

        return cls(
            success=False,
            data=data,
            error=ErrorPayload(
                code=code,
                message=message,
                recoverable=recoverable,
                suggested_action=suggested_action,
                step=step,
            ),
            metadata=metadata,
        )


class ErrorCodes:
    """Namespaced error codes for sc-git-worktree."""

    # Worktree errors
    WORKTREE_DIRTY = "WORKTREE.DIRTY"
    WORKTREE_NOT_FOUND = "WORKTREE.NOT_FOUND"
    WORKTREE_EXISTS = "WORKTREE.EXISTS"
    WORKTREE_UNMERGED = "WORKTREE.UNMERGED"
    WORKTREE_BRANCH_IN_USE = "WORKTREE.BRANCH_IN_USE"

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
    GIT_FETCH_FAILED = "GIT.FETCH_FAILED"
    GIT_COMMAND_FAILED = "GIT.COMMAND_FAILED"

    # Config errors
    CONFIG_MISSING = "CONFIG.MISSING"
    CONFIG_INVALID = "CONFIG.INVALID"
    CONFIG_PROTECTED_BRANCH_NOT_SET = "CONFIG.PROTECTED_BRANCH_NOT_SET"

    # Input errors
    INPUT_INVALID = "INPUT.INVALID"
    INPUT_MISSING = "INPUT.MISSING"
