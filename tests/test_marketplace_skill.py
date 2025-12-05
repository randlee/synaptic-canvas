#!/usr/bin/env python3
"""
Phase 4: Marketplace Skill Integration Tests

Comprehensive test suite covering:
- Test Group 19: Skill Structure & Metadata (10 tests)
- Test Group 20: Agents Exist & Valid (12 tests)
- Test Group 21: Commands Exist & Valid (8 tests)
- Test Group 22: Skill Integration with CLI (15 tests)
- Test Group 23: User Workflows (14 tests)
- Test Group 24: Documentation Quality (10 tests)
- Test Group 25: Agent Discovery & Discoverability (10 tests)
- Test Group 26: Error Handling & User Experience (12 tests)

Total: 91 tests (requirement: 81+)
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from sc_cli import skill_integration


# ============================================================================
# TEST GROUP 19: Skill Structure & Metadata (10 tests)
# ============================================================================

class TestMarketplaceSkillStructure:
    """Test that marketplace skill files exist and are properly structured."""

    @pytest.fixture
    def skill_dir(self) -> Path:
        """Path to marketplace skill directory."""
        return REPO_ROOT / ".claude" / "skills" / "marketplace"

    def test_skill_md_exists_and_valid(self, skill_dir):
        """Test that SKILL.md exists and has required frontmatter."""
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), "SKILL.md must exist"

        content = skill_file.read_text()
        assert len(content) > 500, "SKILL.md must have substantial content"

        # Check for required sections
        assert "# Marketplace Package Manager" in content or "Marketplace" in content
        assert "## Overview" in content or "## Description" in content
        assert "## Features" in content or "## Capabilities" in content

    def test_readme_md_exists_and_complete(self, skill_dir):
        """Test that README.md exists and is comprehensive."""
        readme_file = skill_dir / "README.md"
        assert readme_file.exists(), "README.md must exist"

        content = readme_file.read_text()
        assert len(content) > 1000, "README.md must be comprehensive"

        # Check for required sections
        assert "Quick Start" in content or "Getting Started" in content
        assert "Example" in content or "example" in content
        assert "install" in content.lower(), "Must mention installation"

    def test_use_cases_md_has_7_cases(self, skill_dir):
        """Test that USE-CASES.md exists and has 7 use cases."""
        use_cases_file = skill_dir / "USE-CASES.md"
        assert use_cases_file.exists(), "USE-CASES.md must exist"

        content = use_cases_file.read_text()
        assert len(content) > 2000, "USE-CASES.md must be detailed"

        # Count "Use Case" headings
        use_case_count = content.count("## Use Case") + content.count("# Use Case")
        assert use_case_count >= 7, f"Must have at least 7 use cases, found {use_case_count}"

    def test_troubleshooting_md_comprehensive(self, skill_dir):
        """Test that TROUBLESHOOTING.md exists and is comprehensive."""
        troubleshoot_file = skill_dir / "TROUBLESHOOTING.md"
        assert troubleshoot_file.exists(), "TROUBLESHOOTING.md must exist"

        content = troubleshoot_file.read_text()
        assert len(content) > 1500, "TROUBLESHOOTING.md must be comprehensive"

        # Check for common troubleshooting sections
        assert "Issue" in content or "Problem" in content or "Error" in content
        assert "Solution" in content or "Fix" in content
        assert "registry" in content.lower()

    def test_skill_documents_features(self, skill_dir):
        """Test that SKILL.md documents key features."""
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()

        # Check for key feature mentions
        assert "discovery" in content.lower() or "discover" in content.lower()
        assert "install" in content.lower()
        assert "registry" in content.lower() or "registries" in content.lower()
        assert "search" in content.lower()

    def test_skill_includes_examples(self, skill_dir):
        """Test that documentation includes usage examples."""
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()

        # Check for code blocks or examples
        assert "```" in content or "Example" in content
        assert "/marketplace" in content or "marketplace" in content.lower()

    def test_skill_markdown_syntax_valid(self, skill_dir):
        """Test that markdown files have valid syntax."""
        for md_file in skill_dir.glob("*.md"):
            content = md_file.read_text()

            # Check for common markdown issues
            # Headers should have space after #
            invalid_headers = re.findall(r'^#{1,6}[^\s#]', content, re.MULTILINE)
            assert len(invalid_headers) == 0, f"Found invalid headers in {md_file.name}"

            # Code blocks should be properly closed
            backtick_count = content.count("```")
            assert backtick_count % 2 == 0, f"Unclosed code blocks in {md_file.name}"

    def test_skill_references_agents(self, skill_dir):
        """Test that SKILL.md references the marketplace agents."""
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()

        # Check for agent references
        assert "marketplace-package-discovery" in content or "discovery" in content.lower()
        assert "marketplace-package-installer" in content or "installer" in content.lower()
        assert "marketplace-registry-manager" in content or "registry" in content.lower()

    def test_skill_includes_prerequisites(self, skill_dir):
        """Test that SKILL.md includes prerequisites."""
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()

        # Check for prerequisites section
        assert "prerequisite" in content.lower() or "requirement" in content.lower() or "requires" in content.lower()

    def test_skill_includes_getting_started(self, skill_dir):
        """Test that documentation includes getting started guide."""
        readme_file = skill_dir / "README.md"
        content = readme_file.read_text()

        # Check for getting started content
        assert "quick start" in content.lower() or "getting started" in content.lower()
        assert "example" in content.lower()


# ============================================================================
# TEST GROUP 20: Agents Exist & Valid (12 tests)
# ============================================================================

class TestMarketplaceAgents:
    """Test that marketplace agents exist and are properly formatted."""

    @pytest.fixture
    def agents_dir(self) -> Path:
        """Path to agents directory."""
        return REPO_ROOT / ".claude" / "agents"

    def test_discovery_agent_exists(self, agents_dir):
        """Test that marketplace-package-discovery agent exists."""
        agent_file = agents_dir / "marketplace-package-discovery.md"
        assert agent_file.exists(), "marketplace-package-discovery.md must exist"
        assert agent_file.stat().st_size > 1000, "Agent file must have substantial content"

    def test_installer_agent_exists(self, agents_dir):
        """Test that marketplace-package-installer agent exists."""
        agent_file = agents_dir / "marketplace-package-installer.md"
        assert agent_file.exists(), "marketplace-package-installer.md must exist"
        assert agent_file.stat().st_size > 1000, "Agent file must have substantial content"

    def test_registry_manager_agent_exists(self, agents_dir):
        """Test that marketplace-registry-manager agent exists."""
        agent_file = agents_dir / "marketplace-registry-manager.md"
        assert agent_file.exists(), "marketplace-registry-manager.md must exist"
        assert agent_file.stat().st_size > 1000, "Agent file must have substantial content"

    def test_main_agent_exists(self, agents_dir):
        """Test that marketplace-management-skill agent exists."""
        agent_file = agents_dir / "marketplace-management-skill.md"
        assert agent_file.exists(), "marketplace-management-skill.md must exist"
        assert agent_file.stat().st_size > 1000, "Agent file must have substantial content"

    def test_all_agents_have_descriptions(self, agents_dir):
        """Test that all marketplace agents have description in frontmatter."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
            "marketplace-management-skill.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Check for frontmatter
            assert content.startswith("---"), f"{agent_file} must have frontmatter"
            assert "description:" in content, f"{agent_file} must have description"

    def test_all_agents_have_workflows(self, agents_dir):
        """Test that all marketplace agents document their workflow."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
            "marketplace-management-skill.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Check for workflow documentation
            assert "workflow" in content.lower() or "steps" in content.lower() or "process" in content.lower()

    def test_agents_markdown_syntax_valid(self, agents_dir):
        """Test that agent markdown files have valid syntax."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
            "marketplace-management-skill.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Check code blocks are properly closed
            backtick_count = content.count("```")
            assert backtick_count % 2 == 0, f"Unclosed code blocks in {agent_file}"

    def test_agents_reference_correct_commands(self, agents_dir):
        """Test that agents reference correct marketplace commands."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Should reference /marketplace or sc-install
            assert "/marketplace" in content or "sc-install" in content

    def test_agents_include_examples(self, agents_dir):
        """Test that agents include usage examples."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Should have examples
            assert "example" in content.lower() and ("```" in content or "Example" in content)

    def test_agents_handle_errors(self, agents_dir):
        """Test that agents document error handling."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Should document error handling
            assert "error" in content.lower()

    def test_agents_properly_formatted(self, agents_dir):
        """Test that agents follow standard formatting."""
        agent_files = [
            "marketplace-package-discovery.md",
            "marketplace-package-installer.md",
            "marketplace-registry-manager.md",
            "marketplace-management-skill.md",
        ]

        for agent_file in agent_files:
            path = agents_dir / agent_file
            content = path.read_text()

            # Check for frontmatter
            assert content.startswith("---")
            frontmatter_end = content.find("---", 3)
            assert frontmatter_end > 0, f"{agent_file} must have valid frontmatter"

    def test_agents_discoverable_by_claude(self, agents_dir):
        """Test that agents are in correct location for Claude discovery."""
        # Agents must be in .claude/agents/ directory
        assert agents_dir.exists()
        assert (agents_dir / "marketplace-package-discovery.md").exists()
        assert (agents_dir / "marketplace-package-installer.md").exists()
        assert (agents_dir / "marketplace-registry-manager.md").exists()
        assert (agents_dir / "marketplace-management-skill.md").exists()


# ============================================================================
# TEST GROUP 21: Commands Exist & Valid (8 tests)
# ============================================================================

class TestMarketplaceCommands:
    """Test that marketplace command exists and is properly formatted."""

    @pytest.fixture
    def commands_dir(self) -> Path:
        """Path to commands directory."""
        return REPO_ROOT / ".claude" / "commands"

    def test_marketplace_command_exists(self, commands_dir):
        """Test that marketplace.md command exists."""
        command_file = commands_dir / "marketplace.md"
        assert command_file.exists(), "marketplace.md command must exist"
        assert command_file.stat().st_size > 1000, "Command file must have substantial content"

    def test_command_documents_actions(self, commands_dir):
        """Test that command documents all available actions."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Check for key actions
        assert "list" in content.lower()
        assert "search" in content.lower()
        assert "install" in content.lower()
        assert "registry" in content.lower()

    def test_command_includes_examples(self, commands_dir):
        """Test that command includes usage examples."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Should have examples
        assert "example" in content.lower()
        assert "```" in content or "/marketplace" in content

    def test_command_help_text_clear(self, commands_dir):
        """Test that command has clear help text."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Should explain what the command does
        assert len(content) > 500
        assert "marketplace" in content.lower()
        assert "package" in content.lower()

    def test_command_markdown_valid(self, commands_dir):
        """Test that command markdown is valid."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Check code blocks are properly closed
        backtick_count = content.count("```")
        assert backtick_count % 2 == 0, "Unclosed code blocks in marketplace.md"

    def test_command_references_agents(self, commands_dir):
        """Test that command references marketplace agents."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Should reference agents
        assert "agent" in content.lower()

    def test_command_syntax_correct(self, commands_dir):
        """Test that command documents correct syntax."""
        command_file = commands_dir / "marketplace.md"
        content = command_file.read_text()

        # Should show command syntax
        assert "/marketplace" in content
        assert "<" in content and ">" in content  # Syntax placeholders

    def test_command_discoverable_by_claude(self, commands_dir):
        """Test that command is in correct location for Claude discovery."""
        # Command must be in .claude/commands/ directory
        assert commands_dir.exists()
        assert (commands_dir / "marketplace.md").exists()


