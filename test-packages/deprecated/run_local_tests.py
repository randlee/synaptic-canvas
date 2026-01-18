#!/usr/bin/env python3
"""
Run package-mapped tests locally with optional integration coverage.
"""
from __future__ import annotations

import argparse
import json
import re
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run package-mapped tests")
    ap.add_argument("--package", help="Package name (e.g., sc-startup)")
    ap.add_argument("--integration", action="store_true", help="Include integration tests (token usage)")
    ap.add_argument("--k", dest="keyword", help="pytest -k expression")
    ap.add_argument("--report", help="Write combined pytest output to a file")
    ap.add_argument("--report-md", help="Write a markdown report to a file")
    ap.add_argument("--report-html", help="Write an HTML report to a file")
    ap.add_argument("--report-json", help="Write a JSON report to a file")
    ap.add_argument("--test-repo", help="Path to instrumented test repo")
    ap.add_argument("--test-name", help="Human-friendly test name for reports")
    ap.add_argument("--test-description", help="Short purpose/intent for reports")
    ap.add_argument("--agent-name", help="Agent/command under test (kebab-case)")
    ap.add_argument("--test-summary", help="Human-readable summary of what the test validates")
    ap.add_argument("--test-steps", help="Semicolon-delimited steps for the report")
    ap.add_argument("--claude-command", help="Exact CLI command used to invoke Claude")
    ap.add_argument("--test-script", help="Test script identifier (e.g., file::test_name)")
    ap.add_argument("--expect-tool", action="append", help="Expected tool command (Label::regex)")
    ap.add_argument("--expect-read", action="append", help="Expected Read file path (Label::regex)")
    ap.add_argument("--expect-event", action="append", help="Expected hook event (Label::EventName)")
    ap.add_argument("--expect-prompt", action="append", help="Expected prompt content (Label::regex)")
    ap.add_argument("--expect-output", action="append", help="Expected Claude output content (Label::regex)")
    args, extra = ap.parse_known_args()

    paths = []
    if args.package:
        base = REPO_ROOT / "test-packages" / args.package
        agents = base / "agents"
        if agents.exists():
            paths.append(str(agents))
        if args.integration:
            integration = base / "integration"
            if integration.exists():
                paths.append(str(integration))
    else:
        paths.append(str(REPO_ROOT / "test-packages"))

    if not paths:
        raise SystemExit("No tests found for the requested package")

    cmd = ["pytest", "-q"]
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    if args.integration:
        cmd.extend(["-m", "integration"])
    cmd.extend(paths)
    cmd.extend(extra)

    env = None
    trace_summary = ""
    trace_entries: list[dict[str, str | bool]] = []
    trace_prompt: str | None = None
    trace_events: list[dict[str, str]] = []
    expectations: list[dict[str, object]] = []
    claude_output: str | None = None
    if args.test_repo:
        env = dict(**os.environ, **{"SC_TEST_REPO": args.test_repo})

    if args.report or args.report_md or args.report_html or args.report_json:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        output = result.stdout + result.stderr
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(output, encoding="utf-8")
        if args.report_md or args.report_html or args.report_json:
            trace_path = Path(args.test_repo) / "reports" / "trace.jsonl" if args.test_repo else None
            output_path = Path(args.test_repo) / "reports" / "claude-output.txt" if args.test_repo else None
            if trace_path and trace_path.exists():
                lines = trace_path.read_text(encoding="utf-8").splitlines()
                lines = _select_session_lines(lines, args.claude_command)
                trace_prompt = _extract_prompt(lines)
                trace_events = _extract_events(lines)
                trace_entries = _parse_trace_entries(lines[-400:])
                trace_summary = _summarize_trace_entries(trace_entries)
            expectations = _evaluate_expectations(
                trace_entries,
                trace_events,
                trace_prompt,
                args.expect_tool or [],
                args.expect_read or [],
                args.expect_event or [],
                args.expect_prompt or [],
                args.expect_output or [],
                claude_output or "",
            )
            if output_path and output_path.exists():
                claude_output = output_path.read_text(encoding="utf-8").strip()
        if args.report_md:
            report_path = Path(args.report_md)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            title = report_path.stem.replace("_", " ")
            trace_section = ""
            if trace_summary:
                trace_section = f"\n## Hook trace (formatted)\n\n{trace_summary}\n"
            report_path.write_text(
                f"# {title} {timestamp}\n\n"
                f"## pytest output\n\n"
                "```text\n"
                f"{output.rstrip()}\n"
                "```\n"
                f"{trace_section}",
                encoding="utf-8",
            )
        if args.report_html:
            report_path = Path(args.report_html)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            title = report_path.stem.replace("_", " ")
            payload = _extract_prompt_payload(trace_prompt)
            trace_section = ""
            if trace_entries:
                trace_section = _render_trace_html(trace_entries)
            selection = _render_selection_html(args)
            report_path.write_text(
                _render_html_report(
                    title,
                    timestamp,
                    output.rstrip(),
                    selection,
                    trace_prompt,
                    payload,
                    trace_section,
                    result.returncode == 0,
                    args.test_name,
                    args.agent_name,
                    args.test_description,
                    args.test_summary,
                    args.test_steps,
                    args.claude_command,
                    args.test_script,
                    trace_prompt,
                    trace_events,
                    expectations,
                    claude_output,
                ),
                encoding="utf-8",
            )
        if args.report_json:
            report_path = Path(args.report_json)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report = {
                "title": args.test_name or report_path.stem,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "package": args.package,
                "test_name": args.test_name,
                "test_description": args.test_description,
                "agent_name": args.agent_name,
                "test_summary": args.test_summary,
                "test_steps": args.test_steps,
                "claude_command": args.claude_command,
                "test_script": args.test_script,
                "integration": bool(args.integration),
                "test_repo": args.test_repo,
                "pytest_output": output.rstrip(),
                "prompt": trace_prompt,
                "prompt_payload": _extract_prompt_payload(trace_prompt),
                "events": trace_events,
                "expectations": expectations,
                "claude_output": claude_output,
                "trace": trace_entries,
            }
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode
    return subprocess.call(cmd, env=env)


