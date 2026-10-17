#!/usr/bin/env python3
"""Claude and Codex models, aliases, reasoning-effort levels, and the CLI flags for them.

The one model table for sc-launchpad, sc-launch-term, and sc-codex. Canonical copy:
``packages/shared/scripts/agent_models.py``; packages receive byte-identical copies via
``python3 scripts/sync-shared-scripts.py`` (declared under ``shared_scripts`` in each
manifest). Never edit a package copy.

``tests/test_agent_model_drift.py`` compares this table with what the installed
``claude`` and ``codex`` CLIs report (``python3 scripts/agent_model_discovery.py``
prints the same live data) and names the exact edits when it is stale.

Standard library only; Python 3.9+.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

TOOLS = ("claude", "codex")

# Every level either CLI knows, lowest first.
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")


class ModelSpec(NamedTuple):
    id: str
    efforts: Tuple[str, ...]
    # The model's own default when no effort is passed; None when the CLI does not say.
    default_effort: Optional[str]


def _up_to(top: str) -> Tuple[str, ...]:
    return EFFORTS[: EFFORTS.index(top) + 1]


# `claude --help`: --effort <level> (low, medium, high, xhigh, max), for every model.
CLAUDE_EFFORTS = _up_to("max")

MODELS: Dict[str, Dict[str, ModelSpec]] = {
    "claude": {
        model_id: ModelSpec(model_id, CLAUDE_EFFORTS, None)
        for model_id in ("claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
    },
    # `codex app-server` model/list (codex-cli 0.162.1), newest first.
    "codex": {
        spec.id: spec
        for spec in (
            ModelSpec("gpt-6.1-sol", _up_to("ultra"), "low"),
            ModelSpec("gpt-6-astra", _up_to("ultra"), "medium"),
            ModelSpec("gpt-6-sol", _up_to("ultra"), "medium"),
            ModelSpec("gpt-6-luna", _up_to("max"), "medium"),
            ModelSpec("gpt-5.6-sol", _up_to("ultra"), "low"),
            ModelSpec("gpt-5.6-terra", _up_to("ultra"), "medium"),
            ModelSpec("gpt-5.6-luna", _up_to("max"), "medium"),
        )
    },
}

# Short names. Each family alias points at the newest model of that family; `codex`
# is the Codex CLI's own default model.
ALIASES: Dict[str, Dict[str, str]] = {
    "claude": {
        "fable": "claude-fable-5-1",
        "opus": "claude-opus-5-5",
        "sonnet": "claude-sonnet-5-5",
        "haiku": "claude-haiku-5-5",
    },
    "codex": {
        "astra": "gpt-6-astra",
        "sol": "gpt-6.1-sol",
        "terra": "gpt-5.6-terra",
        "luna": "gpt-6-luna",
        "codex": "gpt-6.1-sol",
    },
}

# Used when a launch names no model: the newest flagship of each tool.
DEFAULT_ALIAS = {"claude": "fable", "codex": "sol"}


class ModelError(ValueError):
    """Unknown model or unsupported effort; the message lists the valid choices."""


def model_choices(tool: str) -> List[str]:
    """Aliases first, then full model ids."""
    return list(ALIASES[tool]) + list(MODELS[tool])


def resolve_model(tool: str, name: Optional[str] = None) -> ModelSpec:
    """Map an alias or full id (default: the tool's default) to its ``ModelSpec``."""
    name = name or DEFAULT_ALIAS[tool]
    model_id = ALIASES[tool].get(name, name)
    spec = MODELS[tool].get(model_id)
    if spec is None:
        raise ModelError(
            f"Unknown {tool} model '{name}'. Use an alias ({', '.join(ALIASES[tool])}) "
            f"or a full id ({', '.join(MODELS[tool])})."
        )
    return spec


def resolve_effort(spec: ModelSpec, effort: Optional[str]) -> Optional[str]:
    """Validate ``effort`` for the model; None means "pass no flag, use the CLI's default"."""
    if effort is None:
        return None
    if effort not in spec.efforts:
        raise ModelError(
            f"Effort '{effort}' is not supported by {spec.id}. Supported: {', '.join(spec.efforts)}."
        )
    return effort


def alias_for(tool: str, model_id: str) -> Optional[str]:
    """The family alias that points at ``model_id`` (never the `codex` catch-all), if any."""
    for alias, target in ALIASES[tool].items():
        if target == model_id and alias != tool:
            return alias
    return None


def model_flags(tool: str, spec: ModelSpec, effort: Optional[str]) -> List[str]:
    """``--model <id>`` plus the effort flag. Values carry no quotes (Windows .cmd shims)."""
    flags = ["--model", spec.id]
    if effort is not None:
        flags += ["--effort", effort] if tool == "claude" else ["-c", f"model_reasoning_effort={effort}"]
    return flags
