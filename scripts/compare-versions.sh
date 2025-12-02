#!/bin/bash
#
# compare-versions.sh - Compare version numbers across packages
#
# Usage:
#   ./scripts/compare-versions.sh [--by-package] [--mismatches] [--verbose]
#
# Options:
#   --by-package   Show versions grouped by package (default)
#   --mismatches   Only show packages with version mismatches
#   --verbose      Show all artifact versions individually
#   --json         Output as JSON
#
# Exit codes:
# 0 - All versions consistent
# 1 - Mismatches found

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BY_PACKAGE=0
SHOW_MISMATCHES_ONLY=0
VERBOSE=0
OUTPUT_JSON=0

# Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --by-package)
      BY_PACKAGE=1
      shift
      ;;
    --mismatches)
      SHOW_MISMATCHES_ONLY=1
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    --json)
      OUTPUT_JSON=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Extract version from YAML frontmatter
extract_version() {
  local file="$1"
  grep "^version:" "$file" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"' || echo ""
}

# Get manifest version
get_manifest_version() {
  local package_name="$1"
  local manifest="$REPO_ROOT/packages/$package_name/manifest.yaml"
  if [[ -f "$manifest" ]]; then
    extract_version "$manifest"
  else
    echo ""
  fi
}

# Compare versions in package
compare_package_versions() {
  local package_name="$1"
  local package_dir="$REPO_ROOT/packages/$package_name"
  local manifest_version=$(get_manifest_version "$package_name")

  local mismatches=0
  local versions=()

  # Check commands
  for cmd_file in "$package_dir"/commands/*.md; do
    if [[ -f "$cmd_file" ]]; then
      local cmd_name=$(basename "$cmd_file" .md)
      local cmd_version=$(extract_version "$cmd_file")
      versions+=("command:$cmd_name:$cmd_version")

      if [[ "$cmd_version" != "$manifest_version" ]]; then
        mismatches=1
      fi
    fi
  done

  # Check skills
  for skill_file in "$package_dir"/skills/*/SKILL.md; do
    if [[ -f "$skill_file" ]]; then
      local skill_name=$(basename "$(dirname "$skill_file")")
      local skill_version=$(extract_version "$skill_file")
      versions+=("skill:$skill_name:$skill_version")

      if [[ "$skill_version" != "$manifest_version" ]]; then
        mismatches=1
      fi
    fi
  done

  # Check agents
  for agent_file in "$package_dir"/agents/*.md; do
    if [[ -f "$agent_file" ]]; then
      local agent_name=$(basename "$agent_file" .md)
      local agent_version=$(extract_version "$agent_file")
      versions+=("agent:$agent_name:$agent_version")

      if [[ "$agent_version" != "$manifest_version" ]]; then
        mismatches=1
      fi
    fi
  done

  # Output results
  if [[ $SHOW_MISMATCHES_ONLY -eq 1 && $mismatches -eq 0 ]]; then
    return 0
  fi

  echo "$package_name:$manifest_version:$mismatches:${versions[@]}"
}

# Main comparison logic
main() {
  if [[ $OUTPUT_JSON -eq 1 ]]; then
    output_json
    return $?
  fi

  local overall_mismatch=0
  local marketplace_version=$(extract_version "$REPO_ROOT/version.yaml")

  echo "=== Synaptic Canvas Version Comparison ==="
  echo ""
  echo "Marketplace Version: $marketplace_version"
  echo ""

  # Iterate through packages
  for package_dir in "$REPO_ROOT"/packages/*/; do
    local package_name=$(basename "$package_dir")
    local result=$(compare_package_versions "$package_name")

    IFS=':' read -r pkg manifest_ver mismatches artifacts <<< "$result"

    if [[ $SHOW_MISMATCHES_ONLY -eq 1 && $mismatches -eq 0 ]]; then
      continue
    fi

    if [[ $mismatches -eq 1 ]]; then
      overall_mismatch=1
      echo -e "${RED}Package: $pkg (manifest: $manifest_ver)${NC}"
    else
      echo -e "${GREEN}Package: $pkg (manifest: $manifest_ver)${NC}"
    fi

    if [[ $VERBOSE -eq 1 ]]; then
      # Parse and display artifact versions
      IFS=' ' read -ra artifact_array <<< "$artifacts"
      for artifact_info in "${artifact_array[@]}"; do
        IFS=':' read -r artifact_type artifact_name artifact_version <<< "$artifact_info"

        if [[ "$artifact_version" != "$manifest_ver" ]]; then
          echo -e "  ${RED}✗${NC} $artifact_type/$artifact_name: $artifact_version"
        else
          echo -e "  ${GREEN}✓${NC} $artifact_type/$artifact_name: $artifact_version"
        fi
      done
    fi
    echo ""
  done

  if [[ $overall_mismatch -eq 0 ]]; then
    echo -e "${GREEN}All versions consistent!${NC}"
    return 0
  else
    echo -e "${RED}Version mismatches found${NC}"
    return 1
  fi
}

# Output as JSON
output_json() {
  echo "{"
  echo "  \"marketplace\": \"$(extract_version "$REPO_ROOT/version.yaml")\","
  echo "  \"packages\": ["

  local first=1
  for package_dir in "$REPO_ROOT"/packages/*/; do
    local package_name=$(basename "$package_dir")
    local result=$(compare_package_versions "$package_name")

    IFS=':' read -r pkg manifest_ver mismatches artifacts <<< "$result"

    if [[ $first -eq 0 ]]; then
      echo ","
    fi
    first=0

    echo -n "    {\"name\": \"$pkg\", \"version\": \"$manifest_ver\", \"consistent\": $([ $mismatches -eq 0 ] && echo "true" || echo "false")}"
  done

  echo ""
  echo "  ]"
  echo "}"
}

main
exit $?
