"""Tests for the sc-launch-term terminal launcher."""

from pathlib import Path
import importlib.util

import pytest


spec = importlib.util.spec_from_file_location(
    "sc_term_launch",
    Path(__file__).parent.parent.parent
    / "packages"
    / "sc-launch-term"
    / "scripts"
    / "sc-term-launch.py",
)
sc_term_launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc_term_launch)


def claude_spec(name):
    return sc_term_launch.agent_models.resolve_model("claude", name)


def codex_spec(name):
    return sc_term_launch.agent_models.resolve_model("codex", name)


def test_build_claude_argv_without_tmux():
    command = sc_term_launch.build_claude_argv(
        claude_spec("sonnet"), None, ["--continue"], teammate_mode=False
    )
    assert command == [
        "claude",
        "--model",
        "claude-sonnet-5-5",
        "--dangerously-skip-permissions",
        "--continue",
    ]


def test_build_claude_argv_with_tmux_and_effort():
    command = sc_term_launch.build_claude_argv(
        claude_spec("haiku"),
        "high",
        ["--resume", "abc123"],
        teammate_mode=True,
    )
    assert command == [
        "claude",
        "--model",
        "claude-haiku-5-5",
        "--effort",
        "high",
        "--dangerously-skip-permissions",
        "--teammate-mode",
        "tmux",
        "--resume",
        "abc123",
    ]


@pytest.mark.parametrize(
    ("model", "model_id"),
    [
        ("sol", "gpt-6.1-sol"),
        ("astra", "gpt-6-astra"),
        ("terra", "gpt-5.6-terra"),
        ("luna", "gpt-6-luna"),
        ("codex", "gpt-6.1-sol"),
        ("gpt-5.6-luna", "gpt-5.6-luna"),
    ],
)
def test_build_codex_argv_routes_models(model, model_id):
    command = sc_term_launch.build_codex_argv(codex_spec(model), None, ["--search"])
    assert command == [
        "codex",
        "--model",
        model_id,
        "--yolo",
        "--enable",
        "hooks",
        "--search",
    ]


def test_build_codex_argv_passes_effort_unquoted():
    command = sc_term_launch.build_codex_argv(codex_spec("astra"), "ultra", [])
    assert command[:5] == ["codex", "--model", "gpt-6-astra", "-c", "model_reasoning_effort=ultra"]


@pytest.mark.parametrize(
    ("tool", "model", "label", "model_id"),
    [
        ("claude", "fable", "fable", "claude-fable-5-1"),
        ("claude", "claude-opus-5-5", "opus", "claude-opus-5-5"),
        ("codex", "codex", "sol", "gpt-6.1-sol"),
        ("codex", "gpt-6-sol", "gpt-6-sol", "gpt-6-sol"),
    ],
)
def test_resolve_model_labels(tool, model, label, model_id):
    spec, got = sc_term_launch.resolve_model(tool, model, None)
    assert (got, spec.id) == (label, model_id)


def test_resolve_model_rejects_unsupported_effort(capsys):
    with pytest.raises(SystemExit):
        sc_term_launch.resolve_model("codex", "luna", "ultra")
    assert "Supported: low, medium, high, xhigh, max" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("tool", "label", "family"),
    [("claude", "opus", "opus"), ("claude", "claude-opus-5-5", "opus"), ("codex", "gpt-6-sol", "sol")],
)
def test_identity_family(tool, label, family):
    assert sc_term_launch.identity_family(tool, label) == family


def test_model_choices_come_from_shared_table():
    agent_models = sc_term_launch.agent_models
    assert set(sc_term_launch.CODEX_MODELS) == set(agent_models.ALIASES["codex"]) | set(agent_models.MODELS["codex"])
    assert set(sc_term_launch.CLAUDE_MODELS) == set(agent_models.ALIASES["claude"]) | set(agent_models.MODELS["claude"])
    for alias in agent_models.ALIASES["codex"]:
        if alias != "codex":
            assert alias in sc_term_launch._IDENTITY_NAMES, f"add an identity pool for {alias}"
    for alias in agent_models.ALIASES["claude"]:
        assert alias in sc_term_launch._IDENTITY_NAMES, f"add an identity pool for {alias}"


def test_render_command_argv_posix_quotes_spaces():
    command = sc_term_launch.render_command_argv(
        ["claude", "--model", "opus", "--resume", "session with spaces"],
        "wezterm",
    )
    assert command == "claude --model opus --resume 'session with spaces'"


