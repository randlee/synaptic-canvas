#!/usr/bin/env python3
"""
validate-script-references.py - Validate all script references in frontmatter and hooks

Usage:
  python3 scripts/validate-script-references.py [--package <name>] [--path <path>]

Options:
  --package NAME    Validate specific package only
  --path PATH       Validate specific file or directory
  --verbose         Show detailed validation output
  --json            Output results as JSON

Exit Codes:
  0: All references valid
  1: Invalid references found

Validates:
  1. Frontmatter script references (allowed-tools field)
  2. Hook script references in hooks.PreToolUse
  3. Pre-exec line (!python3 scripts/...) references in markdown body
  4. Scripts exist and are Python (.py)
  5. Scripts in correct package directory
  6. Same-package constraint (scripts must be in same package as source)
  7. Install path resolution (paths resolve correctly when installed to .claude/)
  8. Scripts have proper shebang (#!/usr/bin/env python3)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add test-packages/harness to path for Result types
sys.path.insert(0, str(Path(__file__).parent.parent / "test-packages" / "harness"))
from result import Result, Success, Failure, collect_results

try:
    import yaml  # type: ignore
except ImportError:
    print("Error: PyYAML not installed. Run: pip install PyYAML", file=sys.stderr)
    sys.exit(1)


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


@dataclass
class ScriptReferenceError:
    """Represents a script reference validation error."""

    message: str
    file_path: str
    script_reference: Optional[str] = None
    line_number: Optional[int] = None
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        """Format error as string."""
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        if self.script_reference:
            location += f" (script: {self.script_reference})"
        return f"{self.severity.upper()}: {location}: {self.message}"


# -----------------------------------------------------------------------------
# Script Reference Data
# -----------------------------------------------------------------------------


@dataclass
class ScriptReference:
    """Container for a script reference found in frontmatter/hooks/pre-exec lines."""

    source_file: str
    script_path: str
    reference_type: str  # "hook", "artifact", or "preexec"
    hook_type: Optional[str] = None  # e.g., "PreToolUse"
    line_number: Optional[int] = None  # Line number where reference was found


@dataclass
class ValidatedScriptReference:
    """Container for validated script reference."""

    reference: ScriptReference
    absolute_script_path: str
    has_shebang: bool
    shebang_line: Optional[str] = None


# -----------------------------------------------------------------------------
# Frontmatter Extraction
# -----------------------------------------------------------------------------


def extract_frontmatter(file_path: str) -> Result[Dict[str, Any], ScriptReferenceError]:
    """
    Extract YAML frontmatter from markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Success with frontmatter dict if valid, Failure with error otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return Failure(
            error=ScriptReferenceError(
                message=f"Failed to read file: {e}",
                file_path=file_path,
            )
        )

    # Extract frontmatter between --- markers
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        # No frontmatter is okay for some files
        return Success(value={}, warnings=["No frontmatter found"])

    raw_frontmatter = match.group(1)

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as e:
        return Failure(
            error=ScriptReferenceError(
                message=f"Invalid YAML in frontmatter: {e}",
                file_path=file_path,
            )
        )

    if not isinstance(frontmatter, dict):
        return Failure(
            error=ScriptReferenceError(
                message="Frontmatter must be a YAML object/dict",
                file_path=file_path,
            )
        )

    return Success(value=frontmatter, warnings=[])


# -----------------------------------------------------------------------------
# Script Reference Extraction
# -----------------------------------------------------------------------------


