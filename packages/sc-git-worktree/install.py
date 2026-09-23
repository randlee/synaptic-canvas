"""sc-install hook for sc-git-worktree.

For --local installs, renders each shipped *.j2 template with this repo's
name and copies the result over the already-installed plain file. Repo name
is obtained by walking up from destination_path to the worktree root (`git
rev-parse --show-toplevel`), not passed in via options, since it's cheap to
derive and destination_path is always known.

Global/user installs never have a meaningful "this repo" (and this package's
manifest.yaml declares install.scope: local-only anyway), so complete() is a
no-op unless options["local"] is set and a repo is actually found.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict


def _repo_basename(destination_path: str) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path(destination_path).parent,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout.strip()
    except Exception:
        return ""
    return Path(out).name if out else ""


def complete(source_path: str, destination_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    if not options.get("local"):
        return {"result": "success"}

    repo_name = _repo_basename(destination_path)
    if not repo_name:
        return {"result": "success"}

    src_root = Path(source_path)
    dst_root = Path(destination_path)

    for j2 in sorted(src_root.rglob("*.j2")):
        rel = j2.relative_to(src_root).with_suffix("")
        dst = dst_root / rel
        if not dst.exists():
            continue
        proc = subprocess.run(
            [
                "sc-compose",
                "render",
                "--file",
                str(j2),
                "--var",
                f"REPO_NAME={repo_name}",
                "--output",
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {
                "result": "fail",
                "message": (
                    f"sc-compose render failed for {rel}: "
                    f"{proc.stderr.strip() or proc.stdout.strip()}. "
                    "Fix: ensure sc-compose is installed and on PATH "
                    f"(pip install sc-compose) and that {j2} is a valid sc-compose template."
                ),
            }

    return {"result": "success"}
