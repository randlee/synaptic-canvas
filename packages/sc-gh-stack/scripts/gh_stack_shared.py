#!/usr/bin/env python3
"""Helpers shared by the sc-gh-stack scripts (stdlib only).

Installed next to ``gh_stack_view.py`` and ``gh_stack_chain_check.py`` under
``.claude/scripts/``.  Everything here is read-only: subprocess wrappers and
the git lookups both scripts need.  Never runs a ``gh stack`` write command.
"""
from __future__ import annotations

import subprocess
import sys
import json
import argparse
import re
from typing import Callable

GIT_TIMEOUT = 60
GH_TIMEOUT = 120


class ReportArgumentParser(argparse.ArgumentParser):
    """Keep machine-output errors machine-readable, including parse failures."""

    def parse_args(self, args=None, namespace=None):
        values = sys.argv[1:] if args is None else list(args)
        self.json_errors = any(value in ("--json", "--compact-json") for value in values)
        return super().parse_args(values, namespace)

    def error(self, message):
        if getattr(self, "json_errors", False):
            print(json.dumps({"schema_version": 1, "success": False,
                              "error": {"code": "INPUT.INVALID_ARGUMENT", "message": message}}))
        super().error(message)


def compact_report(payload, limit=10):
    """Bound agent-facing output without changing acquisition or full JSON.

    This is a presentation projection, not complete composition evidence. Counts
    and explicit truncation prevent a displayed tail from masquerading as top.
    """
    result = {key: payload[key] for key in (
        "schema_version", "success", "snapshot_id", "coherent", "linkable",
        "hidden", "git_observation", "metrics", "unknown_count", "link_command") if key in payload}
    result["output_mode"] = "compact"
    warnings = payload.get("warnings", [])
    result.update(warnings=warnings[:limit], warning_count=len(warnings))
    git = payload.get('git_observation')
    if isinstance(git, dict):
        projected = {key: git[key] for key in ('fresh', 'source', 'observed_at', 'error', 'requested_fresh') if key in git}
        refs = git.get('refs', {})
        names = sorted(refs, key=lambda name: (not bool(refs[name].get('error') or refs[name].get('fresh') is False), name))
        required = git.get('required_refs', [])
        projected.update(refs={name: refs[name] for name in names[:limit]},
                         requested_ref_count=len(refs), shown_ref_count=min(len(refs), limit),
                         required_ref_count=len(required), required_refs=required[:limit],
                         truncated=len(refs) > limit or len(required) > limit)
        result['git_observation'] = projected
    if len(payload.get('rows', [])) > limit and payload.get('link_command'):
        result.update(link_command=None, link_command_omitted=True)

    def project(entry):
        rows = entry.get("rows", [])
        active = [row for row in rows if not row.get("merged")]
        def priority(row):
            bad = (row.get("local_merge_clean") is False or row.get("pushed") is False
                   or row.get("origin_ok") is False or row.get("pr_head_ok") is False
                   or row.get("needs_rebase") or row.get("mergeable") == "CONFLICTING"
                   or row.get("ci") in ("ERROR", "FAILURE"))
            unknown = row.get("local_merge_clean") is None or row.get("hosted_stale") or row.get("unknown")
            return (not bad, not unknown, not row.get("changed", False), row["layer"])
        shown = sorted(rows, key=priority)[:limit]
        part = {key: entry[key] for key in (
            "trunk", "trunk_origin", "id", "number", "structure_observation",
            "coherent", "linkable", "landing") if key in entry}
        local = entry.get("local_mergeability", {})
        part.update(total_layers=len(rows), shown_layers=len(shown), truncated=len(shown) < len(rows),
                    rows=shown, local_mergeability={
                        "clean": local.get("clean"), "combined": local.get("combined"),
                        "conflict_count": sum(row.get("local_merge_clean") is False for row in active),
                        "unknown_count": sum(row.get("local_merge_clean") is None for row in active)},
                    problems=entry.get("problems", [])[:limit], problem_count=len(entry.get("problems", [])),
                    notes=entry.get("notes", [])[:limit], note_count=len(entry.get("notes", [])))
        return part

    if "stacks" in payload:
        stacks = payload["stacks"]
        result.update(total_stacks=len(stacks), shown_stacks=min(len(stacks), limit),
                      truncated=len(stacks) > limit or any(len(stack.get("rows", [])) > limit for stack in stacks),
                      stacks=[project(stack) for stack in stacks[:limit]])
    else:
        result.update(project(payload))
    def bound(value):
        if isinstance(value, str) and len(value) > 1024:
            return value[:1024] + '… [truncated; --json for full]'
        if isinstance(value, list):
            return [bound(item) for item in value]
        if isinstance(value, dict):
            return {key: bound(item) for key, item in value.items()}
        return value
    bounded = bound(result)
    bounded['text_truncated'] = bounded != result
    return bounded


class ToolError(Exception):
    """A required external command is missing or failed; message is actionable."""

    def __init__(self, message: str, code: str = "TOOL.ERROR", details=None):
        super().__init__(message)
        self.code = code
        self.details = details