def extract_script_references_from_hooks(
    file_path: str, frontmatter: Dict[str, Any]
) -> List[ScriptReference]:
    """
    Extract script references from hooks in frontmatter.

    Args:
        file_path: Path to the file containing frontmatter
        frontmatter: Parsed frontmatter dict

    Returns:
        List of ScriptReference objects
    """
    references = []

    hooks = frontmatter.get("hooks", {})
    if not isinstance(hooks, dict):
        return references

    for hook_name, hook_config in hooks.items():
        if not isinstance(hook_config, list):
            continue

        for matcher_entry in hook_config:
            if not isinstance(matcher_entry, dict):
                continue

            hook_list = matcher_entry.get("hooks", [])
            if not isinstance(hook_list, list):
                continue

            for hook in hook_list:
                if not isinstance(hook, dict):
                    continue

                if hook.get("type") == "command":
                    command = hook.get("command", "")
                    # Extract script path from command
                    # Expected format: "python3 scripts/script_name.py"
                    script_match = re.search(r"scripts/([a-zA-Z0-9_\-]+\.py)", command)
                    if script_match:
                        script_path = f"scripts/{script_match.group(1)}"
                        references.append(
                            ScriptReference(
                                source_file=file_path,
                                script_path=script_path,
                                reference_type="hook",
                                hook_type=hook_name,
                            )
                        )

    return references


def extract_script_references_from_manifest(
    manifest_path: str,
) -> Result[List[ScriptReference], ScriptReferenceError]:
    """
    Extract script references from package manifest.

    Args:
        manifest_path: Path to manifest.yaml

    Returns:
        Success with list of ScriptReference objects, or Failure with error
    """
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    except Exception as e:
        return Failure(
            error=ScriptReferenceError(
                message=f"Failed to read manifest: {e}",
                file_path=manifest_path,
            )
        )

    if not isinstance(manifest, dict):
        return Failure(
            error=ScriptReferenceError(
                message="Manifest must be a YAML object/dict",
                file_path=manifest_path,
            )
        )

    references = []
    artifacts = manifest.get("artifacts", {})

    # Extract script artifacts
    scripts = artifacts.get("scripts", [])
    if isinstance(scripts, list):
        for script_path in scripts:
            if isinstance(script_path, str) and script_path.endswith(".py"):
                references.append(
                    ScriptReference(
                        source_file=manifest_path,
                        script_path=script_path,
                        reference_type="artifact",
                    )
                )

    # Also check agents list (may contain .py files)
    agents = artifacts.get("agents", [])
    if isinstance(agents, list):
        for agent_path in agents:
            if isinstance(agent_path, str) and agent_path.endswith(".py"):
                references.append(
                    ScriptReference(
                        source_file=manifest_path,
                        script_path=agent_path,
                        reference_type="artifact",
                    )
                )

    return Success(value=references, warnings=[])


def extract_preexec_script_references(
    file_path: str, content: str
) -> List[ScriptReference]:
    """
    Extract script references from ! pre-exec lines in markdown body.

    Patterns matched:
      - !python3 scripts/foo.py
      - !python3 ./scripts/bar.py $ARGUMENTS
      - !`python3 scripts/baz.py`
      - !`python3 ./scripts/qux.py $ARGUMENTS`
      - - Item: !`python3 scripts/inline.py` (inline in bullet points)

    Args:
        file_path: Path to the markdown file
        content: Full content of the markdown file

    Returns:
        List of ScriptReference objects
    """
    references = []

    # Pattern to match pre-exec with python3 scripts
    # Matches: !`python3 path` or !python3 path (anywhere in line)
    # The path may start with ./ and may have $ARGUMENTS or other suffixes
    preexec_pattern = r"!\`?python3\s+\.?/?([^\s\`\$]+)"

    for line_num, line in enumerate(content.split("\n"), start=1):
        match = re.search(preexec_pattern, line)
        if match:
            script_path = match.group(1)
            # Normalize path (remove leading ./)
            script_path = script_path.lstrip("./")
            # Only match Python files
            if script_path.endswith(".py"):
                references.append(
                    ScriptReference(
                        source_file=file_path,
                        script_path=script_path,
                        reference_type="preexec",
                        line_number=line_num,
                    )
                )

    return references


