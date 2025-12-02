#!/bin/bash
#
# audit-versions.sh - Verify version consistency across packages and artifacts
#
# Usage: ./scripts/audit-versions.sh [--verbose] [--fix-warnings]
#
# Checks:
# - All commands have version frontmatter
# - All skills have version frontmatter
# - All agents have version frontmatter
# - Artifact versions match package versions
# - CHANGELOG files exist for versioned packages
#
# Exit codes:
# 0 - All checks passed
# 1 - Mismatches or missing versions found
# 2 - Critical errors

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VERBOSE=0
FIX_WARNINGS=0

# Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose)
      VERBOSE=1
      shift
      ;;
    --fix-warnings)
      FIX_WARNINGS=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 2
      ;;
  esac
done

# Extract version from YAML frontmatter
extract_version() {
  local file="$1"
  grep "^version:" "$file" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"' || echo ""
}

# Extract version from manifest
get_manifest_version() {
  local package_name="$1"
  local manifest="$REPO_ROOT/packages/$package_name/manifest.yaml"
  if [[ -f "$manifest" ]]; then
    extract_version "$manifest"
  else
    echo ""
  fi
}

# Report result
report_check() {
  local check_name="$1"
  local status="$2"  # "PASS" or "FAIL" or "WARN"
  local message="$3"

  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  case "$status" in
    PASS)
      if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${GREEN}✓${NC} $check_name"
      fi
      PASSED_CHECKS=$((PASSED_CHECKS + 1))
      ;;
    FAIL)
      echo -e "${RED}✗ FAIL${NC} $check_name: $message"
      FAILED_CHECKS=$((FAILED_CHECKS + 1))
      ;;
    WARN)
      echo -e "${YELLOW}⚠ WARN${NC} $check_name: $message"
      WARNINGS=$((WARNINGS + 1))
      ;;
  esac
}

echo "=== Synaptic Canvas Version Audit ==="
echo ""

# 1. Check commands have version frontmatter
echo "Checking commands..."
for cmd_file in "$REPO_ROOT"/packages/*/commands/*.md; do
  if [[ -f "$cmd_file" ]]; then
    cmd_name=$(basename "$cmd_file" .md)
    version=$(extract_version "$cmd_file")

    if [[ -z "$version" ]]; then
      report_check "Command: $cmd_name" "FAIL" "Missing version frontmatter"
    else
      report_check "Command: $cmd_name (v$version)" "PASS"
    fi
  fi
done

# 2. Check skills have version frontmatter
echo "Checking skills..."
for skill_file in "$REPO_ROOT"/packages/*/skills/*/SKILL.md; do
  if [[ -f "$skill_file" ]]; then
    skill_name=$(basename "$(dirname "$skill_file")")
    version=$(extract_version "$skill_file")

    if [[ -z "$version" ]]; then
      report_check "Skill: $skill_name" "FAIL" "Missing version frontmatter"
    else
      report_check "Skill: $skill_name (v$version)" "PASS"
    fi
  fi
done

# 3. Check agents have version frontmatter
echo "Checking agents..."
for agent_file in "$REPO_ROOT"/packages/*/agents/*.md "$REPO_ROOT"/.claude/agents/*.md; do
  if [[ -f "$agent_file" ]]; then
    agent_name=$(basename "$agent_file" .md)
    version=$(extract_version "$agent_file")

    if [[ -z "$version" ]]; then
      report_check "Agent: $agent_name" "FAIL" "Missing version frontmatter"
    else
      report_check "Agent: $agent_name (v$version)" "PASS"
    fi
  fi
done

# 4. Check artifact versions match package versions
echo "Checking version consistency..."
for package_dir in "$REPO_ROOT"/packages/*/; do
  package_name=$(basename "$package_dir")
  package_version=$(get_manifest_version "$package_name")

  if [[ -z "$package_version" ]]; then
    report_check "Package: $package_name" "FAIL" "No manifest.yaml or version found"
    continue
  fi

  # Check commands
  for cmd_file in "$package_dir"commands/*.md; do
    if [[ -f "$cmd_file" ]]; then
      cmd_version=$(extract_version "$cmd_file")
      if [[ "$cmd_version" != "$package_version" ]]; then
        report_check "Command in $package_name" "FAIL" "Version mismatch: command=$cmd_version, package=$package_version"
      fi
    fi
  done

  # Check skills
  for skill_file in "$package_dir"skills/*/SKILL.md; do
    if [[ -f "$skill_file" ]]; then
      skill_version=$(extract_version "$skill_file")
      if [[ "$skill_version" != "$package_version" ]]; then
        report_check "Skill in $package_name" "FAIL" "Version mismatch: skill=$skill_version, package=$package_version"
      fi
    fi
  done

  # Check agents
  for agent_file in "$package_dir"agents/*.md; do
    if [[ -f "$agent_file" ]]; then
      agent_version=$(extract_version "$agent_file")
      if [[ "$agent_version" != "$package_version" ]]; then
        report_check "Agent in $package_name" "FAIL" "Version mismatch: agent=$agent_version, package=$package_version"
      fi
    fi
  done
done

# 5. Check for CHANGELOG files
echo "Checking CHANGELOGs..."
for package_dir in "$REPO_ROOT"/packages/*/; do
  package_name=$(basename "$package_dir")
  changelog="$package_dir/CHANGELOG.md"

  if [[ ! -f "$changelog" ]]; then
    report_check "CHANGELOG for $package_name" "WARN" "No CHANGELOG.md found"
  else
    report_check "CHANGELOG for $package_name" "PASS"
  fi
done

# 6. Check marketplace version
echo "Checking marketplace version..."
marketplace_version=$(extract_version "$REPO_ROOT/version.yaml")
if [[ -z "$marketplace_version" ]]; then
  report_check "Marketplace version" "FAIL" "No version found in version.yaml"
else
  report_check "Marketplace version (v$marketplace_version)" "PASS"
fi

echo ""
echo "=== Audit Results ==="
echo "Total checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [[ $FAILED_CHECKS -eq 0 ]]; then
  echo -e "${GREEN}All checks passed!${NC}"
  exit 0
else
  echo -e "${RED}$FAILED_CHECKS check(s) failed${NC}"
  exit 1
fi
