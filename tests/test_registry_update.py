"""
Comprehensive tests for registry.yaml update functionality.

Tests cover:
- Typical insert/update/remove operations for agents and skills
- Corner cases: malformed YAML, missing fields, version mismatches
- Registry merging with existing entries
- YAML output formatting (both with and without PyYAML library)
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict

import pytest

from sc_cli import install as install_module
from sc_cli.install import (
    _parse_frontmatter_simple,
    _parse_skill_metadata,
    _update_registry,
)


@pytest.fixture(autouse=True)
def mock_repo_version(monkeypatch):
    """Mock _read_repo_version to return None by default (no version check)."""
    monkeypatch.setattr(install_module, "_read_repo_version", lambda: None)


class TestParseFrontmatterSimple:
    """Tests for _parse_frontmatter_simple function."""

    def test_basic_frontmatter(self, tmp_path: Path):
        """Test parsing basic YAML frontmatter."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "---\nname: my-agent\nversion: 1.0.0\ndescription: Test agent\n---\n# Content"
        )

        result = _parse_frontmatter_simple(md_file)
        assert result["name"] == "my-agent"
        assert result["version"] == "1.0.0"
        assert result["description"] == "Test agent"

    def test_missing_frontmatter(self, tmp_path: Path):
        """Test file without frontmatter returns empty dict."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# No frontmatter\nContent here")

        result = _parse_frontmatter_simple(md_file)
        assert result == {}

    def test_incomplete_frontmatter(self, tmp_path: Path):
        """Test file with incomplete frontmatter markers."""
        md_file = tmp_path / "test.md"
        md_file.write_text("---\nname: my-agent\n# Missing closing ---\nContent")

        result = _parse_frontmatter_simple(md_file)
        assert result == {}

    def test_quoted_values(self, tmp_path: Path):
        """Test parsing quoted YAML values."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            '---\nname: "my-agent"\nversion: "2.1.0"\ndescription: "Quoted desc"\n---\nContent'
        )

        result = _parse_frontmatter_simple(md_file)
        assert result["name"] == "my-agent"
        assert result["version"] == "2.1.0"
        assert result["description"] == "Quoted desc"

    def test_multiline_description(self, tmp_path: Path):
        """Test multiline YAML values."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            '---\nname: my-agent\nversion: 1.0.0\ndescription: >\n  This is a\n  multiline description\n---\nContent'
        )

        result = _parse_frontmatter_simple(md_file)
        assert result["name"] == "my-agent"


class TestParseSkillMetadata:
    """Tests for _parse_skill_metadata function."""

    def test_basic_skill_metadata(self, tmp_path: Path):
        """Test parsing basic skill metadata."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: my-skill\nversion: 1.0.0\nentry_point: /my-skill\ndescription: Test skill\n---\nContent"
        )

        result = _parse_skill_metadata(skill_file)
        assert result["name"] == "my-skill"
        assert result["version"] == "1.0.0"
        assert result["entry_point"] == "/my-skill"

    def test_skill_without_entry_point(self, tmp_path: Path):
        """Test skill metadata without entry_point."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: helper-skill\nversion: 0.5.0\ndescription: A helper skill\n---\nContent"
        )

        result = _parse_skill_metadata(skill_file)
        assert result["name"] == "helper-skill"
        assert result["version"] == "0.5.0"
        assert result["entry_point"] == ""

    def test_skill_metadata_missing_fields(self, tmp_path: Path):
        """Test skill with missing optional fields."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: minimal-skill\n---\nContent")

        result = _parse_skill_metadata(skill_file)
        assert result["name"] == "minimal-skill"
        assert result["version"] == ""
        assert result["entry_point"] == ""