def parse_selector(value: str, *, kind: str = 'stack') -> tuple[str, int | str]:
    """Disambiguate numeric identifiers from literal branches without API reads.

    Bare ASCII numbers retain their historical numeric meaning. Explicit
    ``branch:123`` names a numeric branch; ``id:...`` explicitly selects a
    stack ID. Bare nonnumeric stack IDs remain supported for compatibility.
    Git branch validation remains the caller's responsibility.
    """
    if kind not in ('stack', 'layer'):
        raise ValueError('selector kind must be stack or layer')
    def invalid():
        raise ToolError('invalid %s selector %r; use a positive ASCII number or branch:NAME%s' %
                        (kind, value, ' / id:ID' if kind == 'stack' else ''), 'INPUT.INVALID_SELECTOR')
    def number(text):
        if not re.fullmatch(r'[0-9]+', text):
            invalid()
        try:
            parsed = int(text)
        except ValueError:
            invalid()
        if parsed <= 0:
            invalid()
        return 'number', parsed
    if not isinstance(value, str) or not value:
        invalid()
    if ':' in value:
        prefix, text = value.split(':', 1)
        if not text:
            invalid()
        if prefix == 'branch':
            return 'branch', text
        if prefix == 'id' and kind == 'stack':
            return 'id', text
        if prefix != ('number' if kind == 'stack' else 'pr'):
            invalid()
        return number(text)
    if re.fullmatch(r'[0-9]+', value):
        return number(value)
    if value.isdigit():
        invalid()
    return ('auto' if kind == 'stack' else 'branch'), value


def run(cmd: list[str], *, check: bool = True, cwd: str | None = None, timeout: float | None = None,
        input: str | None = None) -> subprocess.CompletedProcess[str]:
    timeout = timeout if timeout is not None else (GH_TIMEOUT if cmd and cmd[0] == "gh" else GIT_TIMEOUT)
    try:
        kwargs = {'input': input} if input is not None else {}
        proc = subprocess.run(cmd, text=True, capture_output=True, cwd=cwd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{' '.join(cmd[:3])} timed out after {timeout}s; check network, `gh auth status`, or a hung prompt") from exc
    except FileNotFoundError as exc:
        missing = cmd[0] if exc.filename in (None, cmd[0]) else f"directory {exc.filename}"
        raise ToolError(f"cannot run {' '.join(cmd[:3])}: {missing} not found "
                        f"(install gh + gh-stack extension and git; prune stale worktrees with `git worktree prune`)") from exc
    except OSError as exc:
        raise ToolError(f"cannot run {' '.join(cmd[:3])}: {exc}") from exc
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        raise ToolError(f"{' '.join(cmd[:3])} failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
                        + hint_for(" ".join(detail)))
    return proc


def hint_for(text: str) -> str:
    """Append the next action for the failure signatures gh and git actually produce."""
    low = text.lower()
    if "rate limit" in low or "secondary" in low or "abuse" in low:
        return "; GitHub rate limit: honor Retry-After/reset and shared cooldown; --no-pr avoids API calls"
    if "auth" in low or "401" in low or "token" in low or "not logged" in low:
        return "; run `gh auth status` / `gh auth login`"
    if "could not resolve host" in low or "network" in low or "timed out" in low or "connection" in low:
        return "; network problem: retry, or use --no-fetch/--no-pr for a local-only view"
    if "not a git repository" in low:
        return "; run from inside the repository or one of its worktrees"
    if "extension" in low and "not found" in low:
        return "; `gh extension install github/gh-stack`"
    return ""


def short(sha: str | None) -> str:
    return (sha or "")[:9] or "-"


def origin_sha(ref: str, remote: str = "origin") -> str | None:
    """None when the branch is not on origin (unpushed or deleted after merge)."""
    proc = run(["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{ref}"], check=False)
    return proc.stdout.strip() or None


def is_ancestor(older: str, newer: str) -> bool:
    return run(["git", "merge-base", "--is-ancestor", older, newer], check=False).returncode == 0


def utf8_stdout() -> None:
    """Emoji in the tables must not raise on a non-UTF-8 console (Windows legacy code pages)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def guarded(tag: str, body: Callable[[], int], *, json_errors: bool = False) -> int:
    """Run ``body``; every failure is one ``<tag>: ...`` line on stderr and exit 2, never a traceback."""
    utf8_stdout()
    try:
        return body()
    except ToolError as exc:
        if json_errors:
            error = {"code": exc.code, "message": str(exc)}
            if exc.details is not None:
                error["details"] = exc.details
            print(json.dumps({"schema_version": 1, "success": False,
                              "error": error}))
        sys.stderr.write(f"{tag}: {exc}\n")
        return 2
    except KeyboardInterrupt:
        if json_errors:
            print(json.dumps({"schema_version": 1, "success": False,
                              "error": {"code": "TOOL.INTERRUPTED", "message": "interrupted"}}))
        sys.stderr.write(f"{tag}: interrupted\n")
        return 2
    except Exception as exc:  # noqa: BLE001 - the contract is "never a traceback"
        if json_errors:
            print(json.dumps({"schema_version": 1, "success": False,
                              "error": {"code": "INTERNAL.ERROR", "message": str(exc)}}))
        sys.stderr.write(f"{tag}: unexpected {type(exc).__name__}: {exc} (report this with the command you ran)\n")
        return 2
