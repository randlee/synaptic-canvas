#!/usr/bin/env python3
"""Ask the installed claude / codex CLIs which models they serve; diff against agent_models.

Usage:
  python3 scripts/agent_model_discovery.py            # live data as JSON
  python3 scripts/agent_model_discovery.py --check    # exit 1 and print fix steps if stale

Sources (no API call, no tokens spent):
- codex: ``codex app-server --stdio`` JSON-RPC ``model/list`` (ids, default, efforts).
- claude: each alias is started with ``--print --output-format stream-json`` and killed
  as soon as the init event names the resolved model id; efforts come from
  ``claude --help``.

Works on Windows (npm ``.cmd`` shims are resolved with ``shutil.which``), macOS and
Linux. Every probe returns None when the CLI is missing or does not answer, so callers
can tell "no data" from "stale data". Used by ``tests/test_agent_model_drift.py``.
"""

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "packages" / "shared" / "scripts" / "agent_models.py"
sys.path.insert(0, str(CANONICAL.parent))

import agent_models  # noqa: E402

PROBE_SECONDS = 30
FAMILY = re.compile(r"^gpt-(\d+(?:\.\d+)*)-([a-z]+)$")
CLAUDE_EFFORT_HELP = re.compile(r"--effort\b[^(]*\(([^)]*)\)", re.DOTALL)


class LiveCodex(NamedTuple):
    version: str
    default: str
    models: Dict[str, agent_models.ModelSpec]


class LiveClaude(NamedTuple):
    version: str
    aliases: Dict[str, str]
    efforts: Tuple[str, ...]


# --- process helpers ---------------------------------------------------------


def _kill(proc: "subprocess.Popen[bytes]") -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":  # a .cmd shim's node child survives a plain kill
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    proc.kill()
    proc.wait()


class _Lines:
    """Read a child's stdout lines on a thread so every wait has a deadline."""

    def __init__(self, proc: "subprocess.Popen[bytes]") -> None:
        self._queue: "queue.Queue[Optional[bytes]]" = queue.Queue()
        thread = threading.Thread(target=self._pump, args=(proc,), daemon=True)
        thread.start()

    def _pump(self, proc: "subprocess.Popen[bytes]") -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            self._queue.put(line)
        self._queue.put(None)

    def json_events(self):
        """Yield decoded JSON objects; stop at EOF or when the probe deadline passes."""
        while True:
            try:
                line = self._queue.get(timeout=PROBE_SECONDS)
            except queue.Empty:
                return
            if line is None:
                return
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event


def _version(exe: str) -> str:
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=PROBE_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return out.stdout.strip() or "unknown"


# --- codex ---------------------------------------------------------------------


