#!/usr/bin/env python3
"""
Registry Validation Utility

Validates Synaptic Canvas package registry against the JSON Schema.
Can be used standalone or integrated into CI/CD pipelines.

Usage:
    python3 validate-registry.py                           # Validate using defaults
    python3 validate-registry.py --registry path/to/registry.json
    python3 validate-registry.py --schema path/to/schema.json
    python3 validate-registry.py --verbose
    python3 validate-registry.py --json                    # Output JSON for CI/CD
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any


def load_json_file(filepath: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load and parse a JSON file.

    Returns:
        Tuple of (parsed_json, error_message). If successful, error is None.
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"File not found: {filepath}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in {filepath}: {e}"
    except Exception as e:
        return None, f"Error reading {filepath}: {e}"


def validate_registry_structure(registry: Dict[str, Any],
                               schema: Dict[str, Any],
                               verbose: bool = False) -> Tuple[bool, List[str]]:
    """Validate registry structure against schema requirements.

    Performs basic validation checks without using external libraries.
    """
    errors = []

    # Check root level required fields
    required_root_fields = schema.get('required', [])
    for field in required_root_fields:
        if field not in registry:
            errors.append(f"Missing required root field: '{field}'")

    # Validate packages structure
    if 'packages' in registry:
        if not isinstance(registry['packages'], dict):
            errors.append("'packages' must be an object/dict")
        else:
            package_schema = schema['definitions']['package']
            required_pkg_fields = package_schema.get('required', [])

            for pkg_name, pkg_data in registry['packages'].items():
                # Validate package name format
                if not isinstance(pkg_name, str) or not _is_valid_package_name(pkg_name):
                    errors.append(f"Invalid package name: '{pkg_name}' (must be lowercase with hyphens)")

                # Check required package fields
                if not isinstance(pkg_data, dict):
                    errors.append(f"Package '{pkg_name}' must be an object")
                    continue

                for field in required_pkg_fields:
                    if field not in pkg_data:
                        errors.append(f"Package '{pkg_name}' missing required field: '{field}'")

                # Validate version format
                if 'version' in pkg_data and not _is_valid_semver(pkg_data['version']):
                    errors.append(f"Package '{pkg_name}': Invalid version format '{pkg_data['version']}'")

                # Validate status enum
                if 'status' in pkg_data:
                    valid_statuses = ['alpha', 'beta', 'stable', 'deprecated', 'archived']
                    if pkg_data['status'] not in valid_statuses:
                        errors.append(f"Package '{pkg_name}': Invalid status '{pkg_data['status']}'")

                # Validate tier range
                if 'tier' in pkg_data:
                    tier = pkg_data['tier']
                    if not isinstance(tier, int) or tier < 0 or tier > 5:
                        errors.append(f"Package '{pkg_name}': Tier must be integer 0-5, got {tier}")

                # Validate URLs
                if 'repo' in pkg_data and not pkg_data['repo'].startswith('https://github.com/'):
                    errors.append(f"Package '{pkg_name}': Invalid repo URL (must be https://github.com/...)")

                if 'readme' in pkg_data and not pkg_data['readme'].startswith('https://raw.githubusercontent.com/'):
                    errors.append(f"Package '{pkg_name}': Invalid readme URL (must be https://raw.githubusercontent.com/...)")

                if 'changelog' in pkg_data and not pkg_data['changelog'].startswith('https://raw.githubusercontent.com/'):
                    errors.append(f"Package '{pkg_name}': Invalid changelog URL (must be https://raw.githubusercontent.com/...)")

                # Validate tags
                if 'tags' in pkg_data:
                    if not isinstance(pkg_data['tags'], list):
                        errors.append(f"Package '{pkg_name}': 'tags' must be an array")
                    else:
                        if len(pkg_data['tags']) == 0:
                            errors.append(f"Package '{pkg_name}': 'tags' must have at least 1 item")
                        for tag in pkg_data['tags']:
                            if not _is_valid_tag_name(tag):
                                errors.append(f"Package '{pkg_name}': Invalid tag '{tag}' (must be lowercase with hyphens)")

                # Validate artifacts
                if 'artifacts' in pkg_data:
                    artifacts = pkg_data['artifacts']
                    if not isinstance(artifacts, dict):
                        errors.append(f"Package '{pkg_name}': 'artifacts' must be an object")
                    else:
                        for artifact_type in ['commands', 'skills', 'agents', 'scripts', 'schemas']:
                            if artifact_type not in artifacts:
                                errors.append(f"Package '{pkg_name}': Missing artifact type '{artifact_type}'")
                            elif not isinstance(artifacts[artifact_type], int) or artifacts[artifact_type] < 0:
                                errors.append(f"Package '{pkg_name}': Artifact '{artifact_type}' must be non-negative integer")

    # Validate metadata
    if 'metadata' in registry:
        metadata = registry['metadata']
        if not isinstance(metadata, dict):
            errors.append("'metadata' must be an object")
        else:
            # Validate version numbers
            if 'registryVersion' in metadata and not _is_valid_semver(metadata['registryVersion']):
                errors.append(f"Invalid registryVersion: '{metadata['registryVersion']}'")
            if 'schemaVersion' in metadata and not _is_valid_semver(metadata['schemaVersion']):
                errors.append(f"Invalid schemaVersion: '{metadata['schemaVersion']}'")

    # Validate root version
    if 'version' in registry and not _is_valid_semver(registry['version']):
        errors.append(f"Invalid root version: '{registry['version']}'")

    return len(errors) == 0, errors


def _is_valid_semver(version: str) -> bool:
    """Check if version string is valid semantic version."""
    import re
    # Basic semver pattern: X.Y.Z with optional pre-release and build
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d?)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    return bool(re.match(pattern, version))


def _is_valid_package_name(name: str) -> bool:
    """Check if package name follows naming conventions."""
    import re
    pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
    return bool(re.match(pattern, name))


def _is_valid_tag_name(tag: str) -> bool:
    """Check if tag follows naming conventions.

    Allows: lowercase letters, numbers, hyphens, dots, hash symbols
    Examples: 'automation', '.net', 'c#', 'asp.net', 'f#', 'ci-cd'
    """
    import re
    # Allow tags like '.net', 'c#', 'asp.net', etc.
    # Pattern: starts with alphanumeric, dot, or hash; can contain hyphens, dots, or hashes between parts
    pattern = r'^[.#a-z0-9]([a-z0-9.\-#]*[a-z0-9])?$'
    return bool(re.match(pattern, tag))


def try_validate_with_jsonschema(registry: Dict[str, Any],
                                 schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Try to validate using jsonschema library if available."""
    try:
        import jsonschema
        from jsonschema import validate, ValidationError

        try:
            validate(instance=registry, schema=schema)
            return True, None
        except ValidationError as e:
            path = ' -> '.join(str(p) for p in e.path) if e.path else 'root'
            return False, f"Validation error at {path}: {e.message}"
    except ImportError:
        # jsonschema not available
        return None, None