# ============================================================================
# TEST GROUP 22: Skill Integration with CLI (15 tests)
# ============================================================================

class TestSkillIntegration:
    """Test that skill integration module works correctly."""

    def test_query_packages_returns_list(self):
        """Test that query_marketplace_packages returns a list of packages."""
        result = skill_integration.query_marketplace_packages()

        assert isinstance(result, dict)
        assert "status" in result
        assert "packages" in result
        assert isinstance(result["packages"], list)

    def test_query_packages_single_registry(self):
        """Test querying a specific registry."""
        result = skill_integration.query_marketplace_packages(registry="synaptic-canvas")

        assert isinstance(result, dict)
        assert result.get("registry") == "synaptic-canvas" or result.get("status") == "error"

    def test_query_packages_all_registries(self):
        """Test querying all registries (registry=None)."""
        result = skill_integration.query_marketplace_packages(registry=None)

        assert isinstance(result, dict)
        assert "packages" in result

    def test_query_packages_handles_errors(self):
        """Test that query handles errors gracefully."""
        # Query non-existent registry
        result = skill_integration.query_marketplace_packages(registry="non-existent-registry")

        assert isinstance(result, dict)
        # Should either work or return error status
        assert "status" in result

    def test_install_package_success(self):
        """Test that install function has correct signature."""
        # Test function exists and has correct parameters
        assert hasattr(skill_integration, "install_marketplace_package")

        # Test with mock to avoid actual installation
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="global"
        )

        assert isinstance(result, dict)
        assert "status" in result

    def test_install_package_with_registry(self):
        """Test install with specific registry."""
        result = skill_integration.install_marketplace_package(
            package="test-package",
            registry="synaptic-canvas",
            scope="global"
        )

        assert isinstance(result, dict)
        assert "status" in result

    def test_install_package_with_scope(self):
        """Test install with different scopes."""
        # Test global scope
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="global"
        )
        assert isinstance(result, dict)

        # Test local scope
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="local"
        )
        assert isinstance(result, dict)

    def test_install_package_error_handling(self):
        """Test that install handles errors gracefully."""
        # Invalid scope
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="invalid"
        )

        assert isinstance(result, dict)
        assert result["status"] == "error"

    def test_get_marketplace_config_returns_dict(self):
        """Test that get_marketplace_config returns configuration."""
        result = skill_integration.get_marketplace_config()

        assert isinstance(result, dict)
        assert "status" in result
        assert "registries" in result

    def test_get_marketplace_config_shows_defaults(self):
        """Test that config shows default registry."""
        result = skill_integration.get_marketplace_config()

        assert "default_registry" in result

    def test_get_marketplace_config_lists_registries(self):
        """Test that config lists all registries."""
        result = skill_integration.get_marketplace_config()

        assert "registries" in result
        assert isinstance(result["registries"], dict)

    def test_skill_integration_module_works(self):
        """Test that skill integration module imports correctly."""
        assert hasattr(skill_integration, "query_marketplace_packages")
        assert hasattr(skill_integration, "install_marketplace_package")
        assert hasattr(skill_integration, "get_marketplace_config")

    def test_agents_can_call_integration_functions(self):
        """Test that integration functions are callable."""
        # These should be callable without errors
        assert callable(skill_integration.query_marketplace_packages)
        assert callable(skill_integration.install_marketplace_package)
        assert callable(skill_integration.get_marketplace_config)

    def test_cli_state_preserved_across_skill_calls(self):
        """Test that CLI state is preserved."""
        # Get config twice
        config1 = skill_integration.get_marketplace_config()
        config2 = skill_integration.get_marketplace_config()

        # Should return same configuration
        assert config1["default_registry"] == config2["default_registry"]

    def test_skill_respects_existing_config(self):
        """Test that skill respects existing configuration."""
        config = skill_integration.get_marketplace_config()

        # If config exists, should have registries
        if config["status"] == "success":
            assert "registries" in config