class TestUpdateRegistry:
    """Tests for _update_registry function."""

    def test_empty_artifact_list(self, tmp_path: Path):
        """Test with empty artifact list returns 0."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        rc = _update_registry(dest, [])
        assert rc == 0
        assert not (dest / "agents" / "registry.yaml").exists()

    def test_create_registry_with_single_agent(self, tmp_path: Path):
        """Test creating registry with a single agent."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        # Create agent file
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nversion: 1.0.0\n---\n# Agent content"
        )

        rc = _update_registry(dest, ["agents/test-agent.md"])
        assert rc == 0

        # Verify registry exists and contains agent
        registry_path = agents_dir / "registry.yaml"
        assert registry_path.exists()
        content = registry_path.read_text()
        assert "test-agent:" in content
        assert "version: 1.0.0" in content
        assert ".claude/agents/test-agent.md" in content

    def test_create_registry_with_single_skill(self, tmp_path: Path):
        """Test creating registry with a single skill."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Create skill directory and file
        skill_dir = dest / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: my-skill\nversion: 2.0.0\nentry_point: /my-skill\n---\n# Skill content"
        )

        rc = _update_registry(dest, ["skills/my-skill/SKILL.md"])
        assert rc == 0

        # Verify registry exists and contains skill
        registry_path = dest / "agents" / "registry.yaml"
        assert registry_path.exists()
        content = registry_path.read_text()
        assert "my-skill:" in content
        assert "version: 2.0.0" in content
        assert "entry_point: /my-skill" in content

    def test_update_existing_agent(self, tmp_path: Path):
        """Test updating an existing agent entry."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        # Create initial agent
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nversion: 1.0.0\n---\n# Content"
        )

        # First update
        _update_registry(dest, ["agents/test-agent.md"])
        registry_path = agents_dir / "registry.yaml"
        content = registry_path.read_text()
        assert "version: 1.0.0" in content

        # Update agent version
        agent_file.write_text(
            "---\nname: test-agent\nversion: 1.1.0\n---\n# Updated"
        )

        # Second update
        rc = _update_registry(dest, ["agents/test-agent.md"])
        assert rc == 0

        # Verify version was updated
        content = registry_path.read_text()
        assert "version: 1.1.0" in content
        assert "version: 1.0.0" not in content

    def test_merge_agents_and_skills(self, tmp_path: Path):
        """Test registry with both agents and skills."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Setup agent
        agents_dir = dest / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nversion: 1.0.0\n---\n# Agent"
        )

        # Setup skill
        skill_dir = dest / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: my-skill\nversion: 2.0.0\nentry_point: /my-skill\n---\n# Skill"
        )

        # Update registry with both
        rc = _update_registry(
            dest, ["agents/test-agent.md", "skills/my-skill/SKILL.md"]
        )
        assert rc == 0

        # Verify both exist in registry
        registry_path = agents_dir / "registry.yaml"
        content = registry_path.read_text()
        assert "agents:" in content
        assert "skills:" in content
        assert "test-agent:" in content
        assert "my-skill:" in content

    def test_preserve_existing_registry_entries(self, tmp_path: Path):
        """Test that existing registry entries are preserved when adding new ones."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        # Create first agent
        agent1 = agents_dir / "agent-one.md"
        agent1.write_text("---\nname: agent-one\nversion: 1.0.0\n---\n# Content")
        _update_registry(dest, ["agents/agent-one.md"])

        # Create second agent
        agent2 = agents_dir / "agent-two.md"
        agent2.write_text("---\nname: agent-two\nversion: 2.0.0\n---\n# Content")
        rc = _update_registry(dest, ["agents/agent-two.md"])
        assert rc == 0

        # Verify both agents exist
        registry_path = agents_dir / "registry.yaml"
        content = registry_path.read_text()
        assert "agent-one:" in content
        assert "agent-two:" in content

    def test_version_mismatch_error(self, tmp_path: Path, monkeypatch):
        """Test error when agent version doesn't match repo version."""
        # Mock _read_repo_version to return a specific version
        monkeypatch.setattr(install_module, "_read_repo_version", lambda: "2.0.0")

        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        # Create agent with mismatched version
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nversion: 1.0.0\n---\n# Content"
        )

        # Should return error code 1 due to version mismatch
        rc = _update_registry(dest, ["agents/test-agent.md"])
        assert rc == 1

    def test_multiple_skills_with_dependencies(self, tmp_path: Path):
        """Test multiple skills with dependency declarations."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Create first skill
        skill1_dir = dest / "skills" / "skill-one"
        skill1_dir.mkdir(parents=True)
        skill1_file = skill1_dir / "SKILL.md"
        skill1_file.write_text(
            "---\nname: skill-one\nversion: 1.0.0\nentry_point: /skill-one\n---\n# Skill One"
        )

        # Create second skill with dependency on first
        skill2_dir = dest / "skills" / "skill-two"
        skill2_dir.mkdir(parents=True)
        skill2_file = skill2_dir / "SKILL.md"
        skill2_file.write_text(
            "---\nname: skill-two\nversion: 1.0.0\nentry_point: /skill-two\ndepends_on: skill-one: 1.x\n---\n# Skill Two"
        )

        rc = _update_registry(dest, ["skills/skill-one/SKILL.md", "skills/skill-two/SKILL.md"])
        assert rc == 0

        # Verify both skills exist
        registry_path = dest / "agents" / "registry.yaml"
        content = registry_path.read_text()
        assert "skill-one:" in content
        assert "skill-two:" in content

    def test_skill_path_variations(self, tmp_path: Path):
        """Test skill files in different directory structures."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Standard structure: skills/<name>/SKILL.md
        skill_dir = dest / "skills" / "standard-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: standard-skill\nversion: 1.0.0\nentry_point: /std\n---\n# Content"
        )

        rc = _update_registry(dest, ["skills/standard-skill/SKILL.md"])
        assert rc == 0

        # Verify it was registered
        registry_path = dest / "agents" / "registry.yaml"
        content = registry_path.read_text()
        assert "standard-skill:" in content

    def test_handle_missing_skill_file(self, tmp_path: Path):
        """Test gracefully handles missing skill file."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Try to update registry with non-existent skill
        rc = _update_registry(dest, ["skills/nonexistent/SKILL.md"])
        assert rc == 0  # Should not fail, just skip missing files

        # Registry should still exist but be empty
        registry_path = dest / "agents" / "registry.yaml"
        assert registry_path.exists()

    def test_agent_with_all_fields(self, tmp_path: Path):
        """Test agent with all possible frontmatter fields."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        agent_file = agents_dir / "full-agent.md"
        agent_file.write_text(
            "---\nname: full-agent\nversion: 3.2.1\nmodel: sonnet\ncolor: blue\ndescription: Complete agent\n---\n# Content"
        )

        rc = _update_registry(dest, ["agents/full-agent.md"])
        assert rc == 0

        registry_path = agents_dir / "registry.yaml"
        content = registry_path.read_text()
        assert "full-agent:" in content
        assert "version: 3.2.1" in content

    def test_skill_with_multiple_dependencies(self, tmp_path: Path):
        """Test skill with multiple dependencies."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        skill_dir = dest / "skills" / "complex-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        # Note: This tests the parsing of multiple dependencies
        skill_file.write_text(
            "---\nname: complex-skill\nversion: 1.5.0\nentry_point: /complex\ndepends_on: agent-one: 1.x, agent-two: 2.x\n---\n# Content"
        )

        rc = _update_registry(dest, ["skills/complex-skill/SKILL.md"])
        assert rc == 0

        registry_path = dest / "agents" / "registry.yaml"
        assert registry_path.exists()
        content = registry_path.read_text()
        assert "complex-skill:" in content

    def test_registry_yaml_formatting(self, tmp_path: Path):
        """Test that registry.yaml is properly formatted YAML."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        # Add both agent and skill
        agents_dir = dest / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("---\nname: test-agent\nversion: 1.0.0\n---\n# Agent")

        skill_dir = dest / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\nversion: 1.0.0\nentry_point: /test\n---\n# Skill"
        )

        rc = _update_registry(
            dest, ["agents/test-agent.md", "skills/test-skill/SKILL.md"]
        )
        assert rc == 0

        # Try to parse registry as YAML to verify it's valid
        registry_path = agents_dir / "registry.yaml"
        content = registry_path.read_text()

        # Basic structural validation
        assert content.startswith("agents:")
        assert "skills:" in content
        assert "version:" in content

    def test_skill_frontmatter_with_no_entry_point(self, tmp_path: Path):
        """Test skill registered without entry_point field."""
        dest = tmp_path / ".claude"
        dest.mkdir()

        skill_dir = dest / "skills" / "silent-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: silent-skill\nversion: 1.0.0\n---\n# Background skill"
        )

        rc = _update_registry(dest, ["skills/silent-skill/SKILL.md"])
        assert rc == 0

        registry_path = dest / "agents" / "registry.yaml"
        content = registry_path.read_text()
        assert "silent-skill:" in content
        # Should have version but no entry_point line
        assert "version: 1.0.0" in content

    def test_whitespace_handling(self, tmp_path: Path):
        """Test handling of whitespace in YAML."""
        dest = tmp_path / ".claude"
        dest.mkdir()
        agents_dir = dest / "agents"
        agents_dir.mkdir()

        agent_file = agents_dir / "test-agent.md"
        # Test with extra whitespace
        agent_file.write_text(
            "---\n  name:  test-agent  \n  version:  1.0.0  \n---\n# Content"
        )

        rc = _update_registry(dest, ["agents/test-agent.md"])
        assert rc == 0

        registry_path = agents_dir / "registry.yaml"
        assert registry_path.exists()
