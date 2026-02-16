#!/usr/bin/env python3
"""Scan for hooks with relative paths (CWD fragility issues).

Finds hook commands that use relative paths instead of environment variables,
which can fail when Claude Code changes the current working directory.

Good patterns:
  - ${CLAUDE_PROJECT_DIR}/...
  - $CLAUDE_PROJECT_DIR/...
  - ${CLAUDE_PLUGIN_ROOT}/...
  - Inline Python with no file paths

Bad patterns:
  - ./scripts/...
  - .claude/scripts/...
  - scripts/... (bare relative)
"""

import json
import re
import sys
from pathlib import Path


def scan_json_file(filepath: Path) -> list[dict]:
    """Scan .json file for hook commands with relative paths."""
    issues = []
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return issues

    if not isinstance(data, dict):
        return issues

    def check_hooks(hooks_obj, path_context):
        if not isinstance(hooks_obj, dict):
            return
        for hook_type, hook_list in hooks_obj.items():
            if not isinstance(hook_list, list):
                continue
            for hook_entry in hook_list:
                if not isinstance(hook_entry, dict):
                    continue
                hook_cmds = hook_entry.get("hooks")
                if not isinstance(hook_cmds, list):
                    continue
                for cmd_obj in hook_cmds:
                    if not isinstance(cmd_obj, dict):
                        continue
                    command = cmd_obj.get("command", "")
                    if has_relative_path(command):
                        issues.append({
                            "file": str(filepath),
                            "hook_type": hook_type,
                            "command": command,
                            "context": path_context
                        })

    # Check if file has hooks section
    if "hooks" in data:
        check_hooks(data["hooks"], "root.hooks")

    return issues


def scan_markdown_file(filepath: Path) -> list[dict]:
    """Scan .md file for hook commands in frontmatter and code blocks."""
    issues = []
    try:
        content = filepath.read_text()
    except IOError:
        return issues

    # Extract frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) < 3:
            return issues
        _, frontmatter, _ = parts
        try:
            # Simple YAML parsing for hooks
            import yaml
            data = yaml.safe_load(frontmatter)
            if isinstance(data, dict) and "hooks" in data:
                def check_hooks(hooks_obj, path_context):
                    if not isinstance(hooks_obj, dict):
                        return
                    for hook_type, hook_list in hooks_obj.items():
                        if not isinstance(hook_list, list):
                            continue
                        for hook_entry in hook_list:
                            if not isinstance(hook_entry, dict):
                                continue
                            hook_cmds = hook_entry.get("hooks")
                            if not isinstance(hook_cmds, list):
                                continue
                            for cmd_obj in hook_cmds:
                                if not isinstance(cmd_obj, dict):
                                    continue
                                command = cmd_obj.get("command", "")
                                if has_relative_path(command):
                                    issues.append({
                                        "file": str(filepath),
                                        "hook_type": hook_type,
                                        "command": command,
                                        "context": f"frontmatter.{path_context}"
                                    })

                check_hooks(data["hooks"], "hooks")
        except Exception:
            pass

    return issues


def has_relative_path(command: str) -> bool:
    """Check if command uses relative paths instead of environment variables.

    Returns True if command has relative path issues (bad patterns).
    Returns False if command uses proper absolute paths or inline code (good patterns).
    """
    # Good patterns - allow these
    good_patterns = [
        r"\$\{CLAUDE_PROJECT_DIR\}",    # ${CLAUDE_PROJECT_DIR}
        r"\$CLAUDE_PROJECT_DIR",         # $CLAUDE_PROJECT_DIR
        r"\$\{CLAUDE_PLUGIN_ROOT\}",     # ${CLAUDE_PLUGIN_ROOT}
        r"\$CLAUDE_PLUGIN_ROOT",         # $CLAUDE_PLUGIN_ROOT
        r"python3 -c",                   # Inline Python
        r"python -c",
    ]

    if any(re.search(pattern, command) for pattern in good_patterns):
        return False

    # Bad patterns - flag these
    bad_patterns = [
        r"\.\/",                   # ./relative/path
        r"\.claude\/",             # .claude/path
        r"^\s*scripts\/",          # scripts/path (bare relative)
        r"\s+scripts\/",           # space + scripts/path
    ]

    return any(re.search(pattern, command) for pattern in bad_patterns)


def main():
    repo_root = Path(__file__).parent.parent
    issues = []

    # Scan JSON files
    for json_file in repo_root.rglob("*.json"):
        if ".git" in json_file.parts or ".venv" in json_file.parts:
            continue
        issues.extend(scan_json_file(json_file))

    # Scan Markdown files
    for md_file in repo_root.rglob("*.md"):
        if ".git" in md_file.parts:
            continue
        issues.extend(scan_markdown_file(md_file))

    if not issues:
        print("✅ No hook path issues found!")
        return 0

    print(f"\n❌ Found {len(issues)} hook(s) with relative path issues:\n")
    for issue in sorted(issues, key=lambda x: x["file"]):
        print(f"📁 {issue['file']}")
        print(f"   Hook Type: {issue['hook_type']}")
        print(f"   Command: {issue['command']}")
        print(f"   Fix: Use ${'{CLAUDE_PROJECT_DIR}'} or ${'{CLAUDE_PLUGIN_ROOT}'}")
        print()

    return 2


if __name__ == "__main__":
    sys.exit(main())
