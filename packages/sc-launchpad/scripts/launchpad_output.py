#!/usr/bin/env python3
"""Parse claude stream-json / codex JSONL, verify isolation, and classify failures."""

import json
import re
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Tuple

from launchpad_commands import isolation_flags
from launchpad_models import LaunchFailure, LaunchpadInput
from launchpad_process import ProcessOutcome

TAIL_CHARS = 4000

AUTH_PATTERN = re.compile(
    r"invalid api key|invalid x-api-key|not logged in|please run /login|codex login|"
    r"unauthori[sz]ed|authentication (?:failed|error|required)|\b401\b|"
    r"oauth token (?:has )?expired|login required",
    re.IGNORECASE,
)
RESUME_NOT_FOUND_PATTERN = re.compile(
    r"no conversation found|no rollout found|session \S* ?not found|thread \S* ?not found",
    re.IGNORECASE,
)
UNSUPPORTED_FLAG_PATTERN = re.compile(
    r"unknown option|unknown feature flag|unexpected argument|unrecognized (?:option|argument)",
    re.IGNORECASE,
)
# codex `Unknown feature flag: <name>` / `unexpected argument '<flag>'`, claude `unknown option '<flag>'`.
REJECTED_FLAG_PATTERN = re.compile(
    r"(?:unknown feature flag:?\s*|unknown option\s*|unexpected argument\s*|"
    r"unrecognized (?:option|argument):?\s*)['\"`]?([^'\"`\s]+)",
    re.IGNORECASE,
)
# Codex items a tool-less turn can legitimately produce; anything else is tool activity.
CODEX_TOOLLESS_ITEMS = {"agent_message", "reasoning", "error", "todo_list"}


class ParsedOutput(NamedTuple):
    session_id: Optional[str]
    result_text: Optional[str]
    reported_error: Optional[str]
    auth_hint: bool
    warnings: List[str]
    # Evidence that tools were available or used, e.g. "tool_use:Bash".
    tool_activity: List[str]
    # claude only: the init event listed no tools and no MCP servers.
    toolless_init: bool


def tail(text: Optional[str]) -> str:
    return (text or "")[-TAIL_CHARS:]


def _events(stdout: str, tool: str, strict: bool) -> Iterator[Dict[str, Any]]:
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            if not strict:
                continue
            raise LaunchFailure(
                "CLI.OUTPUT_UNPARSEABLE",
                f"{tool} produced a non-JSON output line {line_no}: {exc}",
                "Check that extra_args do not override the structured output mode.",
                details={"line": line[:1000], "line_number": line_no},
            )
        if isinstance(event, dict):
            yield event


