#!/usr/bin/env python3
"""Install the refactory runtime into a target repository."""

from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
from pathlib import Path


INSTALL_GUIDE_FALLBACK = """# Refactor Install And Troubleshooting

Use this guide when a refactor skill pre-flight fails.

## Expected Layout

- rules: `.refactor/rules/`
- docs: `.refactor/docs/`
- runtime DB: `.refactor/db/`
- startup/rebuild scripts: `.refactor/scripts/`
- temp files and logs: `.refactor/temp/` and `.refactor/logs/`

## Supported Runtime

Install `oxigraph` from crates.io, not from Homebrew.

This workflow was tested with:

```text
oxigraph 0.5.7
```

## Installation

```bash
cargo install oxigraph-cli
oxigraph --version
```

## Pre-flight

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-lookup
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-write
```

Success output:

```text
oxigraph v 0.5.7 checks pass
```

Failure output:

```text
tools are not installed or working to use this skill. please read ./.refactor/docs/install-and-troubleshooting.md
```

## Repair

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-lookup
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-write
```

## Source Of Truth

The committed source of truth is:

- `.refactor/rules/*.ttl`
- `.refactor/docs/*.md`

Do not commit:

- `.refactor/db/`
- `.refactor/logs/`
- `.refactor/temp/`
"""


RULE_DOC_TEMPLATE_FALLBACK = """# <Rule Title>

## Summary

<One paragraph describing the approved fix policy.>

## Triggers

- `<trigger-1>`
- `<trigger-2>`

## Why This Rule Exists

<Rationale and migration context.>
"""


RULE_TTL_TEMPLATE_FALLBACK = """@prefix ref: <https://synaptic.canvas/refactor/> .

ref:RULE_ID
    a ref:Rule ;
    ref:ruleId "RULE_ID" ;
    ref:severity "warning" ;
    ref:ruleText "Replace this template with an approved rule." ;
    ref:triggeredByString "TRIGGER_VALUE" .
"""


STARTUP_WRAPPER_FALLBACK = """#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / ".refactor" / "scripts" / "session_start.py"
    args = ["python3", str(script), *sys.argv[1:]]
    return subprocess.call(args, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
"""


GITIGNORE = "/db/\n/logs/\n/temp/\n"

SCRIPT_NAMES = [
    "runtime.py",
    "session_start.py",
    "preflight.py",
    "repair.py",
    "log_lookup.py",
    "rebuild_db.py",
    "sync_subset.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install refactory runtime into a repository")
    parser.add_argument("--repo-root", default=None, help="Target repository root")
    parser.add_argument("--force", action="store_true", help="Overwrite existing runtime files")
    parser.add_argument(
        "--seed",
        choices=["empty", "templates"],
        default="templates",
        help="Whether to install empty runtime only or include starter templates",
    )
    return parser.parse_args()


def resolve_repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except subprocess.CalledProcessError:
        return Path.cwd().resolve()


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and not force:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def read_reference(package_root: Path, relative_path: str, fallback: str) -> str:
    path = package_root / relative_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def install_runtime(repo_root: Path, package_root: Path, force: bool) -> None:
    refactor_root = repo_root / ".refactor"
    for rel in [
        "docs",
        "rules",
        "profiles",
        "scripts",
        "reports",
        "db",
        "logs",
        "temp",
    ]:
        (refactor_root / rel).mkdir(parents=True, exist_ok=True)

    write_text(refactor_root / ".gitignore", GITIGNORE, force)
    write_text(
        refactor_root / "docs" / "install-and-troubleshooting.md",
        read_reference(
            package_root,
            "references/install-and-troubleshooting.md",
            INSTALL_GUIDE_FALLBACK,
        ),
        force,
    )

    package_script_dir = package_root / "scripts"
    for name in SCRIPT_NAMES:
        src = package_script_dir / name
        dst = refactor_root / "scripts" / name
        copy_file(src, dst, force)
        make_executable(dst)

    startup_dir = repo_root / ".startup"
    startup_dir.mkdir(parents=True, exist_ok=True)
    startup = startup_dir / "team-lead"
    write_text(
        startup,
        read_reference(
            package_root,
            "assets/startup-wrapper-template/team-lead.py",
            STARTUP_WRAPPER_FALLBACK,
        ),
        force,
    )
    make_executable(startup)


def install_templates(repo_root: Path, package_root: Path, force: bool) -> None:
    docs_dir = repo_root / ".refactor" / "docs"
    rules_dir = repo_root / ".refactor" / "rules"

    write_text(
        docs_dir / "rule-template.md",
        read_reference(
            package_root,
            "references/rule-doc-template.md",
            RULE_DOC_TEMPLATE_FALLBACK,
        ),
        force,
    )
    write_text(
        rules_dir / "rule-template.ttl",
        read_reference(
            package_root,
            "references/rule-ttl-template.ttl",
            RULE_TTL_TEMPLATE_FALLBACK,
        ),
        force,
    )


def preview_startup(repo_root: Path) -> str:
    script = repo_root / ".refactor" / "scripts" / "session_start.py"
    result = subprocess.run(
        ["python3", str(script), "--mode", "startup"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    package_root = Path(__file__).resolve().parents[1]

    if not (repo_root / ".git").exists():
        print(f"warning: {repo_root} does not look like a git repo; continuing anyway")

    install_runtime(repo_root, package_root, args.force)
    if args.seed == "templates":
        install_templates(repo_root, package_root, args.force)

    print(f"installed refactory runtime into {repo_root}")
    print(f"- startup wrapper: {repo_root / '.startup' / 'team-lead'}")
    print(f"- runtime root: {repo_root / '.refactor'}")

    preview = preview_startup(repo_root)
    if preview:
        print("\nstartup preview:\n")
        print(preview)
    else:
        print("\nstartup preview: (no triggers registered yet)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