def _summarize_trace_entries(entries: list[dict[str, str | bool]]) -> str:
    if not entries:
        return "_no trace entries_"
    sections = []
    for idx, entry in enumerate(entries, start=1):
        fence = "error" if entry["is_error"] else "response"
        sections.append(
            f"### Tool Use {idx} — {entry['tool_name']}\n\n"
            f"**{entry['input_label']}:** `{entry['input_value']}`\n\n"
            f"```{fence}\n{entry['response_text']}\n```\n"
        )
    return "\n".join(sections)


def _parse_trace_entries(lines: list[str]) -> list[dict[str, str | bool]]:
    ordered_ids: list[str] = []
    tool_uses: dict[str, dict[str, object]] = {}

    for line in lines:
        try:
            record = json.loads(line)
        except Exception:
            continue
        event = record.get("event") or ""
        if event not in {"PreToolUse", "PostToolUse"}:
            continue
        stdin = record.get("stdin") or ""
        try:
            payload = json.loads(stdin)
        except Exception:
            payload = {}
        tool_use_id = payload.get("tool_use_id") or f"anon-{len(ordered_ids)}"
        if tool_use_id not in tool_uses:
            tool_uses[tool_use_id] = {"event": event}
            ordered_ids.append(tool_use_id)
        tool_uses[tool_use_id]["tool_name"] = payload.get("tool_name") or tool_uses[tool_use_id].get("tool_name")
        tool_uses[tool_use_id]["tool_input"] = payload.get("tool_input") or tool_uses[tool_use_id].get("tool_input")
        if event == "PostToolUse":
            tool_uses[tool_use_id]["tool_response"] = payload.get("tool_response")

    entries: list[dict[str, str | bool]] = []
    for tool_use_id in ordered_ids:
        entry = tool_uses.get(tool_use_id, {})
        tool_name = entry.get("tool_name") or "tool"
        tool_input = entry.get("tool_input") or {}
        tool_response = entry.get("tool_response")

        input_label = "Input"
        input_value = ""
        if isinstance(tool_input, dict):
            if "command" in tool_input:
                input_label = "Command"
                input_value = str(tool_input.get("command") or "")
            elif "file_path" in tool_input:
                input_label = "File Path"
                input_value = str(tool_input.get("file_path") or "")
            elif "relative_path" in tool_input:
                input_label = "Path"
                input_value = str(tool_input.get("relative_path") or "")
            else:
                input_value = json.dumps(tool_input, ensure_ascii=True)
        else:
            input_value = str(tool_input)

        response_text = ""
        is_error = False
        if isinstance(tool_response, dict):
            stdout = str(tool_response.get("stdout") or "")
            stderr = str(tool_response.get("stderr") or "")
            interrupted = bool(tool_response.get("interrupted"))
            is_error = bool(stderr.strip()) or interrupted
            pretty_stdout = _maybe_pretty_json(stdout)
            if pretty_stdout:
                stdout = pretty_stdout
            if stdout and stderr:
                response_text = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
            elif stderr:
                response_text = stderr
            else:
                response_text = stdout
        elif isinstance(tool_response, str):
            try:
                parsed = json.loads(tool_response)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                stdout = str(parsed.get("stdout") or "")
                stderr = str(parsed.get("stderr") or "")
                interrupted = bool(parsed.get("interrupted"))
                is_error = bool(stderr.strip()) or interrupted
                pretty_stdout = _maybe_pretty_json(stdout)
                if pretty_stdout:
                    stdout = pretty_stdout
                if stdout and stderr:
                    response_text = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
                elif stderr:
                    response_text = stderr
                else:
                    response_text = stdout
            else:
                response_text = tool_response
                is_error = "Error:" in tool_response or "error" in tool_response.lower()
        elif tool_response is None:
            response_text = "_no response_"
        else:
            response_text = json.dumps(tool_response, indent=2, ensure_ascii=True)

        response_summary = _summarize_response(tool_name, input_label, input_value, response_text)
        entries.append(
            {
                "tool_name": str(tool_name),
                "input_label": input_label,
                "input_value": input_value,
                "response_text": _truncate_response(response_text),
                "is_error": is_error,
                "response_summary": response_summary,
            }
        )
    return entries