def extract_markdown_body(content: str) -> str:
    """
    Extract the body of a markdown file (content after frontmatter).

    Args:
        content: Full content of the markdown file

    Returns:
        The markdown body (after frontmatter), or full content if no frontmatter
    """
    # Pattern to match frontmatter
    pattern = r"^---\s*\n.*?\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        return content[match.end():]
    return content


# -----------------------------------------------------------------------------
# Same-Package Constraint Validation
# -----------------------------------------------------------------------------


def get_package_name_from_path(source_path: str) -> Optional[str]:
    """
    Extract package name from a source file path.

    Args:
        source_path: Path to the source file

    Returns:
        Package name (e.g., "sc-foo") if in packages/, None if not in a package
    """
    path = Path(source_path)
    parts = path.parts

    # Look for "packages" in path
    if "packages" in parts:
        pkg_idx = parts.index("packages")
        if pkg_idx + 1 < len(parts):
            return parts[pkg_idx + 1]

    return None


def validate_same_package_constraint(
    reference: ScriptReference, repo_root: str
) -> Result[bool, ScriptReferenceError]:
    """
    Validate that a script is in the same package as the source file.

    Scripts referenced in a package's markdown files MUST be inside that same package.
    Root-level .claude/ files can reference scripts/ or .claude/scripts/.

    Args:
        reference: Script reference to validate
        repo_root: Root directory of the repository

    Returns:
        Success if same-package constraint is satisfied, Failure otherwise
    """
    source_path = Path(reference.source_file)
    script_path_str = reference.script_path

    # Get package name from source file
    source_package = get_package_name_from_path(str(source_path))

    if source_package:
        # Source is in a package - script must be in same package
        package_root = Path(repo_root) / "packages" / source_package

        # Normalize the script path to check if it's in the same package
        # The script_path in a package context is relative to the package root
        # Check if the script path would resolve within the same package
        script_full_path = package_root / script_path_str

        try:
            script_full_path.resolve().relative_to(package_root.resolve())
        except ValueError:
            # Script is outside the package directory
            return Failure(
                error=ScriptReferenceError(
                    message=f"Cross-package reference not allowed: script '{script_path_str}' is outside package '{source_package}'",
                    file_path=reference.source_file,
                    script_reference=script_path_str,
                    line_number=reference.line_number,
                )
            )

    # Root-level files can reference scripts/ or .claude/scripts/
    # No constraint for root-level files
    return Success(value=True, warnings=[])


# -----------------------------------------------------------------------------
# Install Path Resolution Validation
# -----------------------------------------------------------------------------


def validate_install_path_resolution(
    reference: ScriptReference, package_root: str
) -> Result[bool, ScriptReferenceError]:
    """
    Validate that the script path would resolve correctly after installation.

    When packages install to .claude/, paths are mapped:
      - packages/sc-foo/scripts/bar.py -> .claude/scripts/bar.py
      - scripts/foo.py (in frontmatter) -> .claude/scripts/foo.py

    This validation ensures the source path exists in the package and would
    resolve correctly after installation.

    Args:
        reference: Script reference to validate
        package_root: Root directory of the package

    Returns:
        Success if path resolution is valid, Failure otherwise
    """
    script_path = reference.script_path
    package_path = Path(package_root)

    # Check if the script path exists in the package
    full_script_path = package_path / script_path

    if not full_script_path.exists():
        # Script doesn't exist - will be caught by validate_script_exists
        # But we can provide additional context about install paths
        return Success(
            value=True,
            warnings=[
                f"Script '{script_path}' not found in package. "
                f"After installation, it would be at '.claude/{script_path}'."
            ],
        )

    # Validate the script is in an expected location for installation
    # Scripts should be in scripts/ or agents/ subdirectories
    script_rel_path = Path(script_path)
    if script_rel_path.parts and script_rel_path.parts[0] not in ("scripts", "agents"):
        return Success(
            value=True,
            warnings=[
                f"Script '{script_path}' is not in a standard location (scripts/ or agents/). "
                f"Install path resolution may be unexpected."
            ],
        )

    return Success(value=True, warnings=[])


