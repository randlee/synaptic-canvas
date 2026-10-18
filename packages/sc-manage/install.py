"""Remember the source checkout and, on Cursor, write a native /sc-manage command.

This is nonsecret install metadata, not a host plugin-registration or trust edit.
"""
import json
from pathlib import Path

# Cumulative hook-owned outputs. Keep entries when retiring an output, and
# delete retired paths in complete() as well as cleanup(). Generated Cursor
# command shares the dest path of Claude's manifest command; only write it
# for the cursor target so Claude's copy is left unchanged.
INVENTORY = ["scripts/sc_manage_source.json", "commands/sc-manage.md"]

_SOURCE_RECORD = "scripts/sc_manage_source.json"
_CURSOR_COMMAND = "commands/sc-manage.md"
_CURSOR_COMMAND_SRC = "cursor/sc-manage.md"


def _is_cursor(options):
    return options.get("target") == "cursor" or options.get("cursor") is True


def complete(source_path, destination_path, options):
    source = Path(source_path).resolve().parent.parent
    if not (source / "tools/sc-install.py").is_file():
        return {"result": "fail", "message": "Source checkout lacks tools/sc-install.py; install sc-manage from a complete Synaptic Canvas checkout"}
    dest = Path(destination_path)
    record = dest / _SOURCE_RECORD
    try:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"sc_repo_path": str(source)}, indent=2) + "\n", encoding="utf-8")
        if _is_cursor(options):
            template = Path(source_path) / _CURSOR_COMMAND_SRC
            if not template.is_file():
                return {"result": "fail", "message": f"Missing {_CURSOR_COMMAND_SRC}; install sc-manage from a complete package tree"}
            command = dest / _CURSOR_COMMAND
            command.parent.mkdir(parents=True, exist_ok=True)
            command.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        return {"result": "fail", "message": f"Cannot write source-location metadata: {exc}; check destination permissions and retry"}
    return {"result": "success"}


def cleanup(source_path, destination_path, options):
    dest = Path(destination_path)
    paths = [dest / _SOURCE_RECORD]
    if _is_cursor(options):
        paths.append(dest / _CURSOR_COMMAND)
    try:
        for path in paths:
            path.unlink(missing_ok=True)
    except OSError as exc:
        return {"result": "fail", "message": f"Cannot remove source-location metadata: {exc}; check destination permissions and retry"}
    return {"result": "success"}
