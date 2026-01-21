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


CodexModel = Literal[
    "codex",
    "gpt-5.2-codex",
    "codex-max",
    "max",
    "gpt-5.1-codex-max",
    "codex-mini",
    "mini",
    "gpt-5.1-codex-mini",
    "gpt-5",
    "gpt-5.2",
    "gtp-5",
]
ClaudeModel = Literal["sonnet", "opus", "haiku"]
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
            "Claude models: sonnet, opus, haiku. Codex models: codex, max/codex-max, "
            "mini/codex-mini, gpt-5, or full model names."
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