# -----------------------------------------------------------------------------
# Script Validation
# -----------------------------------------------------------------------------


def validate_script_exists(
    reference: ScriptReference, package_root: str
) -> Result[str, ScriptReferenceError]:
    """
    Validate that referenced script exists.

    Args:
        reference: Script reference to validate
        package_root: Root directory of the package

    Returns:
        Success with absolute path to script, or Failure with error
    """
    script_path = Path(package_root) / reference.script_path

    if not script_path.exists():
        return Failure(
            error=ScriptReferenceError(
                message=f"Referenced script does not exist: {reference.script_path}",
                file_path=reference.source_file,
                script_reference=reference.script_path,
            )
        )

    if not script_path.is_file():
        return Failure(
            error=ScriptReferenceError(
                message=f"Referenced script is not a file: {reference.script_path}",
                file_path=reference.source_file,
                script_reference=reference.script_path,
            )
        )

    return Success(value=str(script_path.resolve()), warnings=[])


def validate_script_is_python(
    script_path: str, reference: ScriptReference
) -> Result[bool, ScriptReferenceError]:
    """
    Validate that script is a Python file.

    Args:
        script_path: Absolute path to script
        reference: Script reference being validated

    Returns:
        Success if valid Python file, Failure otherwise
    """
    if not script_path.endswith(".py"):
        return Failure(
            error=ScriptReferenceError(
                message=f"Script must be a Python file (.py): {reference.script_path}",
                file_path=reference.source_file,
                script_reference=reference.script_path,
            )
        )

    return Success(value=True, warnings=[])


def validate_shebang(
    script_path: str, reference: ScriptReference
) -> Result[tuple[bool, Optional[str]], ScriptReferenceError]:
    """
    Validate that script has proper shebang.

    Args:
        script_path: Absolute path to script
        reference: Script reference being validated

    Returns:
        Success with (has_shebang, shebang_line), or Failure with error
    """
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
    except Exception as e:
        return Failure(
            error=ScriptReferenceError(
                message=f"Failed to read script: {e}",
                file_path=reference.source_file,
                script_reference=reference.script_path,
            )
        )

    if first_line.startswith("#!"):
        # Check for proper Python shebang
        if "python" not in first_line.lower():
            return Success(
                value=(True, first_line),
                warnings=[f"Shebang does not reference Python: {first_line}"],
            )
        return Success(value=(True, first_line), warnings=[])
    else:
        return Success(
            value=(False, None),
            warnings=[f"Script missing shebang: {reference.script_path}"],
        )


def validate_script_in_package_dir(
    reference: ScriptReference, package_root: str
) -> Result[bool, ScriptReferenceError]:
    """
    Validate that script is in correct package directory.

    Args:
        reference: Script reference to validate
        package_root: Root directory of the package

    Returns:
        Success if in correct directory, Failure otherwise
    """
    script_path = Path(package_root) / reference.script_path
    package_path = Path(package_root).resolve()

    try:
        # Ensure script is within package directory
        script_path.resolve().relative_to(package_path)
    except ValueError:
        return Failure(
            error=ScriptReferenceError(
                message=f"Script outside package directory: {reference.script_path}",
                file_path=reference.source_file,
                script_reference=reference.script_path,
            )
        )

    return Success(value=True, warnings=[])


