"""
Comprehensive SC- Prefix Validation Test Suite

This test suite validates the Synaptic Canvas package sc- prefix refactoring across 4 packages.
Uses single source of truth (PACKAGES dict) to track package metadata, agents, commands, and skills.

On develop: Uses OLD names (without sc- prefix)
On feature branches: Edit PACKAGES dict to use NEW sc-prefixed names for each branch
"""

import json
import os
import re
from pathlib import Path
import pytest
import yaml


# ===========================
# SINGLE SOURCE OF TRUTH
# ===========================

PACKAGES = {
    'sc-delay-tasks': {
        'package_name': 'sc-delay-tasks',
        'agents': ['sc-delay-once', 'sc-delay-poll', 'sc-git-pr-check-delay'],
        'commands': ['sc-delay'],
        'skills': ['sc-delaying-tasks'],
        'version': '0.6.0',
        'path': 'packages/sc-delay-tasks',
        'artifact_counts': {'agents': 3, 'commands': 1, 'skills': 1}
    },
    'sc-git-worktree': {
        'package_name': 'sc-git-worktree',
        'agents': ['sc-git-worktree-create', 'sc-git-worktree-scan', 'sc-git-worktree-cleanup', 'sc-git-worktree-abort', 'sc-git-worktree-update'],
        'commands': ['sc-git-worktree'],
        'skills': ['sc-managing-worktrees'],
        'version': '0.6.0',
        'path': 'packages/sc-git-worktree',
        'artifact_counts': {'agents': 5, 'commands': 1, 'skills': 1}
    },
    'sc-repomix-nuget': {
        'package_name': 'sc-repomix-nuget',
        'agents': ['sc-repomix-nuget-analyze', 'sc-repomix-nuget-generate', 'sc-repomix-nuget-validate'],
        'commands': ['sc-repomix-nuget'],
        'skills': ['sc-generating-nuget-context'],
        'version': '0.6.0',
        'path': 'packages/sc-repomix-nuget',
        'artifact_counts': {'agents': 3, 'commands': 1, 'skills': 1}
    },
    'sc-manage': {
        'package_name': 'sc-manage',
        'agents': ['sc-packages-list', 'sc-package-install', 'sc-package-uninstall', 'sc-package-docs'],
        'commands': ['sc-manage'],
        'skills': ['sc-managing-sc-packages'],
        'version': '0.6.0',
        'path': 'packages/sc-manage',
        'artifact_counts': {'agents': 4, 'commands': 1, 'skills': 1}
    }
}


