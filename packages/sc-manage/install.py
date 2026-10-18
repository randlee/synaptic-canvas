"""Remember a local source checkout for installed managing-sc-packages helpers.

This is nonsecret install metadata, not a host plugin-registration or trust edit.
"""
import json
from pathlib import Path

# Cumulative hook-owned outputs. Keep entries when retiring an output, and
# delete retired paths in complete() as well as cleanup(). This JSON record is
# generated per installation, not a source artifact.
INVENTORY = ["scripts/sc_manage_source.json"]


def complete(source_path, destination_path, options):
    source = Path(source_path).resolve().parent.parent
    if not (source / "tools/sc-install.py").is_file():
        return {"result": "fail", "message": "Source checkout lacks tools/sc-install.py; install sc-manage from a complete Synaptic Canvas checkout"}
    record = Path(destination_path) / "scripts/sc_manage_source.json"
    try:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"sc_repo_path": str(source)}, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"result": "fail", "message": f"Cannot write source-location metadata: {exc}; check destination permissions and retry"}
    return {"result": "success"}


def cleanup(source_path, destination_path, options):
    record = Path(destination_path) / "scripts/sc_manage_source.json"
    try:
        record.unlink(missing_ok=True)
    except OSError as exc:
        return {"result": "fail", "message": f"Cannot remove source-location metadata: {exc}; check destination permissions and retry"}
    return {"result": "success"}
