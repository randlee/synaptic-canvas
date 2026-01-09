#!/usr/bin/env python3
"""
Shared board configuration loader/validator for sc-kanban and sc-project-manager.

- Schema is versioned (0.7) and strict: extra keys are rejected.
- Provider can be "kanban" (preferred) or "checklist" (fallback).
- Uses PyYAML + Pydantic v2 for strict validation and returns typed models.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml  # type: ignore
from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator, model_validator

DEFAULT_BOARD_CONFIG_PATH = Path(".project/board.config.yaml")


class Column(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    name: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("column id cannot be empty")
        return v


class Wip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_column: Dict[str, int] = Field(default_factory=dict)

    @field_validator("per_column")
    @classmethod
    def _non_negative(cls, v: Dict[str, int]) -> Dict[str, int]:
        for col, limit in v.items():
            if limit is None:
                raise ValueError(f"WIP limit missing for column '{col}'")
            if limit < 0:
                raise ValueError(f"WIP limit for column '{col}' must be >= 0")
        return v


class BoardSection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    backlog_path: str
    board_path: str
    done_path: str
    provider: Literal["kanban", "checklist"]
    wip: Wip = Field(default_factory=Wip)
    columns: List[Column]

    @field_validator("backlog_path", "board_path", "done_path")
    @classmethod
    def _path_not_empty(cls, v: str, info: ValidationInfo) -> str:
        if not v:
            raise ValueError(f"board.{info.field_name} cannot be empty")
        return v

    @field_validator("columns")
    @classmethod
    def _columns_unique(cls, v: List[Column]) -> List[Column]:
        if not v:
            raise ValueError("board.columns must contain at least one column")
        ids = [c.id for c in v]
        if len(set(ids)) != len(ids):
            raise ValueError("board.columns ids must be unique")
        return v


class CardField(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    required: bool = False
    type: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("cards.fields.id cannot be empty")
        return v


class Conventions(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    worktree_pattern: str
    sprint_id_grammar: str

    @field_validator("worktree_pattern", "sprint_id_grammar")
    @classmethod
    def _not_empty(cls, v: str, info: ValidationInfo) -> str:
        if not v:
            raise ValueError(f"cards.conventions.{info.field_name} cannot be empty")
        return v


class CardsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: List[CardField]
    conventions: Conventions

    @field_validator("fields")
    @classmethod
    def _fields_unique(cls, v: List[CardField]) -> List[CardField]:
        if not v:
            raise ValueError("cards.fields must contain at least one field")
        ids = [f.id for f in v]
        if len(set(ids)) != len(ids):
            raise ValueError("cards.fields ids must be unique")
        return v


class AgentsSection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transition: Optional[str] = None
    query: Optional[str] = None
    checklist_fallback: Optional[str] = None

    @field_validator("transition", "query", "checklist_fallback")
    @classmethod
    def _non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v:
            raise ValueError("agent identifiers cannot be empty strings")
        return v


class BoardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal["0.7"]
    board: BoardSection
    cards: CardsSection
    agents: AgentsSection

    @model_validator(mode="after")
    def _provider_requirements(self) -> "BoardConfig":  # type: ignore[name-defined]
        provider = self.board.provider
        if provider == "kanban":
            if not self.agents.transition or not self.agents.query:
                raise ValueError("provider=kanban requires agents.transition and agents.query")
        elif provider == "checklist":
            if not self.agents.checklist_fallback:
                raise ValueError("provider=checklist requires agents.checklist_fallback")
        else:
            raise ValueError(f"unsupported provider '{provider}'")
        return self


@dataclass
class BoardConfigError(Exception):
    message: str
    path: Path

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _load_yaml_file(path: Path) -> Dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - relies on PyYAML error paths
        raise BoardConfigError(f"Invalid YAML: {exc}", path)


def load_board_config(path: Path | str | None = None) -> BoardConfig:
    cfg_path = Path(path) if path else DEFAULT_BOARD_CONFIG_PATH
    if not cfg_path.is_file():
        raise BoardConfigError("Board config file not found", cfg_path)
    raw = _load_yaml_file(cfg_path)
    try:
        return BoardConfig.model_validate(raw)
    except ValidationError as exc:
        raise BoardConfigError(f"Invalid board config: {exc}", cfg_path)