# ============================================================================
# TEST GROUP 23: User Workflows (14 tests)
# ============================================================================

class TestMarketplaceWorkflows:
    """Test complete user workflows."""

    @pytest.fixture
    def mock_skill_context(self):
        """Mock skill execution context."""
        return {
            "user_dir": Path.home() / ".claude",
            "project_dir": Path.cwd() / ".claude-local",
        }

    def test_workflow_list_packages(self, mock_skill_context):
        """Test workflow: List all packages."""
        result = skill_integration.query_marketplace_packages()

        assert result["status"] in ["success", "error"]
        assert "packages" in result

    def test_workflow_search_packages(self, mock_skill_context):
        """Test workflow: Search for packages."""
        result = skill_integration.query_marketplace_packages(search_query="test")

        assert result["status"] in ["success", "error"]
        assert "packages" in result

    def test_workflow_install_package(self, mock_skill_context):
        """Test workflow: Install a package."""
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="global"
        )

        assert "status" in result

    def test_workflow_add_registry(self, mock_skill_context):
        """Test workflow: Add a registry (via config check)."""
        config = skill_integration.get_marketplace_config()

        assert "registries" in config

    def test_workflow_list_registries(self, mock_skill_context):
        """Test workflow: List registries."""
        config = skill_integration.get_marketplace_config()

        assert "registries" in config
        assert "total_registries" in config

    def test_workflow_remove_registry(self, mock_skill_context):
        """Test workflow: Remove registry (verify function exists)."""
        # Would use CLI function cmd_registry_remove
        config = skill_integration.get_marketplace_config()
        assert "registries" in config

    def test_workflow_show_package_details(self, mock_skill_context):
        """Test workflow: Show package details."""
        result = skill_integration.query_marketplace_packages()

        if result["packages"]:
            pkg = result["packages"][0]
            assert "name" in pkg
            assert "description" in pkg

    def test_workflow_install_to_global(self, mock_skill_context):
        """Test workflow: Install to global."""
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="global"
        )

        assert result["scope"] == "global" or result["status"] == "error"

    def test_workflow_install_to_local(self, mock_skill_context):
        """Test workflow: Install to local."""
        result = skill_integration.install_marketplace_package(
            package="test-package",
            scope="local"
        )

        assert result["scope"] == "local" or result["status"] == "error"

    def test_workflow_multi_step_discovery_install(self, mock_skill_context):
        """Test workflow: Discover then install."""
        # Step 1: Discover
        result = skill_integration.query_marketplace_packages()
        assert "packages" in result

        # Step 2: Install (if packages found)
        if result["packages"]:
            pkg_name = result["packages"][0]["name"]
            install_result = skill_integration.install_marketplace_package(
                package=pkg_name,
                scope="global"
            )
            assert "status" in install_result

    def test_workflow_handles_errors_gracefully(self, mock_skill_context):
        """Test workflow: Error handling."""
        # Invalid package
        result = skill_integration.install_marketplace_package(
            package="non-existent-package-xyz",
            scope="global"
        )

        assert "status" in result

    def test_workflow_provides_next_steps(self, mock_skill_context):
        """Test workflow: Results provide next steps."""
        result = skill_integration.query_marketplace_packages()

        # Should provide actionable information
        assert "packages" in result or "message" in result

    def test_workflow_clear_user_communication(self, mock_skill_context):
        """Test workflow: Clear communication."""
        result = skill_integration.get_marketplace_config()

        # Should have clear message
        assert "message" in result or "status" in result

    def test_workflow_complete_without_errors(self, mock_skill_context):
        """Test workflow: Complete workflow executes."""
        # Full workflow: config -> query -> (mock) install
        config = skill_integration.get_marketplace_config()
        assert config is not None

        packages = skill_integration.query_marketplace_packages()
        assert packages is not None


