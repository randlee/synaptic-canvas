#!/usr/bin/env python3
"""
Task tool schema models (pydantic).

This module provides:
- TaskToolInput: validated input payload
- TaskToolOutputForeground: foreground output shape
- TaskToolOutputBackground: background output shape
- task_tool_input_schema(): JSON schema for input
"""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Model / effort catalog -- the single source of truth.
#
# These constants live here (rather than in task_runner.py) because
# task_runner imports this module; defining them here avoids a circular
# import. task_runner re-exports them, and argparse help, pydantic Literals
# and resolution logic are all derived from them. tests/ assert that
# schemas/task_tool.schema.json stays in sync.
# ---------------------------------------------------------------------------

#: Reasoning effort levels, lowest to highest.
REASONING_EFFORTS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max", "ultra")


def _efforts_up_to(highest: str) -> tuple[str, ...]:
    return REASONING_EFFORTS[: REASONING_EFFORTS.index(highest) + 1]


#: Full Codex model slugs -> supported reasoning effort levels.
CODEX_MODEL_EFFORTS: dict[str, tuple[str, ...]] = {
    "gpt-6-sol": _efforts_up_to("ultra"),
    "gpt-6-astra": _efforts_up_to("ultra"),
    "gpt-6-luna": _efforts_up_to("max"),
    "gpt-5.6-sol": _efforts_up_to("ultra"),
    "gpt-5.6-terra": _efforts_up_to("ultra"),
    "gpt-5.6-luna": _efforts_up_to("max"),
    "gpt-5.5": _efforts_up_to("xhigh"),
}
CODEX_MODEL_SLUGS: tuple[str, ...] = tuple(CODEX_MODEL_EFFORTS)

#: Model used when no model is given (or the `codex` alias is used).
CODEX_DEFAULT_MODEL = "gpt-6-astra"

#: Short aliases -> full slugs. Full slugs are also accepted as-is.
CODEX_MODEL_ALIASES: dict[str, str] = {
    "codex": CODEX_DEFAULT_MODEL,
    "sol": "gpt-6-sol",
    "astra": "gpt-6-astra",
    "luna": "gpt-6-luna",
    "terra": "gpt-5.6-terra",
}

#: Every accepted Codex model name (aliases first, then slugs).
CODEX_MODEL_NAMES: tuple[str, ...] = tuple(CODEX_MODEL_ALIASES) + CODEX_MODEL_SLUGS

CLAUDE_MODELS: tuple[str, ...] = ("sonnet", "opus", "haiku")

CodexModel = Literal[CODEX_MODEL_NAMES]  # type: ignore[valid-type]
ClaudeModel = Literal[CLAUDE_MODELS]  # type: ignore[valid-type]
ReasoningEffort = Literal[REASONING_EFFORTS]  # type: ignore[valid-type]
ModelName = Union[CodexModel, ClaudeModel]


class TaskToolInput(BaseModel):
    description: str = Field(
        description="A short (3-5 word) description of the task",
        min_length=1,
    )
    prompt: str = Field(
        description="The task for the agent to perform",
        min_length=1,
    )
    subagent_type: str = Field(
        description="The type of specialized agent to use for this task",
        min_length=1,
    )
    model: Optional[ModelName] = Field(
        default=None,
        description=(
            "Optional model to use for this agent. If not specified, inherits from parent. "
            "Claude models: sonnet, opus, haiku. Codex aliases: sol, astra, luna, terra, "
            "codex (default, gpt-6-astra). Codex slugs: gpt-6-sol, gpt-6-astra, gpt-6-luna, "
            "gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-5.5."
        ),
    )
    reasoning_effort: Optional[ReasoningEffort] = Field(
        default=None,
        description=(
            "Optional Codex reasoning effort: low, medium, high, xhigh, max, ultra "
            "(supported levels vary by model). When omitted, no effort override is passed "
            "and the Codex CLI config (~/.codex/config.toml) applies. Ignored by the Claude runner."
        ),
    )
    run_in_background: Optional[bool] = Field(
        default=None,
        description=(
            "Set to true to run this agent in the background. The tool result will include an "
            "output_file path - use Read tool or Bash tail to check on output."
        ),
    )
    max_turns: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "Maximum number of agentic turns (API round-trips) before stopping. "
            "Used internally for warmup."
        ),
    )
    resume: Optional[str] = Field(
        default=None,
        description=(
            "Optional agent ID to resume from. If provided, the agent will continue from the "
            "previous execution transcript."
        ),
    )

    model_config = {
        "extra": "forbid",
    }


class TaskToolOutputForeground(BaseModel):
    output: str = Field(
        description="The agent's completion message",
        min_length=1,
    )
    agentId: str = Field(
        description="Unique identifier for the agent execution",
        min_length=1,
    )

    model_config = {
        "extra": "forbid",
    }


class TaskToolOutputBackground(BaseModel):
    output: str = Field(
        description="Async agent launched successfully.",
        min_length=1,
    )
    agentId: str = Field(
        description="Unique identifier",
        min_length=1,
    )
    output_file: str = Field(
        description="Path to JSONL file containing agent transcript; monitor with TaskOutput, Read, or Bash tail",
        min_length=1,
    )

    model_config = {
        "extra": "forbid",
    }


TaskToolOutput = Union[TaskToolOutputForeground, TaskToolOutputBackground]


def task_tool_input_schema() -> dict:
    return TaskToolInput.model_json_schema()