def validate_script_reference(
    reference: ScriptReference, package_root: str, repo_root: Optional[str] = None
) -> Result[ValidatedScriptReference, ScriptReferenceError]:
    """
    Complete validation pipeline for a script reference.

    Args:
        reference: Script reference to validate
        package_root: Root directory of the package
        repo_root: Root directory of the repository (for same-package constraint)

    Returns:
        Success with ValidatedScriptReference, or Failure with error
    """
    warnings = []

    # Step 1: Check script exists
    exists_result = validate_script_exists(reference, package_root)
    if isinstance(exists_result, Failure):
        return exists_result
    script_path = exists_result.value

    # Step 2: Validate it's a Python file
    python_result = validate_script_is_python(script_path, reference)
    if isinstance(python_result, Failure):
        return python_result

    # Step 3: Validate in correct directory
    dir_result = validate_script_in_package_dir(reference, package_root)
    if isinstance(dir_result, Failure):
        return dir_result

    # Step 4: Validate same-package constraint (if repo_root provided)
    if repo_root:
        same_pkg_result = validate_same_package_constraint(reference, repo_root)
        if isinstance(same_pkg_result, Failure):
            return same_pkg_result
        warnings.extend(same_pkg_result.warnings if isinstance(same_pkg_result, Success) else [])

    # Step 5: Validate install path resolution
    install_result = validate_install_path_resolution(reference, package_root)
    if isinstance(install_result, Success):
        warnings.extend(install_result.warnings)

    # Step 6: Check shebang (warning only)
    shebang_result = validate_shebang(script_path, reference)
    if isinstance(shebang_result, Success):
        has_shebang, shebang_line = shebang_result.value
        warnings.extend(shebang_result.warnings)
    else:
        return shebang_result

    return Success(
        value=ValidatedScriptReference(
            reference=reference,
            absolute_script_path=script_path,
            has_shebang=has_shebang,
            shebang_line=shebang_line,
        ),
        warnings=warnings,
    )


# -----------------------------------------------------------------------------
# Package-Level Validation
# -----------------------------------------------------------------------------


def validate_package_scripts(
    package_path: str,
    repo_root: Optional[str] = None,
) -> Result[List[ValidatedScriptReference], List[ScriptReferenceError]]:
    """
    Validate all script references in a package.

    Args:
        package_path: Path to package directory
        repo_root: Root directory of the repository (for same-package constraint)

    Returns:
        Success with list of validated references, or Failure with errors
    """
    package_path_obj = Path(package_path)
    all_references = []
    warnings = []

    # 1. Check manifest for script artifacts
    manifest_path = package_path_obj / "manifest.yaml"
    if manifest_path.exists():
        manifest_result = extract_script_references_from_manifest(str(manifest_path))
        if isinstance(manifest_result, Success):
            all_references.extend(manifest_result.value)
            warnings.extend(manifest_result.warnings)
        else:
            return Failure(error=[manifest_result.error])

    # 2. Check all markdown files for hook references and pre-exec lines
    for md_file in package_path_obj.rglob("*.md"):
        if md_file.name.startswith("."):
            continue

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Extract hook references from frontmatter
        frontmatter_result = extract_frontmatter(str(md_file))
        if isinstance(frontmatter_result, Success):
            hook_refs = extract_script_references_from_hooks(
                str(md_file), frontmatter_result.value
            )
            all_references.extend(hook_refs)
            warnings.extend(frontmatter_result.warnings)

        # Extract pre-exec script references from markdown body
        body = extract_markdown_body(content)
        preexec_refs = extract_preexec_script_references(str(md_file), body)
        all_references.extend(preexec_refs)

    # 3. Validate each reference
    if not all_references:
        return Success(value=[], warnings=warnings + ["No script references found"])

    validation_results = [
        validate_script_reference(ref, str(package_path_obj), repo_root)
        for ref in all_references
    ]

    # 4. Collect results
    collected = collect_results(validation_results)

    if isinstance(collected, Failure):
        errors = collected.error.errors if hasattr(collected.error, "errors") else [collected.error]
        return Failure(error=errors)

    # Add package-level warnings
    return Success(
        value=collected.value,
        warnings=warnings + collected.warnings,
    )


# -----------------------------------------------------------------------------
# Repository-Level Validation
# -----------------------------------------------------------------------------


