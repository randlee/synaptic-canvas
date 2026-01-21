#!/usr/bin/env python3
"""
Agent Runner for background-friendly CLI execution.

Reads JSON from stdin, validates it with pydantic, loads the agent instructions,
then calls the selected CLI runner (Claude or Codex) with a composed prompt.

Example:
  cat <<'JSON' | python3 tools/claude-agent-runner.py
  {
    "agent": "sc-worktree-create",
    "params": { "branch": "feature-x", "base": "main" },
    "model": "haiku",
    "runner": "claude"
  }
  JSON
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, Field, ValidationError
except Exception:  # pragma: no cover
    print("pydantic is required. Install with: pip install pydantic>=2.7", file=sys.stderr)
    sys.exit(2)

# Allow `python3 tools/claude-agent-runner.py` to import local package
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from agent_runner.runner import REGISTRY_DEFAULT, validate_agent  # noqa: E402


class AgentRunInput(BaseModel):
    agent: str = Field(min_length=1)
    params: Dict[str, Any] = Field(default_factory=dict)
    model: Optional[str] = None
    registry_path: str = Field(default=REGISTRY_DEFAULT)
    claude_bin: str = Field(default="claude")
    codex_bin: str = Field(default="codex")
    runner: str = Field(default="claude", pattern=r"^(claude|codex)$")
    timeout_s: Optional[int] = Field(default=None, ge=1)


def _read_stdin_json() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("Expected JSON input on stdin")
    return json.loads(raw)


def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            fm = "\n".join(lines[1:idx])
            body = "\n".join(lines[idx + 1 :])
            return fm, body
    return "", text


def _parse_frontmatter_model(fm_text: str) -> Optional[str]:
    if not fm_text:
        return None
    match = re.search(r"^model:\s*(.+)$", fm_text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def _load_agent_body(path: str) -> tuple[str, Optional[str]]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    fm, body = _split_frontmatter(text)
    fm_model = _parse_frontmatter_model(fm)
    return body.strip(), fm_model


def _build_prompt(agent_name: str, body: str, params: Dict[str, Any]) -> str:
    params_json = json.dumps(params, indent=2, ensure_ascii=True)
    return "\n".join(
        [
            f"You are the {agent_name} agent. Follow the instructions below exactly.",
            "",
            body,
            "",
            "## Inputs",
            "```json",
            params_json,
            "```",
            "",
            "Return ONLY fenced JSON as described in the agent instructions.",
        ]
    )


def _run_cli(
    runner: str, claude_bin: str, codex_bin: str, model: Optional[str], prompt: str, timeout_s: Optional[int]
) -> int:
    if runner == "codex":
        cmd = [codex_bin, "exec"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
    else:
        cmd = [claude_bin]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--print", prompt])

    try:
        res = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print(f"{runner} CLI timed out", file=sys.stderr)
        return 124
    if res.stdout:
        sys.stdout.write(res.stdout)
    if res.stderr:
        sys.stderr.write(res.stderr)
    return res.returncode


def main() -> int:
    try:
        payload = _read_stdin_json()
        data = AgentRunInput.model_validate(payload)
        spec, info = validate_agent(registry_path=data.registry_path, agent_name=data.agent)
        body, fm_model = _load_agent_body(info.path)
        model = data.model or fm_model
        if not model:
            raise ValueError("Model not specified; provide 'model' or set frontmatter model")
        prompt = _build_prompt(spec.name, body, data.params)
        return _run_cli(data.runner, data.claude_bin, data.codex_bin, model, prompt, data.timeout_s)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
