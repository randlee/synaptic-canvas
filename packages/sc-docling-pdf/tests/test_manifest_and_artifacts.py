from __future__ import annotations

import json
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_manifest() -> dict:
    return yaml.safe_load((PACKAGE_ROOT / "manifest.yaml").read_text(encoding="utf-8"))


def _load_plugin() -> dict:
    return json.loads(
        (PACKAGE_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )


def test_manifest_declares_only_supported_artifact_categories() -> None:
    manifest = _load_manifest()
    artifacts = manifest["artifacts"]
    assert set(artifacts).issubset({"commands", "skills", "agents", "scripts", "assets"})


def test_manifest_artifacts_exist_on_disk() -> None:
    manifest = _load_manifest()
    for artifact_list in manifest["artifacts"].values():
        for rel_path in artifact_list:
            full_path = PACKAGE_ROOT / rel_path
            assert full_path.exists(), f"Missing artifact: {rel_path}"


def test_manifest_lists_all_skill_markdown_files() -> None:
    manifest = _load_manifest()
    declared = {
        Path(rel_path).as_posix()
        for rel_path in manifest["artifacts"]["skills"]
    }
    on_disk = {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in (PACKAGE_ROOT / "skills").rglob("*.md")
    }
    assert declared == on_disk


def test_plugin_skill_paths_match_manifest() -> None:
    manifest = _load_manifest()
    plugin = _load_plugin()
    assert plugin["skills"] == ["./skills/docling-pdf-extraction/SKILL.md"]
    manifest_skills = [
        rel_path
        for rel_path in manifest["artifacts"]["skills"]
        if rel_path.endswith("/SKILL.md")
    ]
    assert manifest_skills == ["skills/docling-pdf-extraction/SKILL.md"]


def test_manifest_plugin_metadata_is_consistent() -> None:
    manifest = _load_manifest()
    plugin = _load_plugin()

    assert plugin["name"] == manifest["name"]
    assert plugin["version"] == manifest["version"]
    assert plugin["description"].strip() == manifest["description"].strip()
    assert plugin["license"] == manifest["license"]
    assert plugin["author"]["name"] == manifest["author"]
    assert sorted(plugin["keywords"]) == sorted(manifest["tags"])


def test_manifest_requires_current_verified_docling_floor() -> None:
    manifest = _load_manifest()
    cli_requirements = manifest["requires"]["cli"]
    assert "python >= 3.10" in cli_requirements
    assert "docling >= 2.90.0" in cli_requirements
