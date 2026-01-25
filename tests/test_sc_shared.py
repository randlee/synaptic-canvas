#!/usr/bin/env python3
"""Unit tests for shared script helpers."""

import json
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

SHARED_DIR = Path(__file__).parent.parent / "packages" / "shared" / "scripts"
sys.path.insert(0, str(SHARED_DIR))

from sc_shared import (
    extract_hook_json,
    extract_json_from_command,
    get_tool_command,
    is_path_allowed,
    is_git_repo,
    validate_allowed_path,
    validate_hook_json,
    validate_json_payload,
)


class HookParams(BaseModel):
    branch: str
    base: str


def test_get_tool_command_from_payload():
    payload = {"tool_input": {"command": "python3 foo '{\"a\": 1}'"}}
    assert get_tool_command(payload) == "python3 foo '{\"a\": 1}'"

    payload = {"command": "echo '{\"a\": 2}'"}
    assert get_tool_command(payload) == "echo '{\"a\": 2}'"


def test_extract_json_from_command_direct():
    data = extract_json_from_command('{"branch": "x", "base": "main"}')
    assert data["branch"] == "x"


def test_extract_json_from_command_embedded():
    data = extract_json_from_command("python3 tool '{\"branch\": \"x\", \"base\": \"main\"}'")
    assert data == {"branch": "x", "base": "main"}


def test_extract_json_from_command_invalid():
    with pytest.raises(ValueError):
        extract_json_from_command("python3 tool no-json")


def test_extract_hook_json():
    payload = {"tool_input": {"command": "do '{\"branch\": \"x\", \"base\": \"main\"}'"}}
    data = extract_hook_json(payload)
    assert data["base"] == "main"


def test_validate_json_payload():
    model = validate_json_payload({"branch": "x", "base": "main"}, HookParams)
    assert model.branch == "x"


def test_validate_hook_json():
    payload = {"tool_input": {"command": "do '{\"branch\": \"x\", \"base\": \"main\"}'"}}
    model = validate_hook_json(payload, HookParams)
    assert model.base == "main"


def test_path_validation(tmp_path: Path):
    allowed = {tmp_path.resolve()}
    target = tmp_path / "repo"
    target.mkdir()

    assert is_path_allowed(target, allowed) is True
    resolved = validate_allowed_path(target, allowed, label="repo_root")
    assert resolved == target.resolve()

    outside = tmp_path.parent / "other"
    outside.mkdir()
    assert is_path_allowed(outside, allowed) is False
    with pytest.raises(ValueError):
        validate_allowed_path(outside, allowed, label="repo_root")


def test_is_git_repo(tmp_path: Path):
    assert is_git_repo(tmp_path) is False
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)
    assert is_git_repo(tmp_path) is True