def find_packages(base_path: str, package_name: Optional[str] = None) -> List[str]:
    """
    Find all packages in the repository.

    Args:
        base_path: Root path of the repository
        package_name: Optional package name to filter by

    Returns:
        List of package directory paths
    """
    packages_dir = Path(base_path) / "packages"
    if not packages_dir.exists():
        return []

    if package_name:
        package_path = packages_dir / package_name
        return [str(package_path)] if package_path.exists() else []

    return [
        str(p)
        for p in packages_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]


def validate_all_packages(
    base_path: str,
    package_name: Optional[str] = None,
    specific_path: Optional[str] = None,
) -> Result[List[ValidatedScriptReference], List[ScriptReferenceError]]:
    """
    Validate all script references in the repository.

    Args:
        base_path: Root path of the repository
        package_name: Optional package name to filter by
        specific_path: Optional specific package path

    Returns:
        Success with list of validated references, or Failure with errors
    """
    if specific_path:
        specific = Path(specific_path)
        if not specific.exists():
            return Failure(
                error=[
                    ScriptReferenceError(
                        message=f"Path does not exist: {specific_path}",
                        file_path=specific_path,
                    )
                ]
            )
        packages = [str(specific)]
    else:
        packages = find_packages(base_path, package_name)

    if not packages:
        return Success(value=[], warnings=["No packages found"])

    # Validate each package (pass repo_root for same-package constraint)
    results = [validate_package_scripts(pkg, repo_root=base_path) for pkg in packages]

    # Flatten results
    all_validated = []
    all_warnings = []
    all_errors = []

    for result in results:
        if isinstance(result, Success):
            all_validated.extend(result.value)
            all_warnings.extend(result.warnings)
        else:
            all_errors.extend(result.error)

    if all_errors:
        return Failure(error=all_errors)

    return Success(value=all_validated, warnings=all_warnings)


# -----------------------------------------------------------------------------
# CLI Interface
# -----------------------------------------------------------------------------


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate script references in frontmatter and hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--package", help="Validate specific package only")
    parser.add_argument("--path", help="Validate specific package directory")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Determine repository root
    repo_root = Path(__file__).parent.parent
    if not (repo_root / "packages").exists():
        print(f"Error: packages directory not found in {repo_root}", file=sys.stderr)
        return 1

    # Run validation
    result = validate_all_packages(
        base_path=str(repo_root),
        package_name=args.package,
        specific_path=args.path,
    )

    # Output results
    if args.json:
        output_json(result)
    else:
        output_text(result, verbose=args.verbose)

    # Return exit code
    return 0 if isinstance(result, Success) else 1


def output_json(
    result: Result[List[ValidatedScriptReference], List[ScriptReferenceError]]
) -> None:
    """Output results as JSON."""
    if isinstance(result, Success):
        output = {
            "status": "success",
            "scripts_validated": len(result.value),
            "warnings": result.warnings,
        }
    else:
        output = {
            "status": "failure",
            "errors": [
                {
                    "file": err.file_path,
                    "message": err.message,
                    "script": err.script_reference,
                    "line": err.line_number,
                    "severity": err.severity,
                }
                for err in result.error
            ],
        }

    print(json.dumps(output, indent=2))


def output_text(
    result: Result[List[ValidatedScriptReference], List[ScriptReferenceError]],
    verbose: bool = False,
) -> None:
    """Output results as human-readable text."""
    if isinstance(result, Success):
        print(f"✓ Validated {len(result.value)} script references successfully")
        if result.warnings:
            for warning in result.warnings:
                print(f"  Warning: {warning}")
        if verbose and result.value:
            print("\nValidated scripts:")
            for validated in result.value:
                ref = validated.reference
                shebang_status = "✓" if validated.has_shebang else "✗"
                print(
                    f"  {shebang_status} {ref.script_path} (referenced in {Path(ref.source_file).name})"
                )
    else:
        print(f"✗ Validation failed with {len(result.error)} errors:", file=sys.stderr)
        for error in result.error:
            print(f"  {error}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
