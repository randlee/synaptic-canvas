#!/bin/bash
# validate-plugin-docs.sh - Validate plugin documentation structure
#
# Usage: ./scripts/validate-plugin-docs.sh [plugin-dir]
#        ./scripts/validate-plugin-docs.sh packages/sc-github-issue
#        ./scripts/validate-plugin-docs.sh --all
#
# Exit codes:
#   0 - All validations passed
#   1 - Missing required files
#   2 - Missing required sections in SKILL-FLOW.md
#   3 - Missing diagrams

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}ERROR${NC}: $1"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}WARNING${NC}: $1"
    ((WARNINGS++))
}

log_ok() {
    echo -e "${GREEN}OK${NC}: $1"
}

log_header() {
    echo ""
    echo "=== $1 ==="
}

validate_plugin() {
    local PLUGIN_DIR="$1"
    local PLUGIN_NAME=$(basename "$PLUGIN_DIR")

    log_header "Validating: $PLUGIN_NAME"

    # Skip if not a plugin directory (no manifest.yaml)
    if [ ! -f "$PLUGIN_DIR/manifest.yaml" ]; then
        echo "Skipping $PLUGIN_DIR (no manifest.yaml)"
        return 0
    fi

    # =========================================
    # Check 1: Required files exist
    # =========================================
    log_header "Required Files"

    REQUIRED_FILES=(
        "README.md"
        "SKILL-FLOW.md"
        "CHANGELOG.md"
        "manifest.yaml"
    )

    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$PLUGIN_DIR/$file" ]; then
            log_error "Missing required file: $file"
        else
            log_ok "$file exists"
        fi
    done

    # Optional but recommended files
    OPTIONAL_FILES=(
        "USE-CASES.md"
        "TROUBLESHOOTING.md"
    )

    for file in "${OPTIONAL_FILES[@]}"; do
        if [ ! -f "$PLUGIN_DIR/$file" ]; then
            log_warning "Missing optional file: $file"
        else
            log_ok "$file exists"
        fi
    done

    # =========================================
    # Check 2: SKILL-FLOW.md structure
    # =========================================
    SKILL_FLOW="$PLUGIN_DIR/SKILL-FLOW.md"

    if [ -f "$SKILL_FLOW" ]; then
        log_header "SKILL-FLOW.md Structure"

        REQUIRED_SECTIONS=(
            "## Overview"
            "## Entry Points"
            "## State Machine"
            "## Agent Orchestration"
            "## User Interaction Gates"
            "## Context Accumulation Map"
            "## Error Recovery Paths"
            "## Examples"
        )

        for section in "${REQUIRED_SECTIONS[@]}"; do
            if ! grep -q "$section" "$SKILL_FLOW"; then
                log_error "SKILL-FLOW.md missing section: $section"
            else
                log_ok "Section present: $section"
            fi
        done

        # =========================================
        # Check 3: Mermaid diagrams
        # =========================================
        log_header "Diagram Validation"

        MERMAID_COUNT=$(grep -c '```mermaid' "$SKILL_FLOW" 2>/dev/null || echo "0")
        if [ "$MERMAID_COUNT" -eq 0 ]; then
            log_error "SKILL-FLOW.md has no Mermaid diagrams"
        elif [ "$MERMAID_COUNT" -lt 2 ]; then
            log_warning "SKILL-FLOW.md has only $MERMAID_COUNT Mermaid diagram(s), recommend at least 2"
        else
            log_ok "Found $MERMAID_COUNT Mermaid diagrams"
        fi

        # =========================================
        # Check 4: ASCII diagrams (fallback)
        # =========================================
        if grep -qE '(╔|┌|└|│|▼|→)' "$SKILL_FLOW"; then
            log_ok "ASCII diagrams present (terminal fallback)"
        else
            log_warning "No ASCII diagrams found (terminal fallback recommended)"
        fi

        # =========================================
        # Check 5: JSON gate examples
        # =========================================
        log_header "JSON Gate Documentation"

        if grep -q '"type":\s*".*_gate"' "$SKILL_FLOW" || \
           grep -q '"type": "confirmation_gate\|decision_gate"' "$SKILL_FLOW"; then
            log_ok "JSON gate examples present"
        else
            log_warning "No JSON gate examples found"
        fi

        # Check for gate response schemas
        if grep -q '"proceed":\|"action":' "$SKILL_FLOW"; then
            log_ok "Gate response schemas present"
        else
            log_warning "No gate response schemas found"
        fi

        # =========================================
        # Check 6: Context accumulation table
        # =========================================
        log_header "Context Documentation"

        if grep -q '| Stage |' "$SKILL_FLOW" || grep -q 'Stage 0:' "$SKILL_FLOW"; then
            log_ok "Context accumulation documentation present"
        else
            log_warning "Context accumulation table/flow not found"
        fi

        # =========================================
        # Check 7: Error code reference
        # =========================================
        log_header "Error Documentation"

        if grep -q '| Code |' "$SKILL_FLOW" || grep -qE '\| `[A-Z]+\.' "$SKILL_FLOW"; then
            log_ok "Error code reference table present"
        else
            log_warning "Error code reference table not found"
        fi

        # =========================================
        # Check 8: Execution trace examples
        # =========================================
        log_header "Example Traces"

        if grep -qE '\[.*\] (Parsed:|Input:|Output:|Prompt:|Response:)' "$SKILL_FLOW"; then
            log_ok "Execution trace examples present"
        else
            log_warning "No execution trace examples found"
        fi
    fi

    # =========================================
    # Check 9: README links to SKILL-FLOW
    # =========================================
    log_header "Cross-References"

    README="$PLUGIN_DIR/README.md"
    if [ -f "$README" ]; then
        if grep -q 'SKILL-FLOW.md' "$README"; then
            log_ok "README.md links to SKILL-FLOW.md"
        else
            log_warning "README.md should link to SKILL-FLOW.md"
        fi
    fi

    # =========================================
    # Summary for this plugin
    # =========================================
    echo ""
    if [ $ERRORS -gt 0 ]; then
        echo -e "${RED}FAIL${NC}: $PLUGIN_NAME - $ERRORS error(s), $WARNINGS warning(s)"
        return 1
    elif [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}WARN${NC}: $PLUGIN_NAME - $WARNINGS warning(s)"
        return 0
    else
        echo -e "${GREEN}PASS${NC}: $PLUGIN_NAME - All checks passed"
        return 0
    fi
}