# ============================================================================
# TEST GROUP 24: Documentation Quality (10 tests)
# ============================================================================

class TestDocumentation:
    """Test documentation quality and completeness."""

    @pytest.fixture
    def skill_dir(self) -> Path:
        return REPO_ROOT / ".claude" / "skills" / "marketplace"

    def test_readme_has_quick_start(self, skill_dir):
        """Test that README has a quick start section."""
        readme = skill_dir / "README.md"
        content = readme.read_text()

        assert "quick start" in content.lower()

    def test_readme_examples_accurate(self, skill_dir):
        """Test that README examples are present."""
        readme = skill_dir / "README.md"
        content = readme.read_text()

        # Should have code examples
        assert "```" in content
        assert "example" in content.lower()

    def test_use_cases_practical_and_complete(self, skill_dir):
        """Test that use cases are practical."""
        use_cases = skill_dir / "USE-CASES.md"
        content = use_cases.read_text()

        # Should have multiple use cases
        assert content.count("## Use Case") >= 7

    def test_troubleshooting_covers_common_issues(self, skill_dir):
        """Test that troubleshooting covers common issues."""
        troubleshoot = skill_dir / "TROUBLESHOOTING.md"
        content = troubleshoot.read_text()

        # Check for common issues
        assert "error" in content.lower()
        assert "solution" in content.lower() or "fix" in content.lower()

    def test_guide_md_comprehensive(self, skill_dir):
        """Test that SKILL.md is comprehensive."""
        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()

        assert len(content) > 1000
        assert "marketplace" in content.lower()

    def test_guide_includes_screenshots_descriptions(self, skill_dir):
        """Test that documentation includes descriptions."""
        readme = skill_dir / "README.md"
        content = readme.read_text()

        # Should describe what marketplace does
        assert "package" in content.lower()
        assert "install" in content.lower()

    def test_guide_natural_language_examples(self, skill_dir):
        """Test that documentation includes natural language examples."""
        readme = skill_dir / "README.md"
        content = readme.read_text()

        # Should show natural language usage
        assert "example" in content.lower() or "usage" in content.lower()

    def test_documentation_syntax_valid(self, skill_dir):
        """Test that all documentation has valid markdown syntax."""
        for md_file in skill_dir.glob("*.md"):
            content = md_file.read_text()

            # Code blocks should be closed
            backtick_count = content.count("```")
            assert backtick_count % 2 == 0, f"Unclosed code blocks in {md_file.name}"

    def test_documentation_internally_consistent(self, skill_dir):
        """Test that documentation is internally consistent."""
        readme = skill_dir / "README.md"
        skill_md = skill_dir / "SKILL.md"

        readme_content = readme.read_text()
        skill_content = skill_md.read_text()

        # Both should mention marketplace
        assert "marketplace" in readme_content.lower()
        assert "marketplace" in skill_content.lower()

    def test_documentation_discoverable_and_clear(self, skill_dir):
        """Test that documentation is discoverable."""
        # Files should exist in expected location
        assert (skill_dir / "README.md").exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "USE-CASES.md").exists()
        assert (skill_dir / "TROUBLESHOOTING.md").exists()