def _string(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def parse_claude(stdout: str, strict: bool = True) -> ParsedOutput:
    """``claude --print --output-format stream-json --verbose``: init, messages, result."""
    session_id = result_text = reported_error = None
    auth_hint = toolless_init = saw_result = False
    activity: List[str] = []
    for event in _events(stdout, "claude", strict):
        etype = event.get("type")
        session_id = _string(event.get("session_id")) or session_id
        if etype == "system" and event.get("subtype") == "init":
            tools, servers = event.get("tools"), event.get("mcp_servers")
            toolless_init = tools == [] and servers == []
            activity += [f"init.tools:{name}" for name in tools or []]
            activity += [f"init.mcp_servers:{(s or {}).get('name', s)}" for s in servers or []]
        elif etype == "assistant":
            content = (event.get("message") or {}).get("content") or []
            activity += [
                f"tool_use:{block.get('name')}"
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]
        elif etype == "result":
            saw_result = True
            result_text = event.get("result") if isinstance(event.get("result"), str) else None
            if event.get("is_error") is True:
                reported_error = result_text or str(event.get("subtype") or "claude reported is_error=true")
                auth_hint = event.get("api_error_status") in (401, 403)
    if strict and not saw_result and session_id is None:
        raise LaunchFailure(
            "CLI.OUTPUT_UNPARSEABLE",
            "claude stream-json output had no init or result event",
            "Check that the installed claude CLI supports --output-format stream-json --verbose.",
        )
    return ParsedOutput(session_id, result_text, reported_error, auth_hint, [], activity, toolless_init)


def parse_codex(stdout: str, strict: bool = True) -> ParsedOutput:
    """``codex exec --json``: thread.started, item.*, turn.completed / turn.failed."""
    session_id = result_text = turn_failed = None
    turn_completed = False
    error_events: List[str] = []
    warnings: List[str] = []
    activity: List[str] = []
    count = 0
    for event in _events(stdout, "codex", strict):
        count += 1
        etype = event.get("type")
        if etype == "thread.started":
            session_id = _string(event.get("thread_id")) or session_id
        elif etype in ("item.started", "item.updated", "item.completed"):
            item = event.get("item") or {}
            itype = item.get("type")
            if itype not in CODEX_TOOLLESS_ITEMS and f"item:{itype}" not in activity:
                activity.append(f"item:{itype}")
            if etype == "item.completed" and itype == "agent_message" and isinstance(item.get("text"), str):
                result_text = item["text"]
            elif etype == "item.completed" and itype == "error" and item.get("message"):
                warnings.append(str(item["message"]))
        elif etype == "turn.completed":
            turn_completed = True
        elif etype == "turn.failed":
            turn_failed = str((event.get("error") or {}).get("message") or "codex reported turn.failed")
        elif etype == "error":
            error_events.append(str(event.get("message") or "codex reported an error event"))
    if strict and count == 0:
        raise LaunchFailure(
            "CLI.OUTPUT_UNPARSEABLE",
            "codex exec --json produced no JSON events",
            "Inspect stderr; the installed codex CLI may not support --json.",
        )
    reported_error = turn_failed
    if turn_completed:
        warnings += error_events  # transient errors (e.g. reconnects) before a completed turn
    elif reported_error is None and error_events:
        reported_error = error_events[-1]
    return ParsedOutput(session_id, result_text, reported_error, False, warnings, activity, False)


PARSERS = {"claude": parse_claude, "codex": parse_codex}


def isolation_violation(payload: LaunchpadInput, parsed: ParsedOutput, completed: bool) -> Optional[LaunchFailure]:
    """Under isolation.tools='none', require positive evidence that no tool was available or used."""
    if not payload.no_tools:
        return None
    missing_proof = payload.tool == "claude" and completed and not parsed.toolless_init
    if not parsed.tool_activity and not missing_proof:
        return None
    return LaunchFailure(
        "ISOLATION.VIOLATED",
        f"{payload.tool} ran with tools despite isolation.tools='none'",
        f"Do not trust this turn's output. Compare `{payload.tool} --version` with the README "
        "\"Isolation guarantees\" and update sc-launchpad's isolation flags.",
        recoverable=False,
        details={
            "tool_activity": parsed.tool_activity,
            "toolless_init_seen": parsed.toolless_init if payload.tool == "claude" else None,
        },
    )


def _unsupported_flag(payload: LaunchpadInput, stderr: str, details: Dict[str, Any]) -> LaunchFailure:
    match = REJECTED_FLAG_PATTERN.search(stderr)
    rejected = match.group(1) if match else None
    is_isolation = rejected is not None and rejected in isolation_flags(payload)
    details = dict(details, rejected=rejected, rejected_is_isolation_flag=is_isolation)
    name = f" `{rejected}`" if rejected else ""
    if is_isolation:
        action = (
            f"The installed {payload.tool} CLI does not accept isolation flag/feature{name}. "
            f"Compare `{payload.tool} --version` with the README \"Isolation guarantees\"; "
            "upgrade the CLI or update sc-launchpad's isolation flags. Isolation is never "
            "weakened automatically."
        )
    else:
        action = (
            f"Remove or fix{name or ' the offending flag'} in extra_args, or compare the "
            f"installed {payload.tool} CLI version with the README."
        )
    return LaunchFailure(
        "CLI.UNSUPPORTED_FLAG",
        f"{payload.tool} rejected command-line flag/feature{name or ' (unknown name)'}",
        action,
        details=details,
    )


def classify(payload: LaunchpadInput, outcome: ProcessOutcome) -> Tuple[ParsedOutput, List[str]]:
    """Return (parsed output, warnings) for a successful structured turn, else raise ``LaunchFailure``.

    Order: isolation violation, timeout, resume-not-found, unsupported flag,
    auth, non-zero exit, reported error, missing session id / result.
    """
    tool = payload.tool
    details: Dict[str, Any] = {
        "exit_code": outcome.exit_code,
        "stderr_tail": tail(outcome.stderr),
        "stdout_tail": tail(outcome.stdout),
    }
    completed = outcome.exit_code == 0 and not outcome.timed_out
    try:
        parsed: Optional[ParsedOutput] = PARSERS[tool](outcome.stdout, strict=completed)
        parse_error = None
    except LaunchFailure as exc:
        parsed, parse_error = None, exc
    if parsed is not None:
        if parsed.session_id:
            details["session_id"] = parsed.session_id
        violation = isolation_violation(payload, parsed, completed and parsed.reported_error is None)
        if violation is not None:
            violation.details.update(details)
            raise violation
    reported = parsed.reported_error if parsed else None
    if reported:
        details["reported_error"] = reported

    if outcome.timed_out:
        raise LaunchFailure(
            "CLI.TIMEOUT",
            f"{tool} did not finish within {payload.timeout_seconds}s and was killed",
            "Increase timeout_seconds or shorten the prompt.",
            details=dict(details, timeout_seconds=payload.timeout_seconds),
        )
    if outcome.exit_code != 0 or reported:
        signal_text = "\n".join(text for text in (outcome.stderr, reported) if text)
        if payload.resume_session_id and RESUME_NOT_FOUND_PATTERN.search(signal_text):
            raise LaunchFailure(
                "CLI.RESUME_SESSION_NOT_FOUND",
                f"{tool} could not find session {payload.resume_session_id}",
                "Pass a session_id from a previous launch together with that launch's data.cwd.",
                details=dict(details, resume_session_id=payload.resume_session_id),
            )
        if outcome.exit_code != 0 and UNSUPPORTED_FLAG_PATTERN.search(outcome.stderr):
            raise _unsupported_flag(payload, outcome.stderr, details)
        if (parsed is not None and parsed.auth_hint) or AUTH_PATTERN.search(signal_text):
            raise LaunchFailure(
                "CLI.AUTH_FAILED",
                f"{tool} reported an authentication failure",
                f"Re-authenticate the {tool} CLI (log in again) and retry.",
                details=details,
            )
        if outcome.exit_code != 0:
            raise LaunchFailure(
                "CLI.NON_ZERO_EXIT",
                f"{tool} exited with code {outcome.exit_code}",
                "Inspect error.details stderr_tail/stdout_tail and retry with an adjusted prompt or args.",
                details=details,
            )
        raise LaunchFailure(
            "CLI.REPORTED_ERROR",
            f"{tool} exited 0 but reported an error: {reported}",
            "Inspect error.details.reported_error and retry.",
            details=details,
        )
    if parse_error is not None:
        parse_error.details.update(details)
        raise parse_error
    assert parsed is not None
    if not parsed.session_id:
        raise LaunchFailure(
            "CLI.SESSION_ID_MISSING",
            f"{tool} structured output did not include a session id",
            "Upgrade or check the CLI; the session id field/event may have been renamed.",
            details=details,
        )
    if parsed.result_text is None:
        raise LaunchFailure(
            "CLI.RESULT_MISSING",
            f"{tool} structured output did not include a final assistant message",
            "Inspect error.details.stdout_tail; the turn may have ended without a reply.",
            details=details,
        )
    warnings = list(parsed.warnings)
    if payload.resume_session_id and parsed.session_id != payload.resume_session_id:
        warnings.append(f"resumed session {payload.resume_session_id} reported session id {parsed.session_id}")
    return parsed, warnings