def test_render_command_argv_powershell_quotes_spaces():
    command = sc_term_launch.render_command_argv(
        ["claude", "--model", "sonnet", "--resume", "session with spaces"],
        "wt",
    )
    assert command == "& 'claude' '--model' 'sonnet' '--resume' 'session with spaces'"


def test_parser_collects_passthrough_claude_args():
    argv, passthrough = sc_term_launch.split_passthrough_argv(
        [
            "launch-claude-model",
            "sonnet",
            "/tmp/project",
            "--terminal",
            "wezterm",
            "--",
            "--continue",
            "--resume",
            "abc123",
        ]
    )
    parser = sc_term_launch.build_parser()
    args = parser.parse_args(argv)
    assert args.subcommand == "launch-claude-model"
    assert args.model == "sonnet"
    assert args.dir == "/tmp/project"
    assert args.terminal == "wezterm"
    assert passthrough == ["--continue", "--resume", "abc123"]


def test_parser_collects_passthrough_codex_args():
    argv, passthrough = sc_term_launch.split_passthrough_argv(
        [
            "launch-codex-model",
            "sol",
            "/tmp/project",
            "--terminal",
            "cmux",
            "--",
            "--search",
        ]
    )
    parser = sc_term_launch.build_parser()
    args = parser.parse_args(argv)
    assert args.subcommand == "launch-codex-model"
    assert args.model == "sol"
    assert args.effort is None
    assert args.dir == "/tmp/project"
    assert args.terminal == "cmux"
    assert passthrough == ["--search"]


def test_apply_atm_env_prefix_posix():
    command = sc_term_launch.apply_atm_env_prefix(
        "claude --model sonnet",
        "wezterm",
        "annotations-test",
        "alice",
    )
    assert (
        command
        == "export ATM_TEAM=annotations-test && export ATM_IDENTITY=alice"
        " && export BEADS_ACTOR=alice && claude --model sonnet"
    )


def test_apply_atm_env_prefix_powershell():
    command = sc_term_launch.apply_atm_env_prefix(
        "& 'claude' '--model' 'sonnet'",
        "wt",
        "annotations-test",
        "alice",
    )
    assert (
        command
        == "$env:ATM_TEAM = 'annotations-test'; $env:ATM_IDENTITY = 'alice';"
        " $env:BEADS_ACTOR = 'alice'; & 'claude' '--model' 'sonnet'"
    )


def test_resolve_identity_generates_random_when_omitted(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None)
    assert identity is not None
    assert len(identity) > 0


def test_resolve_identity_accepts_value_when_atm_team_set(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    assert sc_term_launch.resolve_identity("alice") == "alice"


def test_resolve_identity_uses_tool_pool(monkeypatch):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None, "gemini")
    name, suffix = identity.rsplit("-", 1)
    assert name in sc_term_launch._IDENTITY_NAMES["gemini"]
    assert len(suffix) == 4


@pytest.mark.parametrize("model", ["sol", "astra", "terra", "luna", "codex"])
def test_resolve_identity_uses_codex_model_pool(monkeypatch, model):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    identity = sc_term_launch.resolve_identity(None, model)
    name, suffix = identity.rsplit("-", 1)
    pool_model = "sol" if model == "codex" else model
    assert name in sc_term_launch._IDENTITY_NAMES[pool_model]
    assert len(suffix) == 4


def test_identity_generator_is_the_shared_agent_identity_module(monkeypatch):
    import agent_identity

    assert sc_term_launch.resolve_identity is agent_identity.resolve_identity
    assert sc_term_launch._IDENTITY_NAMES is agent_identity._IDENTITY_NAMES
    monkeypatch.setattr(agent_identity.secrets, "choice", lambda pool: pool[0])
    monkeypatch.setattr(agent_identity.secrets, "token_hex", lambda nbytes: "beef")
    assert sc_term_launch.resolve_identity(None, "codex") == "Smith-beef"
    assert sc_term_launch.resolve_identity(None, "opus") == "Orion-beef"
    assert sc_term_launch.resolve_identity(None, "unknown-family") == "Amber-beef"
    assert sc_term_launch.resolve_identity("alice", "opus") == "alice"


def test_generate_ulid_and_session_path():
    launch_id = sc_term_launch.generate_ulid()
    path = sc_term_launch.build_claude_session_record_path("/tmp/project", launch_id)
    assert len(launch_id) == 26
    assert path.parent == Path("/tmp/project").resolve() / ".sc" / "sessions" / "claude"
    assert path.stem.endswith(launch_id)


def test_generate_codex_session_path():
    launch_id = sc_term_launch.generate_ulid()
    path = sc_term_launch.build_codex_session_record_path("/tmp/project", launch_id)
    assert path.parent == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    assert path.stem.endswith(launch_id)


