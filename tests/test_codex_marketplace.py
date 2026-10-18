"""Native packaging checks, plus opt-in real CLI tests in disposable profiles."""

import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_files_are_current():
    assert load_script("sync-codex-marketplace").sync(ROOT, check=True) == []


def test_catalog_paths_and_packaged_resources():
    catalog = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    assert catalog["name"] == "synaptic-canvas"
    assert {p["name"] for p in catalog["plugins"]} == {"sc-manage", "sc-gh-stack"}
    for entry in catalog["plugins"]:
        source = entry["source"]
        assert source["source"] == "local"
        assert source["path"].startswith("./")
        package = (ROOT / source["path"]).resolve()
        assert package.is_relative_to(ROOT)
        manifest = yaml.safe_load((package / "manifest.yaml").read_text())
        plugin = json.loads((package / "plugin.json").read_text())
        assert plugin["name"] == entry["name"] == manifest["name"]
        assert plugin["version"] == manifest["version"]
        assert plugin["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        for rel in manifest["artifacts"]["skills"]:
            assert (package / rel).is_file()
        assert entry["policy"]["installation"] == "AVAILABLE"
        assert "hooks" not in plugin and "mcpServers" not in plugin


def test_drift_detection_and_repair(tmp_path):
    sync = load_script("sync-codex-marketplace")
    for name in sync.PACKAGES:
        shutil.copytree(ROOT / "packages" / name, tmp_path / "packages" / name)
    assert sync.sync(tmp_path, check=False) == [".agents/plugins/marketplace.json"]
    path = tmp_path / "packages/sc-manage/manifest.yaml"
    data = yaml.safe_load(path.read_text())
    data["version"] = "9.9.9"
    path.write_text(yaml.safe_dump(data))
    changed = sync.sync(tmp_path, check=True)
    assert changed == ["packages/sc-manage/plugin.json"]
    assert json.loads((tmp_path / changed[0]).read_text())["version"] != "9.9.9"
    assert sync.sync(tmp_path, check=False) == changed
    assert sync.sync(tmp_path, check=True) == []


def test_version_bump_updates_both_hosts(tmp_path):
    package = tmp_path / "packages/sc-manage"
    shutil.copytree(ROOT / "packages/sc-manage", package)
    module = load_script("set-package-version")
    before = (package / "plugin.json").read_bytes()
    assert not module.update_package(tmp_path, "sc-manage", "9.9.9", dry_run=True).errors
    assert (package / "plugin.json").read_bytes() == before
    assert not module.update_package(tmp_path, "sc-manage", "9.9.9").errors
    for rel in (".claude-plugin/plugin.json", "plugin.json"):
        assert json.loads((package / rel).read_text())["version"] == "9.9.9"


def loaded_skills(env, cwd):
    """Query skill discovery only: no thread, turn, authentication or model call."""
    proc = subprocess.Popen(["codex", "app-server", "--stdio"], env=env, cwd=cwd,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    pending = b""

    def rpc(request):
        nonlocal pending
        proc.stdin.write(json.dumps(request).encode() + b"\n")
        proc.stdin.flush()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                message = json.loads(line)
                if message.get("id") == request["id"]:
                    assert "error" not in message, message
                    return message["result"]
            if selector.select(timeout=0.2):
                chunk = os.read(proc.stdout.fileno(), 65536)
                assert chunk, "app-server exited before answering"
                pending += chunk
        pytest.fail(f"app-server timeout for {request['method']}")

    try:
        rpc({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "sc-native-packaging-test", "version": "1.0.0"}}})
        proc.stdin.write(b'{"method":"initialized","params":{}}\n')
        proc.stdin.flush()
        return rpc({"id": 2, "method": "skills/list", "params": {
            "cwds": [str(cwd)], "forceReload": True}})
    finally:
        selector.close()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        proc.stdin.close()
        proc.stdout.close()


@pytest.mark.skipif(os.environ.get("SC_TEST_CODEX_CLI") != "1", reason="opt-in installed Codex CLI test")
@pytest.mark.parametrize("source_kind", ["local", "git"])
def test_native_cli_install_load_remove(tmp_path, source_kind):
    assert shutil.which("codex"), "Codex CLI is required for explicit native tests"
    source = str(ROOT)
    extra = []
    if source_kind == "git":
        source = os.environ.get("SC_TEST_CODEX_GIT_SOURCE")
        if not source:
            pytest.skip("Set SC_TEST_CODEX_GIT_SOURCE to test a pushed Git source")
        if os.environ.get("SC_TEST_CODEX_GIT_REF"):
            extra = ["--ref", os.environ["SC_TEST_CODEX_GIT_REF"]]
    profile = tmp_path / "codex"
    profile.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    env = dict(os.environ, CODEX_HOME=str(profile))
    env.pop("SC_REPO_PATH", None)

    def cli(*args):
        result = subprocess.run(["codex", "plugin", *args, "--json"], env=env, cwd=project,
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    assert cli("marketplace", "add", source, *extra)["marketplaceName"] == "synaptic-canvas"
    assert cli("marketplace", "add", source, *extra)["alreadyAdded"]
    available = cli("list", "--available", "--marketplace", "synaptic-canvas")["available"]
    assert {p["name"] for p in available} == {"sc-manage", "sc-gh-stack"}
    installed = {}
    for name in ("sc-manage", "sc-gh-stack"):
        result = cli("add", f"{name}@synaptic-canvas")
        package = Path(result["installedPath"])
        assert package.is_relative_to(profile.resolve())
        installed[name] = package
        assert (package / "plugin.json").is_file()
    state = cli("list", "--marketplace", "synaptic-canvas")["installed"]
    assert {p["name"] for p in state} == set(installed)
    assert all(p["installed"] and p["enabled"] for p in state)
    response = loaded_skills(env, project)
    # Walk the response to tolerate protocol envelopes, but require enabled
    # skills from the actual native cache, not pre-existing global copies.
    found = {}
    native_names = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("path") and str(value["path"]).startswith(str(profile.resolve() / "plugins/cache")):
                native_names.append(value.get("name"))
            name = value.get("name", "").split(":")[-1]
            if name in {"managing-sc-packages", "sc-gh-stack", "sc-gh-stack-view"}:
                path = Path(value["path"]).resolve()
                if path.is_relative_to(profile.resolve()):
                    found[name] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(response)
    assert set(found) == {"managing-sc-packages", "sc-gh-stack", "sc-gh-stack-view"}, response
    assert all(skill["enabled"] for skill in found.values())
    assert len(native_names) == 3, native_names  # no migrated Claude command duplicates
    stack_skill = Path(found["sc-gh-stack"]["path"])
    helper = stack_skill.parent / "../../scripts/gh_stack_view.py"
    result = subprocess.run([sys.executable, str(helper.resolve()), "--help"], env=env,
                            cwd=project, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert "--refresh-status" in result.stdout
    assert (installed["sc-manage"] / "scripts/sc_manage_dispatch.py").is_file()
    cli("remove", "sc-gh-stack@synaptic-canvas")
    assert {p["name"] for p in cli("list")["installed"]} == {"sc-manage"}
    cli("remove", "sc-manage@synaptic-canvas")
    assert cli("list")["installed"] == []
    cli("marketplace", "remove", "synaptic-canvas")
    assert not any(m["name"] == "synaptic-canvas" for m in cli("marketplace", "list")["marketplaces"])
