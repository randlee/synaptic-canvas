from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

import yaml


def test_manifest_artifacts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))

    for _, paths in manifest["artifacts"].items():
        for rel_path in paths:
            assert (root / rel_path).exists(), rel_path


def test_registry_paths_match_installed_layout() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = yaml.safe_load((root / "agents" / "registry.yaml").read_text(encoding="utf-8"))

    for info in registry["agents"].values():
        assert info["path"].startswith(".claude/agents/")

    for info in registry["skills"].values():
        assert info["path"].startswith(".claude/skills/")


def test_install_refactory_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

        script = root / "scripts" / "install_refactory.py"
        subprocess.run(
            ["python3", str(script), "--repo-root", str(repo), "--seed", "templates"],
            check=True,
            capture_output=True,
            text=True,
        )

        expected = [
            repo / ".startup" / "team-lead",
            repo / ".refactor" / ".gitignore",
            repo / ".refactor" / "docs" / "install-and-troubleshooting.md",
            repo / ".refactor" / "docs" / "rule-template.md",
            repo / ".refactor" / "profiles",
            repo / ".refactor" / "rules" / "rule-template.ttl",
            repo / ".refactor" / "scripts" / "session_start.py",
            repo / ".refactor" / "scripts" / "preflight.py",
            repo / ".refactor" / "scripts" / "rebuild_db.py",
            repo / ".refactor" / "scripts" / "sync_subset.py",
        ]

        for path in expected:
            assert path.exists(), str(path)


def test_sc_install_package_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    repo_root = root.parents[1]

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / ".claude"
        subprocess.run(
            [
                "python3",
                str(repo_root / "tools" / "sc-install.py"),
                "install",
                "sc-refactory",
                "--dest",
                str(dest),
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

        installed = [
            dest / "commands" / "sc-refactory-install.md",
            dest / "skills" / "refactor-lookup" / "SKILL.md",
            dest / "agents" / "refactor-lookup-agent.md",
            dest / "agents" / "registry.yaml",
            dest / "scripts" / "install_refactory.py",
            dest / ".claude-plugin" / "plugin.json",
            dest / "assets" / "startup-wrapper-template" / "team-lead.py",
        ]
        for path in installed:
            assert path.exists(), str(path)

        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                [
                    "python3",
                    str(dest / "scripts" / "install_refactory.py"),
                    "--repo-root",
                    str(repo),
                    "--seed",
                    "templates",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            runtime_paths = [
                repo / ".startup" / "team-lead",
                repo / ".refactor" / ".gitignore",
                repo / ".refactor" / "docs" / "install-and-troubleshooting.md",
                repo / ".refactor" / "docs" / "rule-template.md",
                repo / ".refactor" / "profiles",
                repo / ".refactor" / "rules" / "rule-template.ttl",
                repo / ".refactor" / "scripts" / "session_start.py",
                repo / ".refactor" / "scripts" / "preflight.py",
            ]
            for path in runtime_paths:
                assert path.exists(), str(path)


def test_sync_subset_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

        install_script = root / "scripts" / "install_refactory.py"
        subprocess.run(
            ["python3", str(install_script), "--repo-root", str(repo), "--seed", "empty"],
            check=True,
            capture_output=True,
            text=True,
        )

        bundle = Path(tmp) / "bundle"
        (bundle / "rules").mkdir(parents=True)
        (bundle / "docs").mkdir(parents=True)
        (bundle / "profiles").mkdir(parents=True)

        (bundle / "docs" / "focus-distance.md").write_text(
            "# Focus Distance\n",
            encoding="utf-8",
        )
        (bundle / "rules" / "focus-distance.ttl").write_text(
            """@prefix ref: <https://synaptic.canvas/refactor/> .

ref:focus-distance
    a ref:Rule ;
    ref:ruleId "focus-distance" ;
    ref:severity "warning" ;
    ref:ruleText "Use the shared focus-distance policy." ;
    ref:triggeredByType "FocusDistance" ;
    ref:hasFix [
        ref:path ".refactor/docs/focus-distance.md" ;
        ref:line 1
    ] .
""",
            encoding="utf-8",
        )
        (bundle / "profiles" / "sample.yaml").write_text(
            f"""name: sample
source_root: {bundle}
rule_ids:
  - focus-distance
""",
            encoding="utf-8",
        )

        sync_script = repo / ".refactor" / "scripts" / "sync_subset.py"
        subprocess.run(
            ["python3", str(sync_script), "--repo-root", str(repo), "--profile-file", str(bundle / "profiles" / "sample.yaml")],
            check=True,
            capture_output=True,
            text=True,
        )

        assert (repo / ".refactor" / "rules" / "focus-distance.ttl").exists()
        assert (repo / ".refactor" / "docs" / "focus-distance.md").exists()
        assert (repo / ".refactor" / "temp" / "sync_subset_manifest.json").exists()


if __name__ == "__main__":
    test_manifest_artifacts_exist()
    test_registry_paths_match_installed_layout()
    test_install_refactory_smoke()
    test_sc_install_package_smoke()
    test_sync_subset_smoke()
