"""
Shared response filtering and regex helpers for expectation matching.

This module centralizes response filtering so fixtures can rely on
consistent behavior across expectations and report evaluation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

from .collector import CollectedData

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutputFilterConfig:
    """Configuration for output filtering.

    response_filter:
        - "assistant_all": match across all assistant responses (default)
        - "assistant_last": match only the final assistant response
    exclude_prompt:
        If True, remove the exact prompt text from response text before matching.
    """

    response_filter: str = "assistant_all"
    exclude_prompt: bool = True


def compile_output_pattern(
    pattern: str,
    flags: str,
    case_sensitive: bool,
) -> re.Pattern:
    """Compile a regex pattern with normalized flags.

    Default behavior is case-insensitive unless explicitly overridden.
    """
    effective_flags = flags or ""
    if not case_sensitive and "i" not in effective_flags:
        effective_flags += "i"

    regex_flags = 0
    if "i" in effective_flags:
        regex_flags |= re.IGNORECASE
    if "m" in effective_flags:
        regex_flags |= re.MULTILINE
    if "s" in effective_flags:
        regex_flags |= re.DOTALL

    return re.compile(pattern, regex_flags)


def filter_response_texts(
    data: CollectedData,
    config: OutputFilterConfig,
) -> list[str]:
    """Return response texts after applying shared filters."""
    texts = [response.text for response in data.claude_responses]

    if config.response_filter == "assistant_last":
        texts = texts[-1:] if texts else []
    elif config.response_filter != "assistant_all":
        logger.warning("Unknown response_filter '%s'; defaulting to assistant_all", config.response_filter)

    if config.exclude_prompt and data.prompt:
        prompt = data.prompt
        texts = [text.replace(prompt, "") for text in texts]

    return texts