def codex_live() -> Optional[LiveCodex]:
    exe = shutil.which("codex")
    if exe is None:
        return None
    try:
        proc = subprocess.Popen([exe, "app-server", "--stdio"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    lines = _Lines(proc)
    events = lines.json_events()

    def send(message: Dict[str, Any]) -> None:
        assert proc.stdin is not None
        proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        proc.stdin.flush()

    def request(request_id: int, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        send({"id": request_id, "method": method, "params": params})
        for event in events:
            if event.get("id") == request_id and "method" not in event:
                return event.get("result") if "error" not in event else None
        return None

    try:
        if request(1, "initialize", {"clientInfo": {"name": "sc-model-drift", "version": "1"}}) is None:
            return None
        send({"method": "initialized", "params": {}})
        rows: List[Dict[str, Any]] = []
        cursor = None
        for request_id in range(2, 50):
            page = request(request_id, "model/list", {"limit": 100, "cursor": cursor, "includeHidden": False})
            if page is None:
                return None
            rows += page.get("data") or []
            cursor = page.get("nextCursor")
            if not cursor:
                break
    except OSError:
        return None
    finally:
        _kill(proc)
    models = {
        row["model"]: agent_models.ModelSpec(
            row["model"],
            tuple(e["reasoningEffort"] for e in row.get("supportedReasoningEfforts") or []),
            row.get("defaultReasoningEffort"),
        )
        for row in rows
        if row.get("model")
    }
    default = next((row["model"] for row in rows if row.get("isDefault")), "")
    if not models:
        return None
    return LiveCodex(_version(exe), default, models)


# --- claude --------------------------------------------------------------------


def _claude_resolve(exe: str, alias: str, cwd: str) -> Optional[str]:
    argv = [exe, "--print", "--output-format", "stream-json", "--verbose", "--model", alias,
            "--tools", "", "--strict-mcp-config", "--safe-mode", "--disable-slash-commands",
            "--no-session-persistence"]
    try:
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except OSError:
        return None
    try:
        assert proc.stdin is not None
        proc.stdin.write(b"x")
        proc.stdin.close()
        for event in _Lines(proc).json_events():
            if event.get("type") == "system" and event.get("subtype") == "init":
                model = event.get("model")
                return model if isinstance(model, str) and model else None
        return None
    except OSError:
        return None
    finally:
        _kill(proc)


def claude_live() -> Optional[LiveClaude]:
    exe = shutil.which("claude")
    if exe is None:
        return None
    try:
        help_text = subprocess.run([exe, "--help"], capture_output=True, text=True,
                                   timeout=PROBE_SECONDS).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = CLAUDE_EFFORT_HELP.search(help_text)
    efforts = tuple(e.strip() for e in match.group(1).split(",")) if match else ()
    with tempfile.TemporaryDirectory(prefix="sc-model-drift-") as cwd:
        resolved = {alias: _claude_resolve(exe, alias, cwd) for alias in agent_models.ALIASES["claude"]}
    aliases = {alias: model for alias, model in resolved.items() if model}
    if not aliases:
        return None
    return LiveClaude(_version(exe), aliases, efforts)


# --- drift ---------------------------------------------------------------------


def spec_literal(spec: agent_models.ModelSpec) -> str:
    """The exact line to paste into the MODELS["codex"] tuple of agent_models.py."""
    efforts = (
        f'_up_to("{spec.efforts[-1]}")'
        if spec.efforts and spec.efforts == agent_models.EFFORTS[: len(spec.efforts)]
        else repr(spec.efforts)
    )
    default = f'"{spec.default_effort}"' if spec.default_effort else "None"
    return f'ModelSpec("{spec.id}", {efforts}, {default}),'


def _family_latest(model_ids) -> Dict[str, str]:
    latest: Dict[str, Tuple[Tuple[int, ...], str]] = {}
    for model_id in model_ids:
        match = FAMILY.match(model_id)
        if not match:
            continue
        version = tuple(int(part) for part in match.group(1).split("."))
        family = match.group(2)
        if family not in latest or version > latest[family][0]:
            latest[family] = (version, model_id)
    return {family: model_id for family, (_, model_id) in latest.items()}


def codex_drift(live: LiveCodex) -> List[str]:
    """Edits to agent_models.py that make it match ``live``; empty when current."""
    table = agent_models.MODELS["codex"]
    aliases = agent_models.ALIASES["codex"]
    edits: List[str] = []
    for model_id, spec in live.models.items():
        if model_id not in table:
            edits.append(f'MODELS["codex"]: add  {spec_literal(spec)}')
        elif table[model_id] != spec:
            edits.append(f'MODELS["codex"]: replace  {spec_literal(table[model_id])}  with  {spec_literal(spec)}')
    for model_id in table:
        if model_id not in live.models:
            edits.append(f'MODELS["codex"]: remove  {spec_literal(table[model_id])}  (codex no longer lists it)')
    for family, newest in sorted(_family_latest(live.models).items()):
        current = aliases.get(family)
        if current is None:
            edits.append(f'ALIASES["codex"]: add  "{family}": "{newest}",')
        elif current != newest:
            edits.append(f'ALIASES["codex"]: change  "{family}": "{current}"  to  "{family}": "{newest}"')
    if live.default and aliases.get("codex") != live.default:
        edits.append(f'ALIASES["codex"]: change  "codex": "{aliases.get("codex")}"  to  "codex": "{live.default}"  '
                     "(the codex CLI default)")
    if live.default and agent_models.resolve_model("codex").id != live.default:
        family = next((a for a, t in aliases.items() if t == live.default and a != "codex"), None)
        if family is None:
            match = FAMILY.match(live.default)
            family = match.group(2) if match else live.default
        if agent_models.DEFAULT_ALIAS["codex"] != family:  # else the alias edit above covers it
            edits.append(f'DEFAULT_ALIAS: set  "codex": "{family}"  (resolves to {live.default}, the codex CLI default)')
    return edits


def claude_drift(live: LiveClaude) -> List[str]:
    table = agent_models.MODELS["claude"]
    aliases = agent_models.ALIASES["claude"]
    edits: List[str] = []
    for alias, model_id in sorted(live.aliases.items()):
        if aliases.get(alias) != model_id:
            edits.append(f'ALIASES["claude"]: change  "{alias}": "{aliases.get(alias)}"  to  "{alias}": "{model_id}"')
        if model_id not in table:
            edits.append(f'MODELS["claude"]: add "{model_id}" to the claude model id tuple')
    # Only a resolved alias that moved retires a model; an alias the CLI did not answer for
    # (not on this account, probe failed) says nothing.
    moved = {aliases[a] for a, m in live.aliases.items() if aliases.get(a) not in (None, m)}
    for model_id in sorted(moved - set(live.aliases.values())):
        edits.append(f'MODELS["claude"]: remove "{model_id}" (no alias resolves to it any more)')
    if live.efforts and live.efforts != agent_models.CLAUDE_EFFORTS:
        edits.append(f"CLAUDE_EFFORTS: set to {live.efforts!r} (claude --help --effort levels)")
    return edits


def consumers() -> List[Tuple[str, Path]]:
    """(package, copy path) for every package whose manifest syncs agent_models.py."""
    found = []
    for manifest in sorted((REPO / "packages").glob("*/manifest.yaml")):
        text = manifest.read_text(encoding="utf-8")
        match = re.search(r"source:\s*packages/shared/scripts/agent_models\.py\s*\n\s*target:\s*(\S+)", text)
        if match:
            found.append((manifest.parent.name, manifest.parent / match.group(1)))
    return found


def files_naming(model_ids) -> List[Path]:
    """Package docs/config (not CHANGELOGs, not agent_models copies) that name any of ``model_ids``."""
    hits = []
    pattern = re.compile("|".join(re.escape(m) for m in model_ids)) if model_ids else None
    if pattern is None:
        return hits
    for path in sorted((REPO / "packages").rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".json", ".yaml", ".yml", ".py"}:
            continue
        if path.name in {"CHANGELOG.md", "agent_models.py"} or "tests" in path.parts:
            continue
        try:
            if pattern.search(path.read_text(encoding="utf-8")):
                hits.append(path)
        except (OSError, UnicodeDecodeError):
            continue
    return hits


def fix_instructions(tool: str, version: str, edits: List[str], stale_ids) -> str:
    rel = lambda p: p.relative_to(REPO).as_posix()  # noqa: E731
    packages = consumers()
    lines = [
        f"The {tool} model table is stale: the installed {tool} CLI ({version}) reports different models.",
        "Every agent may fix this, whatever task it is on; the steps below are complete.",
        "",
        f"1. Edit {rel(CANONICAL)} (the only hand-edited copy):",
    ]
    lines += [f"     - {edit}" for edit in edits]
    lines += [
        "2. Copy it into every package:  python3 scripts/sync-shared-scripts.py",
        "   (rewrites " + ", ".join(rel(path) for _, path in packages) + ")",
    ]
    docs = files_naming(stale_ids)
    if docs:
        lines.append("3. Replace the old model ids in these docs/config files:")
        lines += [f"     - {rel(path)}" for path in docs]
    else:
        lines.append("3. No package doc names an outdated model id.")
    lines += [
        "4. Update any model tables / defaults in each package's README.md and SKILL.md, add a CHANGELOG",
        "   entry, and bump the minor version of: " + ", ".join(name for name, _ in packages),
        "   (python3 scripts/set-package-version.py <package> <version>).",
        "5. Re-run:  python3 -m pytest tests/test_agent_model_drift.py tests/scripts -q",
        f"   Live data:  python3 scripts/agent_model_discovery.py",
    ]
    return "\n".join(lines)


def stale_ids(tool: str, edits: List[str]) -> List[str]:
    """Model ids the table currently uses that the edits replace or remove."""
    quoted = re.compile(r'"(gpt-[^"]+|claude-[^"]+)"')
    old = set()
    for edit in edits:
        action = edit.split(":", 1)[1].split()[0] if ":" in edit else ""
        if action in {"change", "replace", "remove"}:
            head = edit.split("  to  ")[0].split("  with  ")[0]
            old.update(quoted.findall(head))
    return sorted(old)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Exit 1 with fix steps if agent_models.py is stale")
    args = parser.parse_args(argv)
    codex, claude = codex_live(), claude_live()
    if not args.check:
        print(json.dumps({
            "codex": None if codex is None else {
                "version": codex.version, "default": codex.default,
                "models": {k: v._asdict() for k, v in codex.models.items()},
            },
            "claude": None if claude is None else claude._asdict(),
        }, indent=2))
        return 0
    status = 0
    for tool, live, drift in (("codex", codex, codex_drift), ("claude", claude, claude_drift)):
        if live is None:
            print(f"{tool}: not installed or no answer; skipped")
            continue
        edits = drift(live)
        if edits:
            status = 1
            print(fix_instructions(tool, live.version, edits, stale_ids(tool, edits)), end="\n\n")
        else:
            print(f"{tool}: agent_models.py is current ({live.version})")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
