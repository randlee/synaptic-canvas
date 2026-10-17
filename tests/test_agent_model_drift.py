"""The shared model table (packages/shared/scripts/agent_models.py) against the installed CLIs.

The two live tests run only where `codex` / `claude` are installed and answer; they skip
when there is no model data and fail only when real data shows the table is stale. The
failure message is the complete fix: exact edits, the sync command, the files to touch.

Every other test is static and deterministic (no processes, no clocks).
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import agent_model_discovery as discovery  # noqa: E402
from agent_model_discovery import LiveClaude, LiveCodex, agent_models  # noqa: E402

ModelSpec = agent_models.ModelSpec


# --- live: only on a machine with the CLI installed ---------------------------


def test_codex_models_are_current():
    live = discovery.codex_live()
    if live is None:
        pytest.skip("codex not installed or returned no model data")
    edits = discovery.codex_drift(live)
    assert not edits, discovery.fix_instructions("codex", live.version, edits, discovery.stale_ids("codex", edits))


def test_claude_models_are_current():
    live = discovery.claude_live()
    if live is None:
        pytest.skip("claude not installed or returned no model data")
    edits = discovery.claude_drift(live)
    assert not edits, discovery.fix_instructions("claude", live.version, edits, discovery.stale_ids("claude", edits))


# --- the table itself ------------------------------------------------------------


def current_codex() -> LiveCodex:
    """What codex would report if the table were exactly current."""
    return LiveCodex("test", agent_models.ALIASES["codex"]["codex"], dict(agent_models.MODELS["codex"]))


def current_claude() -> LiveClaude:
    return LiveClaude("test", dict(agent_models.ALIASES["claude"]), agent_models.CLAUDE_EFFORTS)


def test_table_is_self_consistent():
    assert discovery.codex_drift(current_codex()) == []
    assert discovery.claude_drift(current_claude()) == []
    for tool in agent_models.TOOLS:
        for alias, model_id in agent_models.ALIASES[tool].items():
            assert model_id in agent_models.MODELS[tool], f"{tool} alias {alias} -> unknown {model_id}"
        for spec in agent_models.MODELS[tool].values():
            assert spec.efforts and set(spec.efforts) <= set(agent_models.EFFORTS)
            assert spec.default_effort is None or spec.default_effort in spec.efforts
        assert agent_models.DEFAULT_ALIAS[tool] in agent_models.ALIASES[tool]


def test_every_package_copy_matches_the_canonical_file():
    canonical = discovery.CANONICAL.read_bytes()
    stale = [str(path.relative_to(REPO)) for _, path in discovery.consumers() if path.read_bytes() != canonical]
    assert not stale, f"Run `python3 scripts/sync-shared-scripts.py`; stale copies: {stale}"


def test_consumers_are_the_three_launchers():
    assert {name for name, _ in discovery.consumers()} == {"sc-codex", "sc-launch-term", "sc-launchpad"}


def test_resolution_and_flags():
    assert agent_models.resolve_model("codex").id == "gpt-6.1-sol"
    assert agent_models.resolve_model("claude").id == "claude-fable-5-1"
    assert agent_models.alias_for("codex", "gpt-6.1-sol") == "sol"  # never the `codex` catch-all
    spec = agent_models.resolve_model("codex", "luna")
    with pytest.raises(agent_models.ModelError, match="Supported: low, medium, high, xhigh, max"):
        agent_models.resolve_effort(spec, "ultra")
    with pytest.raises(agent_models.ModelError, match="Use an alias"):
        agent_models.resolve_model("claude", "gpt-6-astra")
    assert agent_models.model_flags("codex", spec, "max") == ["--model", "gpt-6-luna", "-c", "model_reasoning_effort=max"]
    assert agent_models.model_flags("claude", agent_models.resolve_model("claude", "opus"), None) == [
        "--model", "claude-opus-5-5"]
    assert agent_models.resolve_model("claude", "fable[1m]").id == "claude-fable-5-1[1m]"
    assert agent_models.alias_for("claude", "claude-fable-5-1[1m]") == "fable[1m]"
    with pytest.raises(agent_models.ModelError, match=r"append \[1m\]"):
        agent_models.resolve_model("claude", "claude-sonnet-4-6[1m]")
    with pytest.raises(agent_models.ModelError):
        agent_models.resolve_model("codex", "sol[1m]")


# --- drift detection on synthetic CLI data ------------------------------------------


def test_new_codex_model_moves_family_alias_default_and_codex_alias():
    live = current_codex()
    live.models["gpt-7-sol"] = ModelSpec("gpt-7-sol", agent_models.EFFORTS, "low")
    live = live._replace(default="gpt-7-sol")
    edits = discovery.codex_drift(live)
    assert edits == [
        'MODELS["codex"]: add  ModelSpec("gpt-7-sol", _up_to("ultra"), "low"),',
        'ALIASES["codex"]: change  "sol": "gpt-6.1-sol"  to  "sol": "gpt-7-sol"',
        'ALIASES["codex"]: change  "codex": "gpt-6.1-sol"  to  "codex": "gpt-7-sol"  (the codex CLI default)',
    ]
    assert discovery.stale_ids("codex", edits) == ["gpt-6.1-sol"]


def test_new_codex_family_becomes_the_default():
    live = current_codex()
    live.models["gpt-7-nova"] = ModelSpec("gpt-7-nova", ("low", "medium"), "medium")
    edits = discovery.codex_drift(live._replace(default="gpt-7-nova"))
    assert 'MODELS["codex"]: add  ModelSpec("gpt-7-nova", _up_to("medium"), "medium"),' in edits
    assert 'ALIASES["codex"]: add  "nova": "gpt-7-nova",' in edits
    assert any(e.startswith('DEFAULT_ALIAS: set  "codex": "nova"') for e in edits)


def test_removed_and_changed_codex_models():
    live = current_codex()
    del live.models["gpt-5.6-luna"]
    live.models["gpt-6-luna"] = ModelSpec("gpt-6-luna", agent_models.EFFORTS, "high")
    edits = discovery.codex_drift(live)
    assert edits == [
        'MODELS["codex"]: replace  ModelSpec("gpt-6-luna", _up_to("max"), "medium"),  with  '
        'ModelSpec("gpt-6-luna", _up_to("ultra"), "high"),',
        'MODELS["codex"]: remove  ModelSpec("gpt-5.6-luna", _up_to("max"), "medium"),  (codex no longer lists it)',
    ]
    assert discovery.stale_ids("codex", edits) == ["gpt-5.6-luna", "gpt-6-luna"]


def test_claude_alias_moving_to_a_new_model():
    live = current_claude()
    live.aliases["opus"] = "claude-opus-6-0"
    edits = discovery.claude_drift(live._replace(efforts=agent_models.CLAUDE_EFFORTS + ("ultra",)))
    assert edits == [
        'ALIASES["claude"]: change  "opus": "claude-opus-5-5"  to  "opus": "claude-opus-6-0"',
        'MODELS["claude"]: add "claude-opus-6-0" to the claude model id tuple',
        'MODELS["claude"]: remove "claude-opus-5-5" (no alias resolves to it any more)',
        "CLAUDE_EFFORTS: set to ('low', 'medium', 'high', 'xhigh', 'max', 'ultra') (claude --help --effort levels)",
    ]
    assert discovery.stale_ids("claude", edits) == ["claude-opus-5-5"]


def test_claude_alias_the_cli_did_not_resolve_is_not_drift():
    live = current_claude()
    del live.aliases["haiku"]  # e.g. not available on this account
    assert discovery.claude_drift(live) == []


def test_unknown_codex_effort_level_is_an_edit():
    live = current_codex()
    live.models["gpt-6-luna"] = ModelSpec("gpt-6-luna", agent_models.EFFORTS + ("hyper",), "medium")
    edits = discovery.codex_drift(live)
    assert edits[0].startswith("EFFORTS: add 'hyper'")


def test_claude_probe_env_drops_overrides_and_blocks_the_api(monkeypatch):
    for var in discovery.CLAUDE_OVERRIDE_VARS + ("ANTHROPIC_DEFAULT_FUTURE_MODEL",):
        monkeypatch.setenv(var, "claude-haiku-5-5[1m]")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("KEEP_ME", "1")
    env = discovery._claude_env()
    assert not [k for k in env if k in discovery.CLAUDE_OVERRIDE_VARS or k.startswith("ANTHROPIC_DEFAULT_")]
    assert env["ANTHROPIC_BASE_URL"] == discovery.NO_API and env["KEEP_ME"] == "1"


def test_claude_probe_ignores_settings_files():
    argv = discovery.claude_probe_argv("claude", "opus")
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--model") + 1] == "opus"


@pytest.mark.parametrize(
    ("model", "accepted"),
    [("claude-fable-5-1", True), ("claude-haiku-5-5", True), ("claude-haiku-5-5[1m]", False),
     ("us.anthropic.claude-opus-5-5-v1:0", False), ("claude-opus-5-5@20261001", False)],
)
def test_probe_accepts_only_first_party_ids(model, accepted):
    assert bool(discovery.CLAUDE_ID.match(model)) is accepted


def test_claude_help_effort_parse():
    help_text = "  --effort <level>   Reasoning effort (low, medium, high, xhigh, max)\n"
    assert discovery.claude_efforts(help_text) == agent_models.CLAUDE_EFFORTS
    assert discovery.claude_efforts("--effort <level>  (see docs, or `low`)") == ()
    assert discovery.claude_efforts("no such flag") == ()


def test_fix_instructions_name_every_file_to_touch():
    edits = ['ALIASES["codex"]: change  "terra": "gpt-5.6-terra"  to  "terra": "gpt-6-terra"']
    text = discovery.fix_instructions("codex", "codex-cli 9.9", edits, discovery.stale_ids("codex", edits))
    assert "codex-cli 9.9" in text
    assert "1. Edit packages/shared/scripts/agent_models.py" in text
    assert edits[0] in text
    assert "python3 scripts/sync-shared-scripts.py" in text
    for _, path in discovery.consumers():
        assert path.relative_to(REPO).as_posix() in text
    # Docs that name the outdated id are listed by path (CHANGELOGs and the copies are not).
    for doc in ("packages/sc-launch-term/commands/sc/terra.md", "packages/sc-launchpad/README.md"):
        assert f"     - {doc}" in text
    assert "CHANGELOG.md" not in text.split("3.")[1].split("4.")[0]
    assert "set-package-version.py" in text and "tests/test_agent_model_drift.py" in text
