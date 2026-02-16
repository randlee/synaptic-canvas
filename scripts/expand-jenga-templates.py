#!/usr/bin/env python3
"""Expand Jenga templates with automatic package-specific naming.

This script automates the Jenga template expansion process:
1. Detects package name from directory path
2. Copies template with package-specific filename
3. Replaces {{PACKAGE_NAME}} placeholder
4. Cleans up Jenga comments

Usage:
    # Expand templates for a package
    python3 scripts/expand-jenga-templates.py packages/sc-git-worktree

    # Expand for centralized hooks
    python3 scripts/expand-jenga-templates.py .claude/scripts --package-name hooks

    # Expand specific template only
    python3 scripts/expand-jenga-templates.py packages/sc-git-worktree --template logging
"""

import argparse
import re
import sys
from pathlib import Path


def detect_package_name(target_dir: Path) -> str:
    """Detect package name from directory path.

    Args:
        target_dir: Target directory (e.g., packages/sc-git-worktree)

    Returns:
        Package name (e.g., "sc-git-worktree")
    """
    # If in packages/ folder, use directory name
    if "packages" in target_dir.parts:
        pkg_idx = target_dir.parts.index("packages")
        if pkg_idx + 1 < len(target_dir.parts):
            return target_dir.parts[pkg_idx + 1]

    # Otherwise use last directory name
    return target_dir.name


def expand_template(
    template_path: Path,
    target_dir: Path,
    package_name: str,
    filename_suffix: str
) -> Path:
    """Expand a Jenga template to target directory.

    Args:
        template_path: Path to template file (e.g., templates/sc-logging.jenga.py)
        target_dir: Target directory (e.g., packages/sc-git-worktree/scripts)
        package_name: Package name for substitution
        filename_suffix: Suffix for output file (e.g., "logging" or "shared")

    Returns:
        Path to created file
    """
    # Read template
    content = template_path.read_text()

    # Replace {{PACKAGE_NAME}}
    content = content.replace("{{PACKAGE_NAME}}", package_name)

    # Clean up unused Jenga variable comments
    content = re.sub(r'\s*# \{\{EXTRA_IMPORTS\}\}[^\n]*\n', '\n', content)
    content = re.sub(r'\s*# \{\{EXTRA_FIELDS\}\}[^\n]*\n', '\n', content)
    content = re.sub(r'\s*\{\{EXTRA_IMPORTS\}\}[^\n]*\n', '\n', content)
    content = re.sub(r'\s*\{\{EXTRA_FIELDS\}\}[^\n]*\n', '\n', content)

    # Create output filename with package-specific naming
    # packages/sc-git-worktree → sc_git_worktree_logging.py
    safe_package_name = package_name.replace("-", "_")
    output_filename = f"{safe_package_name}_{filename_suffix}.py"
    output_path = target_dir / output_filename

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write expanded template
    output_path.write_text(content)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Expand Jenga templates with automatic package-specific naming"
    )
    parser.add_argument(
        "target_dir",
        type=Path,
        help="Target directory (e.g., packages/sc-git-worktree or .claude/scripts)"
    )
    parser.add_argument(
        "--package-name",
        help="Override package name detection (default: auto-detect from path)"
    )
    parser.add_argument(
        "--template",
        choices=["logging", "shared", "both"],
        default="both",
        help="Which template to expand (default: both)"
    )
    parser.add_argument(
        "--scripts-subdir",
        default="scripts",
        help="Scripts subdirectory name (default: scripts)"
    )

    args = parser.parse_args()

    # Resolve paths
    repo_root = Path(__file__).parent.parent
    target_dir = (repo_root / args.target_dir).resolve()

    # Detect or use provided package name
    if args.package_name:
        package_name = args.package_name
    else:
        package_name = detect_package_name(target_dir)

    # Determine scripts directory
    if target_dir.name == args.scripts_subdir:
        scripts_dir = target_dir
    else:
        scripts_dir = target_dir / args.scripts_subdir

    print(f"📦 Package: {package_name}")
    print(f"📁 Target:  {scripts_dir}")
    print()

    # Expand templates
    templates = {
        "logging": "sc-logging.jenga.py",
        "shared": "sc-shared.jenga.py"
    }

    expanded_files = []

    for template_type, template_file in templates.items():
        # Skip if specific template requested
        if args.template != "both" and args.template != template_type:
            continue

        template_path = repo_root / "templates" / template_file

        if not template_path.exists():
            print(f"⚠️  Template not found: {template_path}")
            continue

        try:
            output_path = expand_template(
                template_path,
                scripts_dir,
                package_name,
                template_type
            )
            expanded_files.append(output_path)
            print(f"✅ Created: {output_path.relative_to(repo_root)}")
        except Exception as e:
            print(f"❌ Failed to expand {template_file}: {e}", file=sys.stderr)
            return 1

    if not expanded_files:
        print("⚠️  No templates expanded")
        return 1

    print()
    print("🎉 Jenga template expansion complete!")
    print()
    print("Next steps:")
    print("1. Review the generated files")
    print("2. Add custom fields to LogEntry if needed ({{EXTRA_FIELDS}})")
    print("3. Update your scripts to import from the new modules:")
    print()

    for output_path in expanded_files:
        module_name = output_path.stem
        print(f"   from {module_name} import log_event, get_project_dir")

    return 0


if __name__ == "__main__":
    sys.exit(main())