def _select_session_lines(lines: list[str], claude_command: str | None) -> list[str]:
    sessions: dict[str, list[str]] = {}
    prompts: dict[str, str] = {}
    for line in lines:
        try:
            record = json.loads(line)
        except Exception:
            continue
        stdin = record.get("stdin") or ""
        try:
            payload = json.loads(stdin)
        except Exception:
            payload = {}
        session_id = payload.get("session_id")
        if not session_id:
            continue
        sessions.setdefault(session_id, []).append(line)
        if record.get("event") == "UserPromptSubmit" and payload.get("prompt"):
            prompts[session_id] = payload.get("prompt")

    if not sessions:
        return lines

    desired_prompt = _extract_prompt_from_claude_command(claude_command) if claude_command else None
    if desired_prompt:
        matching = [sid for sid, prompt in prompts.items() if prompt == desired_prompt]
        if matching:
            return sessions[matching[-1]]

    latest_session = list(sessions.keys())[-1]
    return sessions[latest_session]


def _truncate_response(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (truncated)"


def _maybe_pretty_json(text: str) -> str | None:
    stripped = text.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    try:
        parsed = json.loads(stripped)
    except Exception:
        return None
    return json.dumps(parsed, indent=2, ensure_ascii=True)


def _summarize_response(tool_name: str, input_label: str, input_value: str, response_text: str) -> str:
    if input_label == "Command":
        command = input_value.strip().splitlines()[0]
        if "sc_checklist_status.py" in command:
            summary = _summarize_checklist_response(response_text)
            return summary or f"{tool_name} sc-checklist-status"
        if "sc_startup_init.py" in command:
            return f"{tool_name} sc-startup-init"
        if "sc-startup" in command:
            return f"{tool_name} sc-startup"
    return f"{tool_name} {input_label.lower()}"


def _summarize_checklist_response(response_text: str) -> str | None:
    try:
        data = json.loads(response_text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("success"):
        return "sc-checklist-status (failed)"
    details = data.get("data", {})
    missing = details.get("missing") if isinstance(details, dict) else None
    count = len(missing) if isinstance(missing, list) else 0
    return f"sc-checklist-status (missing: {count})"


def _render_html_report(
    title: str,
    timestamp: str,
    output: str,
    selection: str,
    prompt: str | None,
    prompt_payload: str | None,
    trace_section: str,
    passed: bool,
    test_name: str | None,
    agent_name: str | None,
    test_description: str | None,
    test_summary: str | None,
    test_steps: str | None,
    claude_command: str | None,
    test_script: str | None,
    trace_prompt: str | None,
    trace_events: list[dict[str, str]],
    expectations: list[dict[str, object]],
    claude_output: str | None,
) -> str:
    css = """
body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
h1 { margin-bottom: 0; }
h2 { margin-top: 28px; }
pre { background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; }
.error { color: #c92a2a; }
.cmd { font-weight: 700; font-size: 1.05rem; }
details { border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 12px; margin: 8px 0; }
summary { cursor: pointer; font-weight: 600; }
.meta { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px; }
.purpose { margin-top: 16px; }
.label { font-weight: 700; }
.tests table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.tests th, .tests td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.85rem; }
.pill.pass { background: #e6fcf5; color: #0b7285; }
.pill.fail { background: #ffe3e3; color: #c92a2a; }
.steps li { margin-bottom: 6px; }
.debug pre { white-space: pre-wrap; }
.expectations li { margin-bottom: 8px; }
.expectations details { margin-top: 6px; }
"""
    prompt_section = ""
    if prompt:
        label = "Prompt" if prompt.strip().startswith("/") else "Subagent Prompt"
        prompt_section = f"<h3>{label}</h3><pre>{_escape_html(prompt)}</pre>"
    payload_section = ""
    if prompt_payload:
        payload_section = f"<h3>Input Payload</h3><pre>{_escape_html(prompt_payload)}</pre>"
    summary_section = ""
    if test_summary:
        summary_section = f"<h2>Summary</h2><p>{_escape_html(test_summary)}</p>"
    steps_section = ""
    if test_steps:
        steps = [s.strip() for s in test_steps.split(";") if s.strip()]
        if steps:
            steps_section = "<h2>Steps</h2><ul class=\"steps\">" + "".join(
                f"<li>{_escape_html(step)}</li>" for step in steps
            ) + "</ul>"
    claude_section = ""
    if claude_command:
        claude_section = f"<h2>Claude Command</h2><pre>{_escape_html(claude_command)}</pre>"
    slash_section = ""
    slash_prompt = None
    if trace_prompt and trace_prompt.strip().startswith("/"):
        slash_prompt = trace_prompt
    elif claude_command:
        slash_prompt = _extract_prompt_from_claude_command(claude_command)
    if slash_prompt:
        slash_section = f"<h2>Slash Command</h2><pre>{_escape_html(slash_prompt)}</pre>"
    events_section = ""
    if trace_events:
        rows = "".join(
            f"<tr><td>{_escape_html(e['event'])}</td><td>{_escape_html(e['summary'])}</td></tr>" for e in trace_events
        )
        events_section = (
            "<h2>Subagent Events</h2>"
            "<table><thead><tr><th>Event</th><th>Details</th></tr></thead><tbody>"
            f"{rows}</tbody></table>"
        )
    expectations_section = ""
    if expectations:
        items = []
        for entry in expectations:
            status = "✅" if entry.get("met") else "❌"
            label = _escape_html(str(entry.get("label") or "Expectation"))
            details = entry.get("details") or ""
            details_html = ""
            if details:
                details_html = (
                    "<details><summary>Details</summary>"
                    f"<pre>{_escape_html(str(details))}</pre></details>"
                )
            items.append(f"<li>{status} {label}{details_html}</li>")
        expectations_section = "<h2>Expectations</h2><ul class=\"expectations\">" + "".join(items) + "</ul>"
    status = "pass" if passed else "fail"
    status_label = "PASS" if passed else "FAIL"
    tests_table = (
        "<div class=\"tests\">"
        "<h2>Tests</h2>"
        "<table><thead><tr>"
        "<th>Status</th><th>Test Name</th><th>Agent/Command</th><th>Test Script</th><th>Purpose</th>"
        "</tr></thead><tbody>"
        f"<tr><td><span class=\"pill {status}\">{status_label}</span></td>"
        f"<td>{_escape_html(_safe_text(test_name))}</td>"
        f"<td>{_escape_html(_safe_text(agent_name))}</td>"
        f"<td>{_escape_html(_safe_text(test_script))}</td>"
        f"<td>{_escape_html(_safe_text(test_description))}</td></tr>"
        "</tbody></table></div>"
    )
    debug_section = ""
    claude_section_detail = ""
    if claude_output:
        claude_section_detail = f"<h3>Claude Response</h3><pre>{_escape_html(claude_output)}</pre>"
    if prompt_section or payload_section or trace_section or output or claude_section_detail:
        debug_section = (
            "<details class=\"debug\"><summary>Debug Details</summary>"
            "<h3>pytest output</h3>"
            f"<pre>{_escape_html(output)}</pre>"
            f"{claude_section_detail}"
            f"{prompt_section}"
            f"{payload_section}"
            f"{trace_section}"
            "</details>"
        )
    return (
        "<!doctype html>"
        "<html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>{css}</style></head><body>"
        f"<h1>{title} {timestamp}</h1>"
        f"{selection}"
        f"{tests_table}"
        f"{summary_section}"
        f"{steps_section}"
        f"{claude_section}"
        f"{slash_section}"
        f"{expectations_section}"
        f"{events_section}"
        f"{debug_section}"
        "</body></html>"
    )


def _render_trace_html(entries: list[dict[str, str | bool]]) -> str:
    parts = ["<h2>Hook Trace</h2>"]
    for idx, entry in enumerate(entries, start=1):
        tool_name = entry["tool_name"]
        input_label = entry["input_label"]
        input_value = entry["input_value"]
        response_text = entry["response_text"]
        is_error = bool(entry["is_error"])
        status = "❌" if is_error else "✅"
        response_class = "error" if is_error else ""
        summary = entry.get("response_summary") or ""
        parts.append(
            "<details>"
            f"<summary>{status} {tool_name} — {summary}</summary>"
            f"<div><span class=\"cmd\">{input_label}:</span> "
            f"<code>{_escape_html(str(input_value))}</code></div>"
            f"<pre class=\"{response_class}\">{_escape_html(str(response_text))}</pre>"
            "</details>"
        )
    return "".join(parts)


def _render_selection_html(args: argparse.Namespace) -> str:
    parts = []
    if args.test_name:
        parts.append(f"<div><strong>Test Name:</strong> {_escape_html(args.test_name)}</div>")
    if args.agent_name:
        parts.append(f"<div><strong>Agent:</strong> {_escape_html(args.agent_name)}</div>")
    if args.test_description:
        parts.append(f"<div class=\"purpose\"><span class=\"label\">Purpose:</span> {_escape_html(args.test_description)}</div>")
    if args.package:
        parts.append(f"<div><strong>Package:</strong> {_escape_html(args.package)}</div>")
    if args.test_repo:
        parts.append(f"<div><strong>Test Repo:</strong> {_escape_html(args.test_repo)}</div>")
    if not parts:
        return ""
    return f"<div class=\"meta\">{''.join(parts)}</div>"


def _extract_prompt(lines: list[str]) -> str | None:
    for line in lines:
        try:
            record = json.loads(line)
        except Exception:
            continue
        if record.get("event") != "UserPromptSubmit":
            continue
        stdin = record.get("stdin") or ""
        try:
            payload = json.loads(stdin)
        except Exception:
            payload = {}
        prompt = payload.get("prompt")
        if prompt:
            return str(prompt)
    return None


def _extract_prompt_from_claude_command(command: str) -> str | None:
    marker = "-p"
    if marker not in command:
        return None
    parts = command.split(marker, 1)[1].strip()
    if not parts:
        return None
    if parts[0] in {"'", '"'}:
        quote = parts[0]
        end = parts.find(quote, 1)
        if end == -1:
            return None
        return parts[1:end]
    return None


def _evaluate_expectations(
    trace_entries: list[dict[str, str | bool]],
    trace_events: list[dict[str, str]],
    prompt: str | None,
    expect_tool: list[str],
    expect_read: list[str],
    expect_event: list[str],
    expect_prompt: list[str],
    expect_output: list[str],
    claude_output: str,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    tool_entries = [entry for entry in trace_entries if entry.get("input_label") == "Command"]
    read_entries = [entry for entry in trace_entries if entry.get("input_label") == "File Path"]
    event_names = [entry.get("event") for entry in trace_events]
    for item in expect_tool:
        label, pattern = _split_expect(item)
        matched = [entry for entry in tool_entries if _regex_match(pattern, str(entry.get("input_value") or ""))]
        details = _format_expectation_details(matched)
        results.append({"label": label, "met": bool(matched), "details": details})
    for item in expect_read:
        label, pattern = _split_expect(item)
        matched = [entry for entry in read_entries if _regex_match(pattern, str(entry.get("input_value") or ""))]
        details = _format_expectation_details(matched)
        results.append({"label": label, "met": bool(matched), "details": details})
    for item in expect_event:
        label, event = _split_expect(item)
        matched = [name for name in event_names if name == event]
        results.append({"label": label, "met": bool(matched), "details": "\n".join(matched[:5])})
    for item in expect_prompt:
        label, pattern = _split_expect(item)
        matched = bool(prompt and _regex_match(pattern, prompt))
        results.append({"label": label, "met": matched, "details": prompt or ""})
    for item in expect_output:
        label, pattern = _split_expect(item)
        matched = bool(claude_output and _regex_match(pattern, claude_output))
        results.append({"label": label, "met": matched, "details": claude_output})
    return results


def _split_expect(raw: str) -> tuple[str, str]:
    if "::" in raw:
        label, pattern = raw.split("::", 1)
        return label.strip() or "Expectation", pattern.strip()
    return raw.strip(), raw.strip()


def _regex_match(pattern: str, text: str) -> bool:
    try:
        return re.search(pattern, text) is not None
    except re.error:
        return pattern in text


def _format_expectation_details(entries: list[dict[str, str | bool]]) -> str:
    if not entries:
        return ""
    blocks = []
    for entry in entries[:3]:
        input_value = str(entry.get("input_value") or "")
        response_text = str(entry.get("response_text") or "")
        block = f"Input: {input_value}"
        if response_text:
            block += f"\nResponse:\n{response_text}"
        blocks.append(block)
    return "\n\n".join(blocks)


def _extract_events(lines: list[str]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for line in lines:
        try:
            record = json.loads(line)
        except Exception:
            continue
        event = record.get("event")
        if event not in {"SubagentStart", "SubagentStop", "Notification", "PermissionRequest"}:
            continue
        stdin = record.get("stdin") or ""
        try:
            payload = json.loads(stdin)
        except Exception:
            payload = {}
        env = record.get("env") or {}
        if isinstance(env, dict) and env:
            agent_id = env.get("CLAUDE_AGENT_ID")
            agent_task = env.get("CLAUDE_AGENT_TASK")
            agent_status = env.get("CLAUDE_AGENT_STATUS")
            summary_parts = []
            if agent_id:
                summary_parts.append(f"id={agent_id}")
            if agent_task:
                summary_parts.append(f"task={agent_task}")
            if agent_status:
                summary_parts.append(f"status={agent_status}")
            if summary_parts:
                summary = ", ".join(summary_parts)
            else:
                summary = payload.get("message") or payload.get("status") or payload.get("result") or json.dumps(payload, ensure_ascii=True)
        else:
            summary = payload.get("message") or payload.get("status") or payload.get("result") or json.dumps(payload, ensure_ascii=True)
        events.append({"event": str(event), "summary": str(summary)[:200]})
    return events


def _extract_prompt_payload(prompt: str | None) -> str | None:
    if not prompt:
        return None
    marker = "<<'JSON'"
    if marker not in prompt:
        return None
    after = prompt.split(marker, 1)[1]
    parts = after.split("\n")
    if len(parts) < 2:
        return None
    payload_lines = []
    for line in parts[1:]:
        if line.strip() == "JSON":
            break
        payload_lines.append(line)
    payload = "\n".join(payload_lines).strip()
    return payload or None


def _safe_text(text: str | None) -> str:
    return text or "-"




def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
