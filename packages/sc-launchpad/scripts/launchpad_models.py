#!/usr/bin/env python3
"""Launch payload, typed failure, and model aliases for the sc-launchpad runtime."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class LaunchFailure(Exception):
    """A typed failure; rendered into the envelope's ``error`` object."""

    def __init__(
        self,
        code: str,
        message: str,
        suggested_action: Optional[str] = None,
        *,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.suggested_action = suggested_action
        self.recoverable = recoverable
        self.details = details or {}

    def to_error(self) -> Dict[str, Any]:
        error: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action,
        }
        if self.details:
            error["details"] = self.details
        return error


class IsolationInput(BaseModel):
    """Isolation for one launch; every resumed turn states it again explicitly."""

    tools: Literal["default", "none"] = "default"
    cwd: Literal["given", "temp"] = "given"

    model_config = {"extra": "forbid"}


class LaunchpadInput(BaseModel):
    description: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    tool: Literal["claude", "codex", "gemini"]
    model: Optional[str] = None
    cwd: Optional[str] = Field(default=None, min_length=1)
    atm_identity: Optional[str] = None
    extra_args: List[str] = Field(default_factory=list)
    output_format: Optional[Literal["text", "json"]] = None
    # Session ids are UUIDs; the restricted charset keeps argv shim-safe.
    resume_session_id: Optional[str] = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
    )
    isolation: Optional[IsolationInput] = None
    timeout_seconds: Optional[float] = Field(default=None, gt=0)
    ephemeral: bool = False

    model_config = {"extra": "forbid"}

    @property
    def temp_cwd(self) -> bool:
        return self.isolation is not None and self.isolation.cwd == "temp"

    @property
    def no_tools(self) -> bool:
        return self.isolation is not None and self.isolation.tools == "none"

    @property
    def structured(self) -> bool:
        if self.output_format is not None:
            return self.output_format == "json"
        return self.resume_session_id is not None or self.isolation is not None

    @model_validator(mode="after")
    def _check_combinations(self) -> "LaunchpadInput":
        if self.resume_session_id is not None:
            if self.isolation is None:
                raise ValueError(
                    "resume_session_id requires an explicit `isolation` object so a "
                    "resumed turn never keeps or relaxes isolation implicitly"
                )
            if self.temp_cwd:
                raise ValueError(
                    "isolation.cwd='temp' only applies to a new session; to resume, pass "
                    "the previous envelope's data.cwd as `cwd` with isolation.cwd='given'"
                )
            if self.output_format == "text":
                raise ValueError("resume_session_id requires output_format='json'")
        if self.no_tools and self.extra_args:
            raise ValueError("extra_args are not allowed with isolation.tools='none'")
        if self.no_tools and self.atm_identity:
            raise ValueError("atm_identity (teammate mode) needs tools; not allowed with isolation.tools='none'")
        if self.temp_cwd and self.cwd is not None:
            raise ValueError("omit `cwd` when isolation.cwd='temp'")
        if not self.temp_cwd and self.cwd is None:
            raise ValueError("`cwd` is required unless isolation.cwd='temp'")
        return self


CODEX_MODEL_MAP = {
    # `codex` remains a deprecated compatibility alias for Terra.
    "codex": "gpt-5.6-terra",
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
    "luna": "gpt-5.6-luna",
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt-5.6": "gpt-5.6-sol",
    # Preserve explicit legacy model requests without using them as defaults.
    "gpt-5.2-codex": "gpt-5.2-codex",
    "codex-max": "gpt-5.1-codex-max",
    "max": "gpt-5.1-codex-max",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
    "codex-mini": "gpt-5.1-codex-mini",
    "mini": "gpt-5.1-codex-mini",
    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    "gpt-5": "gpt-5.2",
    "gpt-5.2": "gpt-5.2",
}

CODEX_ROSTER_MODEL_MAP = {
    "gpt-5.6-sol": "sol",
    "gpt-5.6-terra": "terra",
    "gpt-5.6-luna": "luna",
}

CLAUDE_MODEL_MAP = {
    "sonnet": "sonnet",
    "haiku": "haiku",
    "opus": "opus",
    "fable": "fable",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5": "haiku",
    "claude-opus-4-1": "opus",
    "claude-fable-5": "fable",
    "claude-fable-5[1m]": "fable",
}


def normalize_tool_model(payload: LaunchpadInput) -> Optional[str]:
    if payload.tool == "claude":
        normalized = CLAUDE_MODEL_MAP.get(payload.model or "sonnet")
        hint = "Use one of: sonnet, haiku, opus, fable."
    elif payload.tool == "codex":
        normalized = CODEX_MODEL_MAP.get(payload.model or "terra")
        hint = "Use sol, terra, luna, codex (deprecated), or a known Codex model alias."
    else:
        return payload.model
    if normalized is None:
        raise LaunchFailure(
            "VALIDATION.INVALID_MODEL",
            f"Unsupported {payload.tool.capitalize()} model: {payload.model}",
            hint,
        )
    return normalized


def roster_model(payload: LaunchpadInput, normalized_model: Optional[str]) -> str:
    if payload.tool == "claude":
        return normalized_model or "sonnet"
    if payload.tool == "codex":
        return CODEX_ROSTER_MODEL_MAP.get(normalized_model or "", normalized_model or "terra")
    return payload.tool
