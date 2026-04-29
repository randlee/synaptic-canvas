#!/usr/bin/env python3
"""Inject the refactor trigger index into session startup context."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime import append_log, find_repo_root, resolve_oxigraph


QUERY = """
PREFIX ref: <https://synaptic.canvas/refactor/>
SELECT DISTINCT ?signal WHERE {
  ?r a ref:Rule .
  { ?r ref:triggeredByNamespace ?signal }
  UNION
  { ?r ref:triggeredByType      ?signal }
  UNION
  { ?r ref:triggeredByError     ?signal }
  UNION
  { ?r ref:triggeredByString    ?signal }
  UNION
  { ?r ref:triggeredByAssembly  ?signal }
}
ORDER BY ?signal
"""

def load_rules_into_db(rules_dir: Path, db_dir: Path, oxigraph: Path) -> None:
    """Load all tracked Turtle rule files into a fresh Oxigraph store."""
    db_dir.mkdir(parents=True, exist_ok=True)

    for ttl in sorted(rules_dir.glob("*.ttl")):
        result = subprocess.run(
            [str(oxigraph), "load", "--location", str(db_dir), "--file", str(ttl)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to load {ttl.name}: {result.stderr.strip()}")


def query_triggers(db_dir: Path, query_dir: Path, oxigraph: Path) -> list[dict]:
    """Run the trigger query against a store and return JSON bindings."""
    query_dir.mkdir(parents=True, exist_ok=True)
    query_file = query_dir / "startup-query.rq"
    query_file.write_text(QUERY, encoding="utf-8")

    result = subprocess.run(
        [
            str(oxigraph),
            "query",
            "--location",
            str(db_dir),
            "--query-file",
            str(query_file),
            "--results-format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"startup trigger query failed: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("startup trigger query returned invalid JSON")
    return data.get("results", {}).get("bindings", [])


def publish_db(build_dir: Path, db_dir: Path, temp_dir: Path) -> None:
    """Swap a validated build directory into place atomically enough for startup."""
    backup_dir = temp_dir / "db-previous"
    if backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)

    if db_dir.exists():
        db_dir.rename(backup_dir)

    try:
        build_dir.rename(db_dir)
    except Exception:
        if backup_dir.exists() and not db_dir.exists():
            backup_dir.rename(db_dir)
        raise
    else:
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)


def rebuild_db_from_rules(rules_dir: Path, db_dir: Path, temp_dir: Path, oxigraph: Path) -> list[dict]:
    """
    Rebuild the runtime DB from committed Turtle rules, validate it with the
    startup query, and only then publish it to .refactor/db.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix="db-build-", dir=temp_dir))

    try:
        load_rules_into_db(rules_dir, build_dir, oxigraph)
        bindings = query_triggers(build_dir, temp_dir, oxigraph)
        publish_db(build_dir, db_dir, temp_dir)
        return bindings
    finally:
        if build_dir.exists():
            shutil.rmtree(build_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refactor trigger index for session context")
    parser.add_argument("--mode", default="startup", choices=["startup", "resume", "clear", "compact"])
    parser.add_argument("--atm-team", default=None)
    parser.add_argument("--atm-identity", default=None)
    return parser.parse_args()


def emit_trigger_index(bindings: list[dict], args: argparse.Namespace) -> None:
    print("# REFACTOR TRIGGERS")
    print("# Approved fix patterns only. On match -> invoke refactor-lookup.")
    print("# Use /refactor-lookup <trigger> <additional-context-error-logs> when one of these items appears in a build error.")
    if args.atm_team or args.atm_identity:
        team = args.atm_team or "-"
        identity = args.atm_identity or "-"
        print(f"# ATM team: {team}  identity: {identity}")
    print("#")
    if not bindings:
        print("# (no triggers registered)")
        return
    for binding in bindings:
        signal = binding["signal"]["value"]
        print(signal)


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root(Path(__file__))
    refactor_root = repo_root / ".refactor"
    temp_dir = refactor_root / "temp"
    oxigraph = resolve_oxigraph()
    append_log(repo_root, "session_start.log", f"start mode={args.mode}")

    if oxigraph is None:
        append_log(repo_root, "session_start.log", "skip reason='oxigraph binary not found'")
        sys.exit(0)

    rules_dir = refactor_root / "rules"
    db_dir = refactor_root / "db"

    if not rules_dir.is_dir():
        append_log(repo_root, "session_start.log", "skip reason='rules directory missing'")
        sys.exit(0)

    try:
        append_log(
            repo_root,
            "session_start.log",
            f"rebuild begin rules_dir='{rules_dir}' db_dir='{db_dir}' oxigraph='{oxigraph}'",
        )
        bindings = rebuild_db_from_rules(rules_dir, db_dir, temp_dir, oxigraph)
    except RuntimeError as exc:
        append_log(repo_root, "session_start.log", f"failure {exc}")
        sys.exit(0)

    append_log(repo_root, "session_start.log", f"success trigger_count={len(bindings)}")
    emit_trigger_index(bindings, args)


if __name__ == "__main__":
    main()
