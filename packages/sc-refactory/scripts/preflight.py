#!/usr/bin/env python3
"""Pre-flight check for refactor skills."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from runtime import append_log, find_repo_root, resolve_oxigraph

GUIDE_PATH = "./.refactor/docs/install-and-troubleshooting.md"


def check_oxigraph() -> tuple[bool, str]:
    oxigraph = resolve_oxigraph()
    if oxigraph is None:
        return False, "oxigraph is not installed or not on PATH"
    try:
        result = subprocess.run(
            [str(oxigraph), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "oxigraph is not installed or not on PATH"
    if result.returncode != 0:
        return False, "oxigraph is not installed or not on PATH"
    version = result.stdout.strip()
    if version.startswith("oxigraph "):
        version = "oxigraph v " + version.removeprefix("oxigraph ").strip()
    return True, version


def check_paths(root: Path) -> tuple[bool, str]:
    required = [
        root / ".refactor" / "rules",
        root / ".refactor" / "docs",
        root / ".refactor" / "scripts" / "session_start.py",
    ]
    missing = [str(p.relative_to(root)) for p in required if not p.exists()]
    if missing:
        return False, f"missing required paths: {', '.join(missing)}"
    return True, "paths present"


def check_db_query(root: Path) -> tuple[bool, str]:
    db_dir = root / ".refactor" / "db"
    if not db_dir.is_dir():
        return False, "missing .refactor/db; run the session_start rebuild path"

    oxigraph = resolve_oxigraph()
    if oxigraph is None:
        return False, "oxigraph is not installed or not on PATH"

    try:
        result = subprocess.run(
            [
                str(oxigraph),
                "query",
                "--location",
                str(db_dir),
                "--query",
                "PREFIX ref: <https://synaptic.canvas/refactor/> SELECT ?s WHERE { ?s ?p ?o } LIMIT 1",
                "--results-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "oxigraph is not installed or not on PATH"
    if result.returncode != 0:
        return False, "unable to query .refactor/db"
    return True, "db query ok"


def rebuild_db(root: Path) -> tuple[bool, str]:
    startup = root / ".refactor" / "scripts" / "session_start.py"
    if not startup.is_file():
        return False, "missing .refactor/scripts/session_start.py"

    result = subprocess.run(
        ["python3", str(startup), "--mode", "startup"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, "session_start.py returned non-zero"

    if not (root / ".refactor" / "db").is_dir():
        return False, "session_start.py did not rebuild .refactor/db"

    return True, "db rebuilt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-flight check for refactor skills")
    parser.add_argument(
        "--skill",
        default="refactor",
        choices=["refactor", "refactor-lookup", "refactor-write"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = find_repo_root(Path(__file__))
    append_log(root, "preflight.log", f"start skill={args.skill}")

    oxigraph_ok, oxigraph_version = check_oxigraph()
    path_ok, path_message = check_paths(root)
    db_dir = root / ".refactor" / "db"

    db_check: tuple[bool, str]
    if oxigraph_ok and path_ok and not db_dir.is_dir():
        append_log(root, "preflight.log", "db missing; invoking session_start rebuild")
        rebuild_ok, rebuild_message = rebuild_db(root)
        append_log(root, "preflight.log", f"db rebuild result ok={rebuild_ok} message='{rebuild_message}'")
        if rebuild_ok:
            db_check = check_db_query(root)
        else:
            db_check = (False, rebuild_message)
    else:
        db_check = check_db_query(root)

    checks = [
        (oxigraph_ok, oxigraph_version),
        (path_ok, path_message),
        db_check,
    ]
    failures = [message for ok, message in checks if not ok]

    if not failures:
        append_log(root, "preflight.log", f"success skill={args.skill} version='{oxigraph_version}'")
        print(f"{oxigraph_version} checks pass")
        sys.exit(0)

    append_log(root, "preflight.log", f"failure skill={args.skill} reasons={failures}")
    print(f"tools are not installed or working to use this skill. please read {GUIDE_PATH}")
    sys.exit(1)


if __name__ == "__main__":
    main()
