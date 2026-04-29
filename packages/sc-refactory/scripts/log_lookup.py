#!/usr/bin/env python3
"""Append refactor lookup request/result logs."""

from __future__ import annotations

import argparse
import json
import sys

from runtime import append_json_log, find_repo_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log refactor lookup activity")
    parser.add_argument("--stage", required=True, choices=["request", "result"])
    parser.add_argument("--status", default=None)
    parser.add_argument("--rule-id", default=None)
    parser.add_argument("--error-code", default=None)
    parser.add_argument("--source", default="refactor-lookup")
    parser.add_argument("--payload-file", default=None)
    return parser.parse_args()


def load_payload(payload_file: str | None) -> dict:
    if payload_file:
        with open(payload_file, encoding="utf-8") as handle:
            return json.load(handle)
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def main() -> None:
    args = parse_args()
    root = find_repo_root()
    payload = load_payload(args.payload_file)
    append_json_log(
        root,
        "lookup.log",
        {
            "source": args.source,
            "stage": args.stage,
            "status": args.status,
            "rule_id": args.rule_id,
            "error_code": args.error_code,
            "payload": payload,
        },
    )


if __name__ == "__main__":
    main()
