#!/usr/bin/env python3
"""Launch supported AI CLIs in detected terminals across macOS and Windows."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from launch_term_shared import (
    build_claude_session_record_path,
    build_codex_session_record_path,
    generate_ulid,
    normalize_passthrough_args,
    quote_powershell,
    quote_shell,
    resolve_identity,
    resolve_team,
    shell_mode_for_terminal,
)


MAC_TERMINALS = ("iterm2", "ghostty", "wezterm", "warp", "terminal")
WINDOWS_TERMINALS = ("wt", "warp")
CLAUDE_MODELS = ("sonnet", "haiku", "opus")
TEAM_MEMBER_MODELS = CLAUDE_MODELS + ("codex", "gemini")
MACOS_SHELL_SETTLE_DELAY_SECONDS = 0.8


def emit_json(data: dict) -> None:
    print(json.dumps(data))


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    sys.exit(exit_code)


def applescript_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def detect_macos_app(app_name: str) -> bool:
    try:
        result = subprocess.run(
            ["osascript", "-e", f'id of application "{app_name}"'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def warp_launch_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / ".warp" / "launch_configurations"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            fail("APPDATA is not set; cannot locate Warp launch configuration directory")
        return Path(appdata) / "warp" / "Warp" / "data" / "launch_configurations"
    fail("Warp launch configuration automation is only supported on macOS and Windows")


def available_terminals() -> list[str]:
    if sys.platform == "darwin":
        available: list[str] = []
        if detect_macos_app("iTerm2"):
            available.append("iterm2")
        if detect_macos_app("Ghostty"):
            available.append("ghostty")
        if command_exists("wezterm"):
            available.append("wezterm")
        if detect_macos_app("Warp"):
            available.append("warp")
        if detect_macos_app("Terminal"):
            available.append("terminal")
        return available

    if os.name == "nt":
        available = []
        if command_exists("wt") or command_exists("wt.exe"):
            available.append("wt")
        if warp_launch_config_dir().parent.exists():
            available.append("warp")
        return available

    return []


def platform_supported_terminals() -> list[str]:
    if sys.platform == "darwin":
        return list(MAC_TERMINALS)
    if os.name == "nt":
        return list(WINDOWS_TERMINALS)
    return []


def resolve_terminal(requested: str | None) -> str:
    aliases = {
        "auto": "auto",
        "windows-terminal": "wt",
        "terminal.app": "terminal",
    }
    requested_value = aliases.get((requested or "auto").lower(), (requested or "auto").lower())

    supported = platform_supported_terminals()
    available = available_terminals()

    if requested_value == "auto":
        if not available:
            fail(
                f"No supported terminals detected on this platform. Supported: {', '.join(supported)}"
            )
        return available[0]

    if requested_value not in supported:
        fail(
            f"Unsupported terminal '{requested_value}' for this platform. Supported: {', '.join(supported)}"
        )

    if requested_value not in available:
        fail(
            f"Requested terminal '{requested_value}' is not available. Detected: {', '.join(available) or 'none'}"
        )

    return requested_value


def detect_command() -> None:
    emit_json(
        {
            "platform": sys.platform,
            "supported": platform_supported_terminals(),
            "available": available_terminals(),
            "default": resolve_terminal("auto") if available_terminals() else None,
        }
    )


def tmux_available() -> bool:
    return command_exists("tmux")


def next_tmux_name(name: str) -> str:
    candidate = name
    index = 2
    while True:
        result = subprocess.run(
            ["tmux", "has-session", "-t", candidate],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            return candidate
        candidate = f"{name}({index})"
        index += 1


def check_session(name: str) -> None:
    if not tmux_available():
        emit_json({"available": False, "exists": False, "next_name": name})
        return

    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    exists = result.returncode == 0
    emit_json(
        {
            "available": True,
            "exists": exists,
            "next_name": next_tmux_name(name) if exists else name,
        }
    )


def osascript(script: str) -> None:
    subprocess.run(["osascript", "-e", script], check=True)


def launch_iterm2(shell_command: str, use_tab: bool) -> None:
    escaped = applescript_escape(shell_command)
    if use_tab:
        script = f'''tell application "iTerm2"
  activate
  if (count of windows) = 0 then
    create window with default profile
    tell current session of current window
      write text "{escaped}"
    end tell
  else
    tell current window
      create tab with default profile
      tell current session of current tab
        delay {MACOS_SHELL_SETTLE_DELAY_SECONDS}
        write text "{escaped}"
      end tell
    end tell
  end if
end tell'''
    else:
        script = f'''tell application "iTerm2"
  activate
  create window with default profile
  tell current session of current window
    delay {MACOS_SHELL_SETTLE_DELAY_SECONDS}
    write text "{escaped}"
  end tell
end tell'''
    osascript(script)


def launch_terminal_app(shell_command: str, use_tab: bool) -> None:
    escaped = applescript_escape(shell_command)
    if use_tab:
        script = f'''tell application "Terminal"
  activate
  if (count of windows) = 0 then
    do script "{escaped}"
  else
    do script "{escaped}" in front window
  end if
end tell'''
    else:
        script = f'''tell application "Terminal"
  activate
  do script "{escaped}"
end tell'''
    osascript(script)


def launch_ghostty(shell_command: str, dir_path: str, use_tab: bool) -> None:
    escaped_dir = applescript_escape(dir_path)
    escaped_cmd = applescript_escape(shell_command)
    if use_tab:
        script = f'''tell application "Ghostty"
  activate
  set cfg to new surface configuration
  set initial working directory of cfg to "{escaped_dir}"
  if (count of windows) = 0 then
    set win to new window with configuration cfg
    set targetTerm to focused terminal of selected tab of win
  else
    set win to front window
    set tabRef to new tab in win with configuration cfg
    set targetTerm to focused terminal of tabRef
  end if
  delay {MACOS_SHELL_SETTLE_DELAY_SECONDS}
  input text "{escaped_cmd}" to targetTerm
  send key "enter" to targetTerm
  focus targetTerm
end tell'''
    else:
        script = f'''tell application "Ghostty"
  activate
  set cfg to new surface configuration
  set initial working directory of cfg to "{escaped_dir}"
  set win to new window with configuration cfg
  set targetTerm to focused terminal of selected tab of win
  delay {MACOS_SHELL_SETTLE_DELAY_SECONDS}
  input text "{escaped_cmd}" to targetTerm
  send key "enter" to targetTerm
  focus targetTerm
end tell'''
    osascript(script)


def launch_wezterm(shell_command: str, dir_path: str, use_tab: bool) -> None:
    start_cmd = ["wezterm", "start"]
    if use_tab:
        start_cmd.append("--new-tab")
    else:
        start_cmd.append("--always-new-process")
    start_cmd.extend(["--cwd", dir_path])
    subprocess.run(start_cmd, check=True)
    time.sleep(0.35)
    subprocess.run(["wezterm", "cli", "send-text", "--no-paste", shell_command], check=True)
    subprocess.run(["wezterm", "cli", "send-text", "--no-paste", "\n"], check=True)


def write_warp_launch_config(command: str, dir_path: str, title: str) -> Path:
    config_dir = warp_launch_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "sc-launch-term.generated.yaml"
    yaml_text = "\n".join(
        [
            "---",
            f"name: {json.dumps(title)}",
            "windows:",
            "  - tabs:",
            f"      - title: {json.dumps(title)}",
            "        layout:",
            f"          cwd: {json.dumps(dir_path)}",
            "          commands:",
            f"            - exec: {json.dumps(command)}",
            "",
        ]
    )
    config_path.write_text(yaml_text, encoding="utf-8")
    return config_path


def launch_warp(shell_command: str, dir_path: str, use_tab: bool, title: str) -> None:
    if use_tab:
        fail("Warp automation currently supports new-window launches only; omit --tab or choose another terminal")

    config_path = write_warp_launch_config(shell_command, dir_path, title)
    uri = f"warp://launch/{urllib.parse.quote(str(config_path), safe='')}"
    if sys.platform == "darwin":
        subprocess.run(["open", uri], check=True)
        return
    if os.name == "nt":
        os.startfile(uri)  # type: ignore[attr-defined]
        return
    fail("Warp automation is only supported on macOS and Windows")


def preferred_windows_shell() -> list[str]:
    if command_exists("pwsh"):
        return ["pwsh", "-NoExit", "-Command"]
    return ["powershell", "-NoExit", "-Command"]


def launch_windows_terminal(shell_command: str, dir_path: str, use_tab: bool) -> None:
    shell_prefix = preferred_windows_shell()
    command = ["wt"]
    if use_tab:
        command.extend(["-w", "0"])
    command.extend(["new-tab", "-d", dir_path])
    command.extend(shell_prefix)
    command.append(shell_command)
    subprocess.run(command, check=True)


def run_launch(terminal: str, shell_command: str, dir_path: str, use_tab: bool, title: str) -> None:
    if terminal == "iterm2":
        launch_iterm2(shell_command, use_tab)
        return
    if terminal == "terminal":
        launch_terminal_app(shell_command, use_tab)
        return
    if terminal == "ghostty":
        launch_ghostty(shell_command, dir_path, use_tab)
        return
    if terminal == "wezterm":
        launch_wezterm(shell_command, dir_path, use_tab)
        return
    if terminal == "warp":
        launch_warp(shell_command, dir_path, use_tab, title)
        return
    if terminal == "wt":
        launch_windows_terminal(shell_command, dir_path, use_tab)
        return
    fail(f"Unhandled terminal backend: {terminal}")


def register_team_member(
    team: str | None,
    identity: str | None,
    model: str | None,
    cwd: str,
) -> None:
    if not team:
        return
    if not identity:
        fail(f"ATM_TEAM is set to '{team}'; supply --identity <name> for this launch")
    if not model:
        fail("ATM_TEAM launch registration requires a member model")
    if not command_exists("atm"):
        fail("ATM_TEAM is set, but `atm` is not available on PATH")

    command = [
        "atm",
        "teams",
        "add-member",
        team,
        identity,
        "--model",
        model,
        "--cwd",
        cwd,
    ]
    # TODO: When tmux pane IDs are surfaced here, append `--pane-id <pane-id>`
    # for pane-targeted launches such as `attach-pane`.
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        fail(f"`{' '.join(command)}` failed with exit code {exc.returncode}")


def render_command_argv(command_argv: list[str], terminal: str) -> str:
    shell_mode = shell_mode_for_terminal(terminal)
    if shell_mode == "powershell":
        return "& " + " ".join(quote_powershell(part) for part in command_argv)
    return shlex.join(command_argv)


def build_claude_argv(model: str, extra_args: list[str], teammate_mode: bool) -> list[str]:
    command = ["claude", "--model", model, "--dangerously-skip-permissions"]
    if teammate_mode:
        command.extend(["--teammate-mode", "tmux"])
    command.extend(extra_args)
    return command


def apply_env_prefix(
    command: str,
    terminal: str,
    env_vars: dict[str, str],
) -> str:
    filtered = {key: value for key, value in env_vars.items() if value}
    if not filtered:
        return command
    shell_mode = shell_mode_for_terminal(terminal)
    if shell_mode == "powershell":
        assignments: list[str] = []
        for key, value in filtered.items():
            assignments.append(f"$env:{key} = {quote_powershell(value)}")
        return "; ".join(assignments + [command])
    exports: list[str] = []
    for key, value in filtered.items():
        exports.append(f"export {key}={quote_shell(value)}")
    return " && ".join(exports + [command])


def apply_atm_env_prefix(
    command: str,
    terminal: str,
    team: str | None,
    identity: str | None,
) -> str:
    env_vars: dict[str, str] = {}
    if team:
        env_vars["ATM_TEAM"] = team
    if identity:
        env_vars["ATM_IDENTITY"] = identity
    return apply_env_prefix(command, terminal, env_vars)


def wait_for_path(path: Path, timeout_seconds: float = 5.0, interval_seconds: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(interval_seconds)
    return path.exists()


def build_tmux_launch(command: str, dir_path: str, session_name: str) -> str:
    return (
        f"tmux new-session -s {quote_shell(session_name)} "
        f"-c {quote_shell(dir_path)} {quote_shell(command)}"
    )


def build_tmux_attach(session_name: str) -> str:
    return f"tmux attach-session -t {quote_shell(session_name)}"


def build_tmux_attach_pane(session_name: str, command: str) -> str:
    return (
        f"tmux split-window -t {quote_shell(session_name)} {quote_shell(command)}; "
        f"tmux attach-session -t {quote_shell(session_name)}"
    )


def prepare_shell_command(
    terminal: str,
    command: str,
    dir_path: str,
    tmux_session: str | None,
) -> str:
    if tmux_session:
        return build_tmux_launch(command, dir_path, tmux_session)
    if terminal in {"iterm2", "terminal"}:
        return f"cd {quote_shell(dir_path)} && {command}"
    return command


def title_from_command(command: str) -> str:
    first = command.split()[0]
    return f"sc-launch-term {first}"


def title_from_label(label: str) -> str:
    return f"sc-launch-term {label}"


def session_tracking_for_member_model(
    member_model: str | None,
    dir_path: str,
) -> tuple[str, Path] | tuple[None, None]:
    if member_model == "codex":
        launch_id = generate_ulid()
        return launch_id, build_codex_session_record_path(dir_path, launch_id)
    return None, None


def handle_launch(args: argparse.Namespace) -> None:
    terminal = resolve_terminal(args.terminal)
    if args.tmux and not tmux_available():
        fail("tmux is not available on PATH; omit --tmux or install tmux")

    team = resolve_team()
    identity = resolve_identity(args.identity, args.member_model)
    register_team_member(team, identity, args.member_model, args.dir)
    launch_id, session_record = session_tracking_for_member_model(args.member_model, args.dir)
    env_vars: dict[str, str] = {}
    if launch_id and session_record:
        env_vars["SC_LAUNCH_ID"] = launch_id
        env_vars["SC_SESSION_RECORD"] = str(session_record)
    if team:
        env_vars["ATM_TEAM"] = team
    if identity:
        env_vars["ATM_IDENTITY"] = identity
    command = apply_env_prefix(args.command, terminal, env_vars)
    shell_command = prepare_shell_command(terminal, command, args.dir, args.tmux)
    run_launch(terminal, shell_command, args.dir, args.tab, title_from_command(args.command))
    if launch_id and session_record:
        emit_json(
            {
                "ok": True,
                "tool": args.member_model,
                "launch_id": launch_id,
                "session_record": str(session_record),
                "session_record_found": wait_for_path(session_record),
            }
        )


def handle_attach(args: argparse.Namespace) -> None:
    terminal = resolve_terminal(args.terminal)
    if not tmux_available():
        fail("tmux is not available on PATH; cannot attach to a session")
    run_launch(
        terminal,
        build_tmux_attach(args.session),
        os.getcwd(),
        args.tab,
        f"sc-launch-term attach {args.session}",
    )


def handle_attach_pane(args: argparse.Namespace) -> None:
    terminal = resolve_terminal(args.terminal)
    if not tmux_available():
        fail("tmux is not available on PATH; cannot attach a pane")
    team = resolve_team()
    identity = resolve_identity(args.identity, args.member_model)
    register_team_member(team, identity, args.member_model, args.cwd)
    launch_id, session_record = session_tracking_for_member_model(args.member_model, args.cwd)
    env_vars: dict[str, str] = {}
    if launch_id and session_record:
        env_vars["SC_LAUNCH_ID"] = launch_id
        env_vars["SC_SESSION_RECORD"] = str(session_record)
    if team:
        env_vars["ATM_TEAM"] = team
    if identity:
        env_vars["ATM_IDENTITY"] = identity
    command = apply_env_prefix(args.command, terminal, env_vars)
    run_launch(
        terminal,
        build_tmux_attach_pane(args.session, command),
        os.getcwd(),
        args.tab,
        f"sc-launch-term pane {args.session}",
    )
    if launch_id and session_record:
        emit_json(
            {
                "ok": True,
                "tool": args.member_model,
                "launch_id": launch_id,
                "session_record": str(session_record),
                "session_record_found": wait_for_path(session_record),
            }
        )


def handle_launch_claude_model(args: argparse.Namespace) -> None:
    terminal = resolve_terminal(args.terminal)
    if args.tmux and not tmux_available():
        fail("tmux is not available on PATH; omit --tmux or install tmux")

    team = resolve_team()
    identity = resolve_identity(args.identity, args.model)
    register_team_member(team, identity, args.model, args.dir)
    launch_id = generate_ulid()
    session_record = build_claude_session_record_path(args.dir, launch_id)
    extra_args = normalize_passthrough_args(getattr(args, "claude_args", []))
    command = render_command_argv(
        build_claude_argv(args.model, extra_args, teammate_mode=bool(args.tmux)),
        terminal,
    )
    env_vars = {
        "SC_LAUNCH_ID": launch_id,
        "SC_SESSION_RECORD": str(session_record),
    }
    if team:
        env_vars["ATM_TEAM"] = team
    if identity:
        env_vars["ATM_IDENTITY"] = identity
    command = apply_env_prefix(command, terminal, env_vars)
    shell_command = prepare_shell_command(terminal, command, args.dir, args.tmux)
    run_launch(terminal, shell_command, args.dir, args.tab, title_from_label(args.model))
    emit_json(
        {
            "ok": True,
            "tool": "claude",
            "model": args.model,
            "launch_id": launch_id,
            "session_record": str(session_record),
            "session_record_found": wait_for_path(session_record),
        }
    )


def handle_attach_pane_claude_model(args: argparse.Namespace) -> None:
    terminal = resolve_terminal(args.terminal)
    if not tmux_available():
        fail("tmux is not available on PATH; cannot attach a pane")

    team = resolve_team()
    identity = resolve_identity(args.identity, args.model)
    register_team_member(team, identity, args.model, args.cwd)
    launch_id = generate_ulid()
    session_record = build_claude_session_record_path(args.cwd, launch_id)
    extra_args = normalize_passthrough_args(getattr(args, "claude_args", []))
    command = render_command_argv(
        build_claude_argv(args.model, extra_args, teammate_mode=True),
        terminal,
    )
    env_vars = {
        "SC_LAUNCH_ID": launch_id,
        "SC_SESSION_RECORD": str(session_record),
    }
    if team:
        env_vars["ATM_TEAM"] = team
    if identity:
        env_vars["ATM_IDENTITY"] = identity
    command = apply_env_prefix(command, terminal, env_vars)
    run_launch(
        terminal,
        build_tmux_attach_pane(args.session, command),
        os.getcwd(),
        args.tab,
        f"sc-launch-term pane {args.session}",
    )
    emit_json(
        {
            "ok": True,
            "tool": "claude",
            "model": args.model,
            "launch_id": launch_id,
            "session_record": str(session_record),
            "session_record_found": wait_for_path(session_record),
        }
    )


def split_passthrough_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("detect", help="Show detected terminal backends")

    check = subparsers.add_parser("check-session", help="Check tmux session existence")
    check.add_argument("name")

    launch = subparsers.add_parser("launch", help="Launch a command in a terminal")
    launch.add_argument("command")
    launch.add_argument("dir")
    launch.add_argument("--terminal")
    launch.add_argument("--tab", action="store_true")
    launch.add_argument("--tmux")
    launch.add_argument("--identity")
    launch.add_argument("--member-model", choices=TEAM_MEMBER_MODELS)

    launch_claude_model = subparsers.add_parser(
        "launch-claude-model",
        help="Launch a Claude model with the standard wrapper flags",
    )
    launch_claude_model.add_argument("model", choices=CLAUDE_MODELS)
    launch_claude_model.add_argument("dir")
    launch_claude_model.add_argument("--terminal")
    launch_claude_model.add_argument("--tab", action="store_true")
    launch_claude_model.add_argument("--tmux")
    launch_claude_model.add_argument("--identity")

    attach = subparsers.add_parser("attach", help="Attach to an existing tmux session")
    attach.add_argument("session")
    attach.add_argument("--terminal")
    attach.add_argument("--tab", action="store_true")

    attach_pane = subparsers.add_parser(
        "attach-pane", help="Split a tmux session and launch a command in the new pane"
    )
    attach_pane.add_argument("session")
    attach_pane.add_argument("command")
    attach_pane.add_argument("--cwd", default=os.getcwd())
    attach_pane.add_argument("--terminal")
    attach_pane.add_argument("--tab", action="store_true")
    attach_pane.add_argument("--identity")
    attach_pane.add_argument("--member-model", choices=TEAM_MEMBER_MODELS)

    attach_pane_claude_model = subparsers.add_parser(
        "attach-pane-claude-model",
        help="Split a tmux session and launch a Claude model in the new pane",
    )
    attach_pane_claude_model.add_argument("session")
    attach_pane_claude_model.add_argument("model", choices=CLAUDE_MODELS)
    attach_pane_claude_model.add_argument("--cwd", default=os.getcwd())
    attach_pane_claude_model.add_argument("--terminal")
    attach_pane_claude_model.add_argument("--tab", action="store_true")
    attach_pane_claude_model.add_argument("--identity")

    return parser


def main() -> None:
    parser = build_parser()
    argv, passthrough_args = split_passthrough_argv(sys.argv[1:])
    args = parser.parse_args(argv)
    if args.subcommand in {"launch-claude-model", "attach-pane-claude-model"}:
        args.claude_args = passthrough_args
    elif passthrough_args:
        parser.error("passthrough args after -- are only supported for Claude model launches")

    if args.subcommand == "detect":
        detect_command()
        return
    if args.subcommand == "check-session":
        check_session(args.name)
        return
    if args.subcommand == "launch":
        handle_launch(args)
        return
    if args.subcommand == "launch-claude-model":
        handle_launch_claude_model(args)
        return
    if args.subcommand == "attach":
        handle_attach(args)
        return
    if args.subcommand == "attach-pane":
        handle_attach_pane(args)
        return
    if args.subcommand == "attach-pane-claude-model":
        handle_attach_pane_claude_model(args)
        return
    parser.error(f"unknown subcommand: {args.subcommand}")


if __name__ == "__main__":
    main()