def test_session_tracking_for_codex_member_model():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "codex", "/tmp/project"
    )
    assert launch_id is not None
    assert session_record is not None
    assert (
        session_record.parent
        == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    )
    assert session_record.stem.endswith(launch_id)


def test_session_tracking_for_non_codex_member_model():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "gemini", "/tmp/project"
    )
    assert launch_id is None
    assert session_record is None


def test_session_tracking_for_codex_model_alias():
    launch_id, session_record = sc_term_launch.session_tracking_for_member_model(
        "sol", "/tmp/project"
    )
    assert launch_id is not None
    assert session_record is not None
    assert (
        session_record.parent
        == Path("/tmp/project").resolve() / ".sc" / "sessions" / "codex"
    )


def test_apply_env_prefix_with_session_tracking_posix():
    command = sc_term_launch.apply_env_prefix(
        "claude --model haiku",
        "ghostty",
        {
            "SC_LAUNCH_ID": "01JVY7YVYH57FHE2S2P0S8F3XW",
            "SC_SESSION_RECORD": "/tmp/project/.sc/sessions/claude/session.json",
        },
    )
    assert (
        command
        == "export SC_LAUNCH_ID=01JVY7YVYH57FHE2S2P0S8F3XW && export SC_SESSION_RECORD=/tmp/project/.sc/sessions/claude/session.json && claude --model haiku"
    )


def test_launch_cmux_creates_focused_workspace(monkeypatch):
    calls = []

    def fake_run(command, *, check):
        calls.append((command, check))

    monkeypatch.setattr(sc_term_launch.subprocess, "run", fake_run)
    sc_term_launch.launch_cmux("claude --model fable", "/tmp/project", True, "fable")

    assert calls == [
        (
            [
                "cmux",
                "new-workspace",
                "--cwd",
                "/tmp/project",
                "--name",
                "fable",
                "--command",
                "claude --model fable",
                "--focus",
                "true",
            ],
            True,
        )
    ]



# --- ATM team / identity handling across every launch path and backend -----

PARENT_IDENTITY = "Parent-1234"
PARENT_ACTOR = "Parent-Actor"  # the parent's BEADS_ACTOR (bd audit/slot attribution)
POSIX_CLEAR = "unset ATM_IDENTITY BEADS_ACTOR"
POWERSHELL_CLEAR = "Remove-Item Env:ATM_IDENTITY,Env:BEADS_ACTOR -ErrorAction SilentlyContinue"

# (subcommand argv, handler name) for every path that builds a child command.
LAUNCH_PATHS = [
    (["launch-claude-model", "opus", "/tmp/project"], "handle_launch_claude_model"),
    (["launch-claude-model", "opus", "/tmp/project", "--tmux", "proj - opus"], "handle_launch_claude_model"),
    (["launch-codex-model", "sol", "/tmp/project"], "handle_launch_codex_model"),
    (
        ["attach-pane-claude-model", "sess", "opus", "--cwd", "/tmp/project"],
        "handle_attach_pane_claude_model",
    ),
    (
        ["attach-pane-codex-model", "sess", "sol", "--cwd", "/tmp/project"],
        "handle_attach_pane_codex_model",
    ),
    (
        ["launch", "gemini --yolo", "/tmp/project", "--member-model", "gemini"],
        "handle_launch",
    ),
    (
        ["launch", "codex --yolo", "/tmp/project", "--member-model", "codex", "--tmux", "proj - codex"],
        "handle_launch",
    ),
    (
        ["attach-pane", "sess", "gemini --yolo", "--cwd", "/tmp/project", "--member-model", "gemini"],
        "handle_attach_pane",
    ),
]
PATH_IDS = [" ".join(argv[:2]) + (" tmux" if "--tmux" in argv else "") for argv, _ in LAUNCH_PATHS]
# Every backend; wt renders PowerShell, the rest render POSIX shell.
TERMINALS = ["iterm2", "terminal", "ghostty", "wezterm", "warp", "cmux", "wt"]