# =========================================
# Main execution
# =========================================

if [ $# -eq 0 ]; then
    echo "Usage: $0 [plugin-dir|--all]"
    echo ""
    echo "Examples:"
    echo "  $0 packages/sc-github-issue"
    echo "  $0 --all"
    exit 1
fi

TOTAL_ERRORS=0
TOTAL_WARNINGS=0
PLUGINS_CHECKED=0

if [ "$1" = "--all" ]; then
    # Validate all plugins
    for plugin in packages/*/; do
        if [ -f "${plugin}manifest.yaml" ]; then
            ERRORS=0
            WARNINGS=0
            if ! validate_plugin "$plugin"; then
                ((TOTAL_ERRORS++))
            fi
            ((TOTAL_WARNINGS += WARNINGS))
            ((PLUGINS_CHECKED++))
        fi
    done

    echo ""
    echo "=========================================="
    echo "Summary: $PLUGINS_CHECKED plugins checked"
    echo "  Plugins with errors: $TOTAL_ERRORS"
    echo "  Total warnings: $TOTAL_WARNINGS"
    echo "=========================================="

    if [ $TOTAL_ERRORS -gt 0 ]; then
        exit 1
    fi
else
    # Validate single plugin
    if [ ! -d "$1" ]; then
        echo "ERROR: Directory not found: $1"
        exit 1
    fi

    validate_plugin "$1"
fi