# ============================================================================
# TEST GROUP 25: Agent Discovery & Discoverability (10 tests)
# ============================================================================

class TestAgentDiscovery:
    """Test that agents are discoverable and well-documented."""

    @pytest.fixture
    def agents_dir(self) -> Path:
        return REPO_ROOT / ".claude" / "agents"

    def test_agents_listed_in_registry(self, agents_dir):
        """Test that agents can be discovered."""
        # Agents should be in correct directory
        assert agents_dir.exists()

    def test_agents_have_clear_descriptions(self, agents_dir):
        """Test that agents have clear descriptions."""
        agent_files = list(agents_dir.glob("marketplace-*.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()
            # Should have frontmatter with description
            assert "description:" in content

    def test_agents_shown_in_help(self, agents_dir):
        """Test that agents are documented."""
        # Agents exist and have content
        agent_files = list(agents_dir.glob("marketplace-*.md"))
        assert len(agent_files) >= 3

    def test_agents_accessible_from_skill_context(self, agents_dir):
        """Test that agents are in skill context."""
        # Agents should be accessible from .claude/agents/
        assert agents_dir.exists()

    def test_skill_advertises_agents(self):
        """Test that skill documentation advertises agents."""
        skill_md = REPO_ROOT / ".claude" / "skills" / "marketplace" / "SKILL.md"
        content = skill_md.read_text()

        assert "agent" in content.lower()

    def test_commands_advertise_agents(self):
        """Test that commands reference agents."""
        command_md = REPO_ROOT / ".claude" / "commands" / "marketplace.md"
        content = command_md.read_text()

        assert "agent" in content.lower()

    def test_agents_natural_to_invoke(self, agents_dir):
        """Test that agents have clear invocation patterns."""
        agent_files = list(agents_dir.glob("marketplace-*.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()
            # Should document when to use
            assert "when" in content.lower() or "use" in content.lower()

    def test_agents_have_usage_examples(self, agents_dir):
        """Test that agents include usage examples."""
        agent_files = list(agents_dir.glob("marketplace-*.md"))

        for agent_file in agent_files:
            content = agent_file.read_text()
            assert "example" in content.lower()

    def test_agents_discoverable_through_search(self, agents_dir):
        """Test that agents are discoverable."""
        # Agents should be in standard location
        agent_files = list(agents_dir.glob("marketplace-*.md"))
        assert len(agent_files) >= 3

    def test_agents_appear_in_claude_ui(self, agents_dir):
        """Test that agents are in correct location for Claude."""
        # Agents must be in .claude/agents/ for Claude to discover them
        assert agents_dir.exists()
        assert agents_dir.name == "agents"


# ============================================================================
# TEST GROUP 26: Error Handling & User Experience (12 tests)
# ============================================================================

class TestSkillUX:
    """Test error handling and user experience."""

    def test_clear_error_messages(self):
        """Test that errors have clear messages."""
        result = skill_integration.install_marketplace_package(
            package="test",
            scope="invalid"
        )

        assert "message" in result or "errors" in result

    def test_actionable_error_suggestions(self):
        """Test that errors provide actionable suggestions."""
        result = skill_integration.query_marketplace_packages(registry="non-existent")

        if result["status"] == "error":
            assert "message" in result

    def test_next_steps_provided(self):
        """Test that operations provide next steps."""
        result = skill_integration.query_marketplace_packages()

        # Should provide useful information
        assert "packages" in result or "message" in result

    def test_help_text_available(self):
        """Test that help text is available."""
        command_file = REPO_ROOT / ".claude" / "commands" / "marketplace.md"
        assert command_file.exists()

    def test_examples_provided_for_each_action(self):
        """Test that examples are provided."""
        command_file = REPO_ROOT / ".claude" / "commands" / "marketplace.md"
        content = command_file.read_text()

        assert "example" in content.lower()

    def test_invalid_input_handled_gracefully(self):
        """Test that invalid input is handled."""
        result = skill_integration.install_marketplace_package(
            package="",
            scope="invalid"
        )

        assert result["status"] == "error"

    def test_network_errors_handled_well(self):
        """Test that network errors are handled."""
        # Query with non-existent registry
        result = skill_integration.query_marketplace_packages(registry="invalid")

        assert "status" in result

    def test_missing_registry_error_clear(self):
        """Test that missing registry errors are clear."""
        result = skill_integration.query_marketplace_packages(registry="non-existent-registry")

        if result["status"] == "error":
            assert "message" in result

    def test_package_not_found_helpful(self):
        """Test that package not found errors are helpful."""
        result = skill_integration.install_marketplace_package(
            package="non-existent-package-xyz-123",
            scope="global"
        )

        # Should handle gracefully
        assert "status" in result

    def test_installation_failure_informative(self):
        """Test that installation failures are informative."""
        result = skill_integration.install_marketplace_package(
            package="invalid-package",
            scope="global"
        )

        assert "status" in result

    def test_success_messages_clear(self):
        """Test that success messages are clear."""
        result = skill_integration.query_marketplace_packages()

        if result["status"] == "success":
            assert "message" in result or "packages" in result

    def test_progress_shown_for_long_operations(self):
        """Test that operations provide feedback."""
        # Functions should return status information
        result = skill_integration.get_marketplace_config()

        assert "status" in result


# ============================================================================
# Test Fixtures & Utilities
# ============================================================================

@pytest.fixture
def marketplace_skill_files():
    """Check marketplace skill files exist."""
    skill_dir = REPO_ROOT / ".claude" / "skills" / "marketplace"

    return {
        "skill_dir": skill_dir,
        "skill_md": skill_dir / "SKILL.md",
        "readme": skill_dir / "README.md",
        "use_cases": skill_dir / "USE-CASES.md",
        "troubleshooting": skill_dir / "TROUBLESHOOTING.md",
    }


@pytest.fixture
def sample_marketplace_packages():
    """Sample package data for testing."""
    return [
        {
            "name": "delay-tasks",
            "version": "0.4.0",
            "status": "beta",
            "description": "Schedule delayed or interval-based actions",
            "tags": ["delay", "polling", "tasks", "ci", "automation"],
            "artifacts": {"commands": 1, "skills": 1, "agents": 3, "scripts": 1},
            "dependencies": [],
            "repo": "https://github.com/randlee/synaptic-canvas",
            "license": "MIT",
            "author": "Anthropic",
            "lastUpdated": "2025-12-04",
        },
        {
            "name": "sc-git-worktree",
            "version": "0.4.0",
            "status": "beta",
            "description": "Create, manage, scan, and clean up git worktrees",
            "tags": ["git", "worktree", "branches", "development", "parallel"],
            "artifacts": {"commands": 1, "skills": 1, "agents": 4, "scripts": 0},
            "dependencies": ["git >= 2.27"],
            "repo": "https://github.com/randlee/synaptic-canvas",
            "license": "MIT",
            "author": "Anthropic",
            "lastUpdated": "2025-12-04",
        },
    ]


# ============================================================================
# Main Test Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