@pytest.fixture
def launch_harness(monkeypatch, tmp_path):
    """Run a handler through the real backend code with every process call captured.

    Nothing launches, sleeps or waits. Returns a dict with the child command
    (env prefix + tool command), every rendered backend call (argv, env kwarg,
    and the Warp launch config text), and the `atm teams add-member` calls.
    """
    calls = {"child": [], "subprocess": []}
    real_apply_env_prefix = sc_term_launch.apply_env_prefix

    def record_child_command(*args, **kwargs):
        child = real_apply_env_prefix(*args, **kwargs)
        calls["child"].append(child)
        return child

    monkeypatch.setattr(sc_term_launch, "apply_env_prefix", record_child_command)
    monkeypatch.setattr(sc_term_launch, "resolve_terminal", lambda requested: requested)
    monkeypatch.setattr(sc_term_launch, "tmux_available", lambda: True)
    monkeypatch.setattr(sc_term_launch, "command_exists", lambda name: True)
    monkeypatch.setattr(sc_term_launch, "wait_for_path", lambda path: False)
    monkeypatch.setattr(sc_term_launch, "emit_json", lambda data: None)
    monkeypatch.setattr(sc_term_launch.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(sc_term_launch.sys, "platform", "darwin")
    monkeypatch.setattr(sc_term_launch, "warp_launch_config_dir", lambda: tmp_path)
    monkeypatch.setattr(
        sc_term_launch.subprocess,
        "run",
        lambda command, **kwargs: calls["subprocess"].append((command, kwargs.get("env"))),
    )

    def run(argv, handler, terminal, identity=None):
        argv = [*argv, "--terminal", terminal]
        if identity:
            argv += ["--identity", identity]
        args = sc_term_launch.build_parser().parse_args(argv)
        args.model_args = []
        getattr(sc_term_launch, handler)(args)
        assert len(calls["child"]) == 1
        add_member = [c for c, _ in calls["subprocess"] if c[:3] == ["atm", "teams", "add-member"]]
        backend = [(c, env) for c, env in calls["subprocess"] if c[:3] != ["atm", "teams", "add-member"]]
        rendered = [repr(c) for c, _ in backend]
        rendered += [path.read_text() for path in tmp_path.glob("*.yaml")]
        assert rendered, "the backend rendered nothing"
        return {
            "child": calls["child"][0],
            "rendered": "\n".join(rendered),
            "envs": [env for _, env in backend],
            "add_member": add_member,
        }

    return run


@pytest.mark.parametrize("terminal", TERMINALS)
@pytest.mark.parametrize(("argv", "handler"), LAUNCH_PATHS, ids=PATH_IDS)
def test_no_team_launch_clears_inherited_identity_on_every_backend(
    monkeypatch, launch_harness, argv, handler, terminal
):
    monkeypatch.delenv("ATM_TEAM", raising=False)
    monkeypatch.setenv("ATM_IDENTITY", PARENT_IDENTITY)
    monkeypatch.setenv("BEADS_ACTOR", PARENT_ACTOR)
    result = launch_harness(argv, handler, terminal)

    for parent_value in (PARENT_IDENTITY, PARENT_ACTOR):
        assert parent_value not in result["child"]
        assert parent_value not in result["rendered"]
    if terminal == "wt":
        assert result["child"].startswith(POWERSHELL_CLEAR + "; ")
        assert "$env:ATM_" not in result["child"]
        assert "$env:BEADS_ACTOR" not in result["child"]
    else:
        assert result["child"].startswith(POSIX_CLEAR + " && ")
        assert "export ATM_" not in result["child"]
        assert "export BEADS_ACTOR" not in result["child"]
    # ATM_TEAM is neither set nor removed in the child.
    assert "ATM_TEAM" not in result["child"]
    assert result["add_member"] == []
    # No backend passes an env dict, and the launcher's own environment (which
    # spawned backends inherit) no longer carries the parent's identity.
    assert all(env is None for env in result["envs"])
    assert "ATM_IDENTITY" not in sc_term_launch.os.environ
    assert "BEADS_ACTOR" not in sc_term_launch.os.environ


@pytest.mark.parametrize("terminal", ["wezterm", "wt"])
def test_no_team_never_removes_inherited_atm_team(monkeypatch, launch_harness, terminal):
    # A blank ATM_TEAM resolves to "no team"; it is left exactly as inherited.
    monkeypatch.setenv("ATM_TEAM", "   ")
    monkeypatch.setenv("ATM_IDENTITY", PARENT_IDENTITY)
    monkeypatch.setenv("BEADS_ACTOR", PARENT_ACTOR)
    result = launch_harness(*LAUNCH_PATHS[0], terminal)

    assert "ATM_TEAM" not in result["child"]
    assert PARENT_IDENTITY not in result["rendered"]
    assert PARENT_ACTOR not in result["rendered"]
    assert result["add_member"] == []
    assert sc_term_launch.os.environ["ATM_TEAM"] == "   "
    assert "ATM_IDENTITY" not in sc_term_launch.os.environ
    assert "BEADS_ACTOR" not in sc_term_launch.os.environ


@pytest.mark.parametrize(("argv", "handler"), LAUNCH_PATHS, ids=PATH_IDS)
def test_no_team_explicit_identity_is_ignored_with_warning(
    monkeypatch, capsys, launch_harness, argv, handler
):
    monkeypatch.delenv("ATM_TEAM", raising=False)
    monkeypatch.delenv("ATM_IDENTITY", raising=False)
    result = launch_harness(argv, handler, "wezterm", identity="alice")

    assert "alice" not in result["child"]
    assert "alice" not in result["rendered"]
    assert result["add_member"] == []
    assert "warning: ignoring --identity alice: ATM_TEAM is not set" in capsys.readouterr().err


@pytest.mark.parametrize("terminal", ["wezterm", "iterm2", "wt"])
@pytest.mark.parametrize(("argv", "handler"), LAUNCH_PATHS, ids=PATH_IDS)
def test_team_launch_registers_and_exports_explicit_identity(
    monkeypatch, launch_harness, argv, handler, terminal
):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    monkeypatch.setenv("ATM_IDENTITY", PARENT_IDENTITY)
    monkeypatch.setenv("BEADS_ACTOR", PARENT_ACTOR)
    result = launch_harness(argv, handler, terminal, identity="alice")

    # BEADS_ACTOR tracks the child's ATM_IDENTITY exactly.
    if terminal == "wt":
        assert (
            "$env:ATM_TEAM = 'atm-core'; $env:ATM_IDENTITY = 'alice'; $env:BEADS_ACTOR = 'alice'; "
            in result["child"]
        )
        assert "Remove-Item" not in result["child"]
    else:
        assert (
            "export ATM_TEAM=atm-core && export ATM_IDENTITY=alice && export BEADS_ACTOR=alice && "
            in result["child"]
        )
        assert "unset" not in result["child"]
    assert PARENT_IDENTITY not in result["rendered"]
    assert PARENT_ACTOR not in result["rendered"]
    assert sc_term_launch.os.environ["ATM_TEAM"] == "atm-core"
    (add_member,) = result["add_member"]
    assert add_member[3:5] == ["atm-core", "alice"]
    assert add_member[-2:] == ["--cwd", "/tmp/project"]


@pytest.mark.parametrize(("argv", "handler"), LAUNCH_PATHS, ids=PATH_IDS)
def test_team_launch_without_identity_never_reuses_inherited_identity(
    monkeypatch, launch_harness, argv, handler
):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    monkeypatch.setenv("ATM_IDENTITY", PARENT_IDENTITY)
    monkeypatch.setenv("BEADS_ACTOR", PARENT_ACTOR)
    result = launch_harness(argv, handler, "wezterm")

    (add_member,) = result["add_member"]
    identity = add_member[4]
    assert identity != PARENT_IDENTITY
    for parent_value in (PARENT_IDENTITY, PARENT_ACTOR):
        assert parent_value not in result["child"]
        assert parent_value not in result["rendered"]
    assert (
        f"export ATM_TEAM=atm-core && export ATM_IDENTITY={identity}"
        f" && export BEADS_ACTOR={identity} && " in result["child"]
    )


def test_team_launch_generates_pool_identity(monkeypatch, launch_harness):
    monkeypatch.setenv("ATM_TEAM", "atm-core")
    result = launch_harness(*LAUNCH_PATHS[0], "wezterm")
    (add_member,) = result["add_member"]
    assert add_member[4].rsplit("-", 1)[0] in sc_term_launch._IDENTITY_NAMES["opus"]


def test_resolve_atm_member_without_team_returns_nothing(monkeypatch):
    monkeypatch.delenv("ATM_TEAM", raising=False)
    monkeypatch.setenv("ATM_IDENTITY", PARENT_IDENTITY)
    monkeypatch.setenv("BEADS_ACTOR", PARENT_ACTOR)
    assert sc_term_launch.resolve_atm_member(None, "opus") == (None, None)
    assert "ATM_IDENTITY" not in sc_term_launch.os.environ
    assert "BEADS_ACTOR" not in sc_term_launch.os.environ


def test_apply_atm_env_prefix_without_team_clears_atm_vars():
    assert (
        sc_term_launch.apply_atm_env_prefix("claude", "wezterm", None, "alice")
        == "unset ATM_IDENTITY BEADS_ACTOR && claude"
    )
    assert (
        sc_term_launch.apply_atm_env_prefix("& 'claude'", "wt", None, "alice")
        == "Remove-Item Env:ATM_IDENTITY,Env:BEADS_ACTOR -ErrorAction SilentlyContinue; & 'claude'"
    )