class TestPackageDiscoveryAndInstallation:
    """TEST 1: Validate package discovery and installation."""

    def test_packages_exist(self):
        """All packages should exist in their expected directories."""
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_path = Path(pkg_info['path'])
            assert pkg_path.exists(), f"Package directory {pkg_info['path']} does not exist"
            assert (pkg_path / 'manifest.yaml').exists(), \
                f"manifest.yaml missing in {pkg_info['path']}"

    def test_package_names_in_manifest(self):
        """Package names in manifest should match PACKAGES dict."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            assert manifest['name'] == pkg_info['package_name'], \
                f"Package name mismatch in {pkg_info['path']}: " \
                f"expected {pkg_info['package_name']}, got {manifest['name']}"

    def test_package_versions_in_manifest(self):
        """Package versions should match PACKAGES dict."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            assert manifest['version'] == pkg_info['version'], \
                f"Version mismatch in {pkg_info['path']}: " \
                f"expected {pkg_info['version']}, got {manifest['version']}"

    def test_agents_files_exist(self):
        """All agent files listed in manifest should exist."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            agent_files = manifest.get('artifacts', {}).get('agents', [])
            for agent_file in agent_files:
                agent_path = Path(pkg_info['path']) / agent_file
                assert agent_path.exists(), \
                    f"Agent file missing: {agent_path}"

    def test_command_files_exist(self):
        """All command files listed in manifest should exist."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            command_files = manifest.get('artifacts', {}).get('commands', [])
            for command_file in command_files:
                command_path = Path(pkg_info['path']) / command_file
                assert command_path.exists(), \
                    f"Command file missing: {command_path}"

    def test_skill_files_exist(self):
        """All skill files listed in manifest should exist."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            skill_files = manifest.get('artifacts', {}).get('skills', [])
            for skill_file in skill_files:
                skill_path = Path(pkg_info['path']) / skill_file
                assert skill_path.exists(), \
                    f"Skill file missing: {skill_path}"


class TestRegistryValidation:
    """TEST 2: Validate docs/registries/nuget/registry.json."""

    def test_registry_file_exists(self):
        """Registry file should exist."""
        registry_path = Path('docs/registries/nuget/registry.json')
        assert registry_path.exists(), "docs/registries/nuget/registry.json does not exist"

    def test_registry_parses_as_json(self):
        """Registry should be valid JSON."""
        registry_path = Path('docs/registries/nuget/registry.json')
        with open(registry_path) as f:
            registry = json.load(f)
        assert isinstance(registry, dict), "Registry should be a JSON object"

    def test_all_packages_in_registry(self):
        """All packages from PACKAGES dict should be in registry."""
        registry_path = Path('docs/registries/nuget/registry.json')
        with open(registry_path) as f:
            registry = json.load(f)

        packages = registry.get('packages', {})
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_name = pkg_info['package_name']
            assert pkg_name in packages, \
                f"Package {pkg_name} not found in registry"

    def test_package_versions_in_registry(self):
        """Package versions in registry should match PACKAGES dict."""
        registry_path = Path('docs/registries/nuget/registry.json')
        with open(registry_path) as f:
            registry = json.load(f)

        packages = registry.get('packages', {})
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_name = pkg_info['package_name']
            expected_version = pkg_info['version']
            actual_version = packages[pkg_name].get('version')
            assert actual_version == expected_version, \
                f"Version mismatch for {pkg_name}: " \
                f"expected {expected_version}, got {actual_version}"

    def test_package_paths_in_registry(self):
        """Package paths in registry should match expected structure."""
        registry_path = Path('docs/registries/nuget/registry.json')
        with open(registry_path) as f:
            registry = json.load(f)

        packages = registry.get('packages', {})
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_name = pkg_info['package_name']
            expected_path = pkg_info['path']
            actual_path = packages[pkg_name].get('path')
            assert actual_path == expected_path, \
                f"Path mismatch for {pkg_name}: " \
                f"expected {expected_path}, got {actual_path}"


class TestManifestValidation:
    """TEST 3: Validate manifest.yaml files."""

    def test_manifest_artifacts_in_registry(self):
        """Artifact counts in registry should match PACKAGES dict."""
        registry_path = Path('docs/registries/nuget/registry.json')
        with open(registry_path) as f:
            registry = json.load(f)

        packages = registry.get('packages', {})
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_name = pkg_info['package_name']
            expected_counts = pkg_info['artifact_counts']

            reg_pkg = packages[pkg_name]
            actual_counts = reg_pkg.get('artifacts', {})

            for artifact_type in ['agents', 'commands', 'skills']:
                expected = expected_counts.get(artifact_type, 0)
                actual = actual_counts.get(artifact_type, 0)
                assert actual == expected, \
                    f"{pkg_name}: expected {expected} {artifact_type}, got {actual}"


class TestCrossReferenceValidation:
    """TEST 5: Search for old package names and stray references."""

    def test_no_old_package_name_references(self):
        """Should not find old package names without sc- prefix in wrong contexts."""
        # Define old package names that should not appear (except in changelog/historical sections)
        old_names = ['delay-tasks', 'git-worktree', 'repomix-nuget']

        # Allowlist: patterns that indicate historical/acceptable usage
        allowlist_patterns = [
            'CHANGELOG',  # Historical changelogs can reference old names
            'migration',  # Migration documentation
            'renamed from',  # Explicit rename documentation
            'previously called',  # Historical reference
            'formerly known as',  # Historical reference
            '## [0.4.0]',  # Old version sections in changelogs
            'v0.4.0',  # Old version references
        ]

        # Files to check
        files_to_check = [
            'README.md',
            'docs/registries/nuget/registry.schema.json',
            'scripts/security-scan.sh',
            'src/sc_cli/skill_integration.py',
            'packages/sc-delay-tasks/TROUBLESHOOTING.md',
            'packages/sc-manage/agents/sc-package-install.md',
            'packages/sc-manage/agents/sc-package-docs.md',
            'packages/sc-manage/agents/sc-packages-list.md',
        ]

        violations = []

        for file_path in files_to_check:
            full_path = Path(file_path)
            if not full_path.exists():
                continue

            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Skip lines matching allowlist patterns
                if any(pattern in line for pattern in allowlist_patterns):
                    continue

                # Check for old package names
                for old_name in old_names:
                    if old_name in line:
                        # Check if it's a reference that should use sc- prefix
                        # Allow: packages/delay-tasks/ directory references (but they're actually packages/sc-delay-tasks/)
                        if f'packages/{old_name}' in line:
                            continue  # Directory structure references are OK
                        if f'/{old_name}/' in line:
                            continue  # Path references are OK
                        # Allow: already prefixed with sc- (e.g., sc-delay-tasks contains delay-tasks)
                        if f'sc-{old_name}' in line:
                            continue  # sc-prefixed references are OK
                        # Allow: in examples/docstrings showing the package name
                        if '"' + old_name + '"' in line or "'" + old_name + "'" in line:
                            # Check if it's in a code example or docstring
                            if '>>>' in line or 'install_marketplace_package' in line:
                                continue  # Code examples are OK if they're showing old usage

                        violations.append(
                            f"{file_path}:{line_num}: Found '{old_name}' (should be 'sc-{old_name}'): {line.strip()[:80]}"
                        )

        # Assert no violations found
        if violations:
            error_msg = "Found old package name references that should use sc- prefix:\n" + "\n".join(violations)
            pytest.fail(error_msg)

    def test_no_double_sc_prefixes(self):
        """Should not find any 'sc-sc-' double prefixes."""
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_path = Path(pkg_info['path'])

            # Check all .md files for sc-sc- patterns
            for md_file in pkg_path.rglob('*.md'):
                with open(md_file, encoding='utf-8') as f:
                    content = f.read()
                assert 'sc-sc-' not in content, \
                    f"Found double prefix 'sc-sc-' in {md_file}"

    def test_no_stray_yaml_references(self):
        """Should not find malformed agent/command/skill references in YAML."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            with open(manifest_path) as f:
                content = f.read()

            # Look for malformed prefixes
            assert 'sc-sc-' not in content, \
                f"Found double prefix in {manifest_path}"
            assert '{{' not in content or '}}' not in content, \
                f"Found unexpanded template variables in {manifest_path}"