def generate_report(registry: Dict[str, Any],
                   errors: List[str],
                   json_output: bool = False,
                   verbose: bool = False) -> str:
    """Generate validation report."""

    if json_output:
        report = {
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'errors': errors,
            'registry': {
                'version': registry.get('version'),
                'packages': len(registry.get('packages', {})),
                'generated': registry.get('generated'),
            }
        }
        return json.dumps(report, indent=2)

    lines = []
    lines.append("=" * 70)
    lines.append("SYNAPTIC CANVAS REGISTRY VALIDATION REPORT")
    lines.append("=" * 70)

    # Summary
    lines.append(f"\nRegistry Version: {registry.get('version', 'unknown')}")
    lines.append(f"Generated: {registry.get('generated', 'unknown')}")
    lines.append(f"Packages: {len(registry.get('packages', {}))}")
    lines.append(f"Repository: {registry.get('repo', 'unknown')}")

    # Results
    lines.append("\n" + "-" * 70)
    if len(errors) == 0:
        lines.append("STATUS: VALID")
        lines.append("-" * 70)
        lines.append("\nAll validation checks passed!")

        if 'metadata' in registry:
            metadata = registry['metadata']
            lines.append(f"\nRegistry Statistics:")
            lines.append(f"  Total Packages: {metadata.get('totalPackages', 0)}")
            lines.append(f"  Total Commands: {metadata.get('totalCommands', 0)}")
            lines.append(f"  Total Skills: {metadata.get('totalSkills', 0)}")
            lines.append(f"  Total Agents: {metadata.get('totalAgents', 0)}")
            lines.append(f"  Total Scripts: {metadata.get('totalScripts', 0)}")

            if 'categories' in metadata:
                lines.append(f"\nCategories: {len(metadata['categories'])}")
                for cat, pkgs in metadata['categories'].items():
                    lines.append(f"  - {cat}: {len(pkgs)} package(s)")
    else:
        lines.append("STATUS: INVALID")
        lines.append("-" * 70)
        lines.append(f"\nFound {len(errors)} validation error(s):\n")
        for i, error in enumerate(errors, 1):
            lines.append(f"  {i}. {error}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Synaptic Canvas package registry against schema'
    )
    parser.add_argument(
        '--registry',
        default='docs/registries/nuget/registry.json',
        help='Path to registry.json file'
    )
    parser.add_argument(
        '--schema',
        default='docs/registries/nuget/registry.schema.json',
        help='Path to registry.schema.json file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output validation result as JSON'
    )

    args = parser.parse_args()

    # Load files
    schema, schema_error = load_json_file(args.schema)
    if schema_error:
        print(f"ERROR: {schema_error}", file=sys.stderr)
        return 1

    registry, registry_error = load_json_file(args.registry)
    if registry_error:
        print(f"ERROR: {registry_error}", file=sys.stderr)
        return 1

    # Perform validation
    is_valid, errors = validate_registry_structure(registry, schema, verbose=args.verbose)

    # Try to use jsonschema for more comprehensive validation
    if is_valid:
        jsonschema_valid, jsonschema_error = try_validate_with_jsonschema(registry, schema)
        if jsonschema_valid is not None:
            if not jsonschema_valid and jsonschema_error:
                is_valid = False
                errors.append(f"(jsonschema) {jsonschema_error}")
        elif args.verbose:
            print("Note: jsonschema library not available, using basic validation only",
                  file=sys.stderr)

    # Generate report
    report = generate_report(registry, errors, json_output=args.json, verbose=args.verbose)
    print(report)

    return 0 if is_valid else 1


if __name__ == '__main__':
    sys.exit(main())
