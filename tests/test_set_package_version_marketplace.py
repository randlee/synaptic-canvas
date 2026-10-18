"""set-package-version.py: the registries' marketplace version comes from version.yaml.

The registries used to copy the version of the alphabetically first package, so a
marketplace bump never reached them. Each test runs a copy of the script against a
throwaway repo under tmp_path (the script finds its repo from its own location).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "set-package-version.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(root: Path) -> Path:
    (root / "scripts").mkdir()
    shutil.copy(SCRIPT, root / "scripts" / "set-package-version.py")
    write(root / "version.yaml", '# Marketplace Platform Version\nversion: "0.13.0"\n')
    # "a-first" sorts first and has a version unrelated to the marketplace.
    for name, version in (("a-first", "0.1.0"), ("b-second", "0.2.0")):
        write(
            root / "packages" / name / "manifest.yaml",
            yaml.safe_dump({"name": name, "version": version, "description": name}),
        )
    marketplace = {
        "name": "synaptic-canvas",
        "metadata": {"version": "0.13.0"},
        "plugins": [{"name": n, "source": f"./packages/{n}", "version": "0.0.0"} for n in ("a-first", "b-second")],
    }
    write(root / ".claude-plugin" / "marketplace.json", json.dumps(marketplace))
    write(root / ".claude-plugin" / "registry.json", json.dumps({"version": "0.13.0"}))
    write(
        root / "docs" / "registries" / "nuget" / "registry.json",
        json.dumps({"marketplace": {"version": "0.13.0"}, "packages": {}}),
    )
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "set-package-version.py"), *args],
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )


def registry_versions(root: Path) -> dict:
    load = lambda rel: json.loads((root / rel).read_text())
    return {
        "version.yaml": yaml.safe_load((root / "version.yaml").read_text())["version"],
        "marketplace.json": load(".claude-plugin/marketplace.json")["metadata"]["version"],
        "registry.json": load(".claude-plugin/registry.json")["version"],
        "nuget": load("docs/registries/nuget/registry.json")["marketplace"]["version"],
    }


def manifest_version(root: Path, name: str) -> str:
    return yaml.safe_load((root / "packages" / name / "manifest.yaml").read_text())["version"]


def test_marketplace_only_bump_reaches_every_registry(tmp_path):
    root = make_repo(tmp_path)
    result = run(root, "--marketplace", "0.14.0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert set(registry_versions(root).values()) == {"0.14.0"}
    assert manifest_version(root, "a-first") == "0.1.0"
    assert manifest_version(root, "b-second") == "0.2.0"
    assert (root / "version.yaml").read_text().startswith("# Marketplace Platform Version\n")


def test_package_bump_keeps_marketplace_version(tmp_path):
    root = make_repo(tmp_path)
    result = run(root, "a-first", "0.5.0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert manifest_version(root, "a-first") == "0.5.0"
    assert set(registry_versions(root).values()) == {"0.13.0"}


def test_marketplace_decrement_is_refused_without_force(tmp_path):
    root = make_repo(tmp_path)
    result = run(root, "--marketplace", "0.12.0")
    assert result.returncode == 1
    assert "decrement" in result.stdout
    assert registry_versions(root)["version.yaml"] == "0.13.0"
    assert run(root, "--marketplace", "0.12.0", "--force").returncode == 0
    assert set(registry_versions(root).values()) == {"0.12.0"}


def test_dry_run_changes_nothing(tmp_path):
    root = make_repo(tmp_path)
    before = registry_versions(root)
    assert run(root, "--marketplace", "0.14.0", "--dry-run").returncode == 0
    assert registry_versions(root) == before