class TestTokenExpansion:
    """TEST 6: Validate token expansion for Tier 1 packages."""

    def test_no_unexpanded_tokens_in_packages(self):
        """Should not find unexpanded {{REPO_NAME}} tokens in package files."""
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_path = Path(pkg_info['path'])

            # Check manifest for unexpanded tokens
            manifest_path = pkg_path / 'manifest.yaml'
            with open(manifest_path, encoding='utf-8') as f:
                content = f.read()
            assert '{{REPO_NAME}}' not in content, \
                f"Found unexpanded {{{{REPO_NAME}}}} token in {manifest_path}"

            # Check all .md files for unexpanded tokens
            for md_file in pkg_path.rglob('*.md'):
                with open(md_file, encoding='utf-8') as f:
                    content = f.read()
                # Note: Some unexpanded tokens may be expected in documentation/examples
                # Only fail if they appear in actual directives
                if 'include:' in content or 'execute:' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if '{{REPO_NAME}}' in line and ('include:' in line or 'execute:' in line):
                            pytest.fail(
                                f"Found unexpanded {{{{REPO_NAME}}}} in directive at {md_file}:{i+1}: {line}"
                            )


class TestSmokeSuite:
    """TEST 7: Smoke test - verify basic functionality."""

    def test_all_packages_discoverable(self):
        """All packages should be discoverable in their expected locations."""
        for pkg_key, pkg_info in PACKAGES.items():
            pkg_path = Path(pkg_info['path'])
            assert pkg_path.is_dir(), f"Package {pkg_info['package_name']} not found at {pkg_path}"

    def test_no_syntax_errors_in_manifests(self):
        """All manifest.yaml files should parse without errors."""
        for pkg_key, pkg_info in PACKAGES.items():
            manifest_path = Path(pkg_info['path']) / 'manifest.yaml'
            try:
                with open(manifest_path) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML syntax error in {manifest_path}: {e}")

    def test_registry_consistency(self):
        """Registry should be consistent with package structure."""
        registry_path = Path('docs/registries/nuget/registry.json')
        if not registry_path.exists():
            pytest.skip("Registry file not found")

        with open(registry_path) as f:
            registry = json.load(f)

        packages = registry.get('packages', {})
        # Verify all entries have required fields
        for pkg_name, pkg_info in packages.items():
            assert 'version' in pkg_info, f"Missing version for {pkg_name}"
            assert 'path' in pkg_info, f"Missing path for {pkg_name}"
            assert Path(pkg_info['path']).exists(), \
                f"Package path {pkg_info['path']} does not exist for {pkg_name}"
