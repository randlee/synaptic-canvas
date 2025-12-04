#!/usr/bin/env bash
#
# security-scan.sh - Automated security scanning for Synaptic Canvas packages
#
# Purpose: Run comprehensive security checks on all packages in the repository
#
# Usage:
#   ./scripts/security-scan.sh                       # Full scan
#   ./scripts/security-scan.sh --quick               # Quick checks only
#   ./scripts/security-scan.sh --json                # JSON output
#   ./scripts/security-scan.sh --package delay-tasks # Single package
#   ./scripts/security-scan.sh --help                # Show help
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCAN_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUTPUT_FORMAT="text"
QUICK_MODE=false
SINGLE_PACKAGE=""

# Results tracking
declare -A RESULTS
OVERALL_STATUS="PASSED"
ISSUES_FOUND=0

# Initialize results
RESULTS[secrets_detection]="pending"
RESULTS[script_quality]="pending"
RESULTS[python_safety]="pending"
RESULTS[package_docs]="pending"
RESULTS[license_files]="pending"
RESULTS[dependency_audit]="pending"

#=============================================================================
# Helper Functions
#=============================================================================

print_header() {
    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "$1"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
    fi
}

print_section() {
    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        echo ""
        echo "--- $1 ---"
        echo ""
    fi
}

print_result() {
    local check="$1"
    local status="$2"
    local message="$3"

    RESULTS["$check"]="$status"

    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        if [[ "$status" == "PASSED" ]]; then
            echo -e "${GREEN}✅ $check: PASSED${NC} $message"
        elif [[ "$status" == "WARNING" ]]; then
            echo -e "${YELLOW}⚠️  $check: WARNING${NC} $message"
            OVERALL_STATUS="WARNING"
        else
            echo -e "${RED}❌ $check: FAILED${NC} $message"
            OVERALL_STATUS="FAILED"
        fi
    fi
}

print_detail() {
    local severity="$1"
    local message="$2"

    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        if [[ "$severity" == "HIGH" ]]; then
            echo -e "   ${RED}[HIGH]${NC} $message"
        elif [[ "$severity" == "MEDIUM" ]]; then
            echo -e "   ${YELLOW}[MEDIUM]${NC} $message"
        else
            echo -e "   ${BLUE}[LOW]${NC} $message"
        fi
    fi
}

show_help() {
    cat <<EOF
Security Scan Tool for Synaptic Canvas

Usage:
  ./scripts/security-scan.sh [OPTIONS]

Options:
  --quick               Run quick checks only (skip slow scans)
  --json                Output results in JSON format
  --package NAME        Scan only the specified package
  --help                Show this help message

Examples:
  ./scripts/security-scan.sh
  ./scripts/security-scan.sh --quick
  ./scripts/security-scan.sh --json > scan-results.json
  ./scripts/security-scan.sh --package delay-tasks

Checks Performed:
  1. Secrets Detection      - Scan for hardcoded credentials
  2. Script Quality         - Validate shell scripts with shellcheck
  3. Python Safety          - Check for unsafe Python patterns
  4. Package Documentation  - Verify security docs present
  5. License Files          - Ensure all packages have LICENSE
  6. Dependency Audit       - Check for vulnerable dependencies

Exit Codes:
  0 - All checks passed
  1 - Warnings found (non-critical)
  2 - Failures found (critical issues)
EOF
}

#=============================================================================
# 1. Secrets Detection
#=============================================================================

scan_secrets() {
    print_section "Secrets Detection"

    local secrets_found=0
    local files_with_secrets=()

    # Patterns to search for
    local patterns=(
        'password\s*=\s*["\047][^"\047]+["\047]'
        'api_key\s*=\s*["\047][^"\047]+["\047]'
        'secret\s*=\s*["\047][^"\047]+["\047]'
        'token\s*=\s*["\047][^"\047]+["\047]'
        'AWS_KEY\s*=\s*["\047][^"\047]+["\047]'
        'AWS_SECRET\s*=\s*["\047][^"\047]+["\047]'
        'GITHUB_TOKEN\s*=\s*["\047][^"\047]+["\047]'
        'private_key\s*=\s*["\047][^"\047]+["\047]'
        'BEGIN PRIVATE KEY'
        'BEGIN RSA PRIVATE KEY'
    )

    # Search in all code files
    local search_path="$REPO_ROOT"
    if [[ -n "$SINGLE_PACKAGE" ]]; then
        search_path="$REPO_ROOT/packages/$SINGLE_PACKAGE"
    fi

    for pattern in "${patterns[@]}"; do
        while IFS= read -r match; do
            if [[ -n "$match" ]]; then
                secrets_found=$((secrets_found + 1))
                local file="${match%%:*}"
                local line="${match#*:}"
                files_with_secrets+=("$file")
                print_detail "HIGH" "Potential secret in: $file"
                if [[ "$OUTPUT_FORMAT" == "text" ]]; then
                    echo "      Line: ${line:0:100}..."
                fi
            fi
        done < <(grep -rn -E -i "$pattern" "$search_path" \
            --exclude-dir=.git \
            --exclude-dir=.venv \
            --exclude-dir=__pycache__ \
            --exclude-dir=node_modules \
            --exclude="*.pyc" \
            --exclude="security-scan.sh" \
            2>/dev/null || true)
    done

    # Check for common config mistakes in markdown
    while IFS= read -r match; do
        if echo "$match" | grep -qE "(password|secret|token|key).*[\"'].*[a-zA-Z0-9]{16,}"; then
            secrets_found=$((secrets_found + 1))
            local file="${match%%:*}"
            files_with_secrets+=("$file")
            print_detail "MEDIUM" "Possible credential in markdown: $file"
        fi
    done < <(grep -rn -E "(password|secret|token|key)" "$search_path" \
        --include="*.md" \
        --exclude-dir=.git \
        2>/dev/null || true)

    if [[ $secrets_found -eq 0 ]]; then
        print_result "Secrets Detection" "PASSED" "(0 potential secrets found)"
    else
        print_result "Secrets Detection" "FAILED" "($secrets_found potential secrets found)"
        ISSUES_FOUND=$((ISSUES_FOUND + secrets_found))
    fi
}

#=============================================================================
# 2. Script Quality Checks
#=============================================================================

check_script_quality() {
    print_section "Script Quality"

    local script_issues=0
    local total_scripts=0
    local non_executable=0

    local search_path="$REPO_ROOT"
    if [[ -n "$SINGLE_PACKAGE" ]]; then
        search_path="$REPO_ROOT/packages/$SINGLE_PACKAGE"
    fi

    # Find all shell scripts
    while IFS= read -r script; do
        total_scripts=$((total_scripts + 1))

        # Check if executable
        if [[ ! -x "$script" ]]; then
            non_executable=$((non_executable + 1))
            print_detail "MEDIUM" "Script not executable: $script"
        fi

        # Run shellcheck if available
        if command -v shellcheck &> /dev/null; then
            if ! shellcheck -x "$script" 2>&1 | grep -q "No issues detected"; then
                local issues=$(shellcheck "$script" 2>&1 | grep -c "^In " || echo "0")
                if [[ $issues -gt 0 ]]; then
                    script_issues=$((script_issues + issues))
                    print_detail "LOW" "Shellcheck found $issues issue(s) in: $script"
                fi
            fi
        fi
    done < <(find "$search_path" -type f -name "*.sh" 2>/dev/null)

    # Check for common script issues
    while IFS= read -r script; do
        # Check for missing shebang
        if ! head -n 1 "$script" | grep -q "^#!"; then
            script_issues=$((script_issues + 1))
            print_detail "MEDIUM" "Missing shebang in: $script"
        fi

        # Check for 'set -e' or 'set -euo pipefail'
        if ! head -n 20 "$script" | grep -q "set -e"; then
            script_issues=$((script_issues + 1))
            print_detail "LOW" "Missing 'set -e' in: $script"
        fi
    done < <(find "$search_path" -type f -name "*.sh" 2>/dev/null)

    if [[ ! -x "$REPO_ROOT/scripts/security-scan.sh" ]]; then
        script_issues=$((script_issues + 1))
    fi

    if [[ $script_issues -eq 0 && $non_executable -eq 0 ]]; then
        print_result "Script Quality" "PASSED" "(all $total_scripts scripts valid)"
    elif [[ $script_issues -lt 5 ]]; then
        print_result "Script Quality" "WARNING" "($script_issues minor issues found)"
        ISSUES_FOUND=$((ISSUES_FOUND + script_issues))
    else
        print_result "Script Quality" "FAILED" "($script_issues issues found)"
        ISSUES_FOUND=$((ISSUES_FOUND + script_issues))
    fi
}

#=============================================================================
# 3. Python Code Quality
#=============================================================================

check_python_safety() {
    print_section "Python Safety"

    local python_issues=0

    local search_path="$REPO_ROOT"
    if [[ -n "$SINGLE_PACKAGE" ]]; then
        search_path="$REPO_ROOT/packages/$SINGLE_PACKAGE"
    fi

    # Check for eval() calls
    while IFS= read -r match; do
        python_issues=$((python_issues + 1))
        print_detail "HIGH" "Unsafe eval() call in: ${match%%:*}"
    done < <(grep -rn "eval(" "$search_path" \
        --include="*.py" \
        --exclude-dir=.venv \
        --exclude-dir=__pycache__ \
        2>/dev/null || true)

    # Check for exec() calls
    while IFS= read -r match; do
        python_issues=$((python_issues + 1))
        print_detail "HIGH" "Unsafe exec() call in: ${match%%:*}"
    done < <(grep -rn "exec(" "$search_path" \
        --include="*.py" \
        --exclude-dir=.venv \
        --exclude-dir=__pycache__ \
        2>/dev/null || true)

    # Check for shell=True in subprocess
    while IFS= read -r match; do
        python_issues=$((python_issues + 1))
        print_detail "MEDIUM" "Potentially unsafe shell=True in: ${match%%:*}"
    done < <(grep -rn "shell=True" "$search_path" \
        --include="*.py" \
        --exclude-dir=.venv \
        --exclude-dir=__pycache__ \
        2>/dev/null || true)

    # Check for pickle.loads without verification
    while IFS= read -r match; do
        python_issues=$((python_issues + 1))
        print_detail "MEDIUM" "Pickle deserialization in: ${match%%:*}"
    done < <(grep -rn "pickle.loads" "$search_path" \
        --include="*.py" \
        --exclude-dir=.venv \
        --exclude-dir=__pycache__ \
        2>/dev/null || true)

    if [[ $python_issues -eq 0 ]]; then
        print_result "Python Safety" "PASSED" "(no unsafe patterns found)"
    else
        print_result "Python Safety" "FAILED" "($python_issues unsafe patterns found)"
        ISSUES_FOUND=$((ISSUES_FOUND + python_issues))
    fi
}

#=============================================================================
# 4. Package Verification
#=============================================================================

verify_package_documentation() {
    print_section "Package Documentation"

    local missing_security_docs=0
    local packages_checked=0

    if [[ -n "$SINGLE_PACKAGE" ]]; then
        local packages=("$SINGLE_PACKAGE")
    else
        # Find all packages
        local packages=()
        while IFS= read -r pkg_dir; do
            packages+=("$(basename "$pkg_dir")")
        done < <(find "$REPO_ROOT/packages" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
    fi

    for package in "${packages[@]}"; do
        packages_checked=$((packages_checked + 1))
        local pkg_path="$REPO_ROOT/packages/$package"

        # Check for README.md
        if [[ ! -f "$pkg_path/README.md" ]]; then
            missing_security_docs=$((missing_security_docs + 1))
            print_detail "HIGH" "Missing README.md in: $package"
        else
            # Check README mentions security
            if ! grep -qi "security" "$pkg_path/README.md"; then
                missing_security_docs=$((missing_security_docs + 1))
                print_detail "MEDIUM" "README missing security information: $package"
            fi
        fi

        # Check for LICENSE file
        if [[ ! -f "$pkg_path/LICENSE" ]]; then
            missing_security_docs=$((missing_security_docs + 1))
            print_detail "HIGH" "Missing LICENSE in: $package"
        fi

        # Check for manifest.yaml
        if [[ ! -f "$pkg_path/manifest.yaml" ]]; then
            missing_security_docs=$((missing_security_docs + 1))
            print_detail "HIGH" "Missing manifest.yaml in: $package"
        else
            # Validate YAML syntax
            if command -v python3 &> /dev/null; then
                if ! python3 -c "import yaml; yaml.safe_load(open('$pkg_path/manifest.yaml'))" 2>/dev/null; then
                    missing_security_docs=$((missing_security_docs + 1))
                    print_detail "HIGH" "Invalid YAML in manifest.yaml: $package"
                fi
            fi
        fi

        # Check for CHANGELOG.md
        if [[ ! -f "$pkg_path/CHANGELOG.md" ]]; then
            print_detail "LOW" "Missing CHANGELOG.md in: $package (recommended)"
        fi
    done

    if [[ $missing_security_docs -eq 0 ]]; then
        print_result "Package Documentation" "PASSED" "(all $packages_checked packages have required docs)"
    else
        print_result "Package Documentation" "FAILED" "($missing_security_docs issues in $packages_checked packages)"
        ISSUES_FOUND=$((ISSUES_FOUND + missing_security_docs))
    fi
}

verify_license_files() {
    print_section "License Files"

    local missing_licenses=0
    local packages_checked=0

    if [[ -n "$SINGLE_PACKAGE" ]]; then
        local packages=("$SINGLE_PACKAGE")
    else
        local packages=()
        while IFS= read -r pkg_dir; do
            packages+=("$(basename "$pkg_dir")")
        done < <(find "$REPO_ROOT/packages" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
    fi

    for package in "${packages[@]}"; do
        packages_checked=$((packages_checked + 1))
        local pkg_path="$REPO_ROOT/packages/$package"

        if [[ ! -f "$pkg_path/LICENSE" ]]; then
            missing_licenses=$((missing_licenses + 1))
            print_detail "HIGH" "Missing LICENSE in: $package"
        else
            # Check LICENSE is not empty
            if [[ ! -s "$pkg_path/LICENSE" ]]; then
                missing_licenses=$((missing_licenses + 1))
                print_detail "HIGH" "Empty LICENSE file in: $package"
            fi
        fi
    done

    # Check root LICENSE
    if [[ ! -f "$REPO_ROOT/LICENSE" ]]; then
        missing_licenses=$((missing_licenses + 1))
        print_detail "HIGH" "Missing LICENSE in repository root"
    fi

    if [[ $missing_licenses -eq 0 ]]; then
        print_result "License Files" "PASSED" "(all packages have LICENSE)"
    else
        print_result "License Files" "FAILED" "($missing_licenses missing licenses)"
        ISSUES_FOUND=$((ISSUES_FOUND + missing_licenses))
    fi
}

#=============================================================================
# 5. Dependency Audit
#=============================================================================

audit_dependencies() {
    if [[ "$QUICK_MODE" == "true" ]]; then
        print_result "Dependency Audit" "SKIPPED" "(quick mode)"
        return
    fi

    print_section "Dependency Audit"

    local vulnerabilities=0
    local warnings=0

    # Check Node.js dependencies
    if [[ -f "$REPO_ROOT/package.json" ]] && command -v npm &> /dev/null; then
        if [[ "$OUTPUT_FORMAT" == "text" ]]; then
            echo "Checking Node.js dependencies..."
        fi

        local npm_output
        npm_output=$(cd "$REPO_ROOT" && npm audit --json 2>/dev/null || echo '{"error": "failed"}')

        if echo "$npm_output" | jq -e '.vulnerabilities' &>/dev/null; then
            local high=$(echo "$npm_output" | jq -r '.metadata.vulnerabilities.high // 0')
            local moderate=$(echo "$npm_output" | jq -r '.metadata.vulnerabilities.moderate // 0')

            if [[ $high -gt 0 ]]; then
                vulnerabilities=$((vulnerabilities + high))
                print_detail "HIGH" "$high high severity npm vulnerabilities"
            fi

            if [[ $moderate -gt 0 ]]; then
                warnings=$((warnings + moderate))
                print_detail "MEDIUM" "$moderate moderate severity npm vulnerabilities"
            fi
        fi
    fi

    # Check Python dependencies
    if [[ -f "$REPO_ROOT/requirements.txt" ]] && command -v pip3 &> /dev/null; then
        if [[ "$OUTPUT_FORMAT" == "text" ]]; then
            echo "Checking Python dependencies..."
        fi

        # Simple check for known vulnerable packages
        local vulnerable_packages=("pyyaml<5.4" "requests<2.20.0" "urllib3<1.26.5")

        for vuln_pkg in "${vulnerable_packages[@]}"; do
            local pkg_name="${vuln_pkg%%<*}"
            if grep -q "^$pkg_name" "$REPO_ROOT/requirements.txt" 2>/dev/null; then
                warnings=$((warnings + 1))
                print_detail "MEDIUM" "Check version of $pkg_name (known vulnerabilities in old versions)"
            fi
        done
    fi

    # Check for outdated git references
    while IFS= read -r manifest; do
        if grep -q "git+http://" "$manifest" 2>/dev/null; then
            warnings=$((warnings + 1))
            print_detail "LOW" "Insecure git:// protocol in: $manifest"
        fi
    done < <(find "$REPO_ROOT/packages" -name "manifest.yaml" 2>/dev/null)

    if [[ $vulnerabilities -eq 0 && $warnings -eq 0 ]]; then
        print_result "Dependency Audit" "PASSED" "(no vulnerabilities found)"
    elif [[ $vulnerabilities -eq 0 ]]; then
        print_result "Dependency Audit" "WARNING" "($warnings warnings found)"
        ISSUES_FOUND=$((ISSUES_FOUND + warnings))
    else
        print_result "Dependency Audit" "FAILED" "($vulnerabilities high severity issues)"
        ISSUES_FOUND=$((ISSUES_FOUND + vulnerabilities))
    fi
}

#=============================================================================
# Report Generation
#=============================================================================

generate_report() {
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        generate_json_report
    else
        generate_text_report
    fi
}

generate_text_report() {
    print_header "Security Scan Report - $SCAN_DATE"

    echo ""

    # Print all results
    for check in "Secrets Detection" "Script Quality" "Python Safety" "Package Documentation" "License Files" "Dependency Audit"; do
        local key="${check// /_}"
        key="${key,,}"
        local status="${RESULTS[$key]}"

        if [[ "$status" == "PASSED" ]]; then
            echo -e "${GREEN}✅ $check: PASSED${NC}"
        elif [[ "$status" == "WARNING" ]]; then
            echo -e "${YELLOW}⚠️  $check: WARNING${NC}"
        elif [[ "$status" == "SKIPPED" ]]; then
            echo -e "${BLUE}⊘  $check: SKIPPED${NC}"
        else
            echo -e "${RED}❌ $check: FAILED${NC}"
        fi
    done

    echo ""
    echo "─────────────────────────────────────────────────────────"
    echo ""

    if [[ "$OVERALL_STATUS" == "PASSED" ]]; then
        echo -e "${GREEN}OVERALL STATUS: ✅ PASSED${NC}"
    elif [[ "$OVERALL_STATUS" == "WARNING" ]]; then
        echo -e "${YELLOW}OVERALL STATUS: ⚠️  PASSED (with warnings)${NC}"
    else
        echo -e "${RED}OVERALL STATUS: ❌ FAILED${NC}"
    fi

    echo "Total Issues Found: $ISSUES_FOUND"
    echo "Scan Date: $SCAN_DATE"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
}

generate_json_report() {
    cat <<EOF
{
  "scan_date": "$SCAN_DATE",
  "overall_status": "$OVERALL_STATUS",
  "issues_found": $ISSUES_FOUND,
  "checks": {
    "secrets_detection": "${RESULTS[secrets_detection]}",
    "script_quality": "${RESULTS[script_quality]}",
    "python_safety": "${RESULTS[python_safety]}",
    "package_documentation": "${RESULTS[package_docs]}",
    "license_files": "${RESULTS[license_files]}",
    "dependency_audit": "${RESULTS[dependency_audit]}"
  },
  "scan_configuration": {
    "quick_mode": $QUICK_MODE,
    "single_package": "${SINGLE_PACKAGE:-null}",
    "repo_root": "$REPO_ROOT"
  }
}
EOF
}

#=============================================================================
# Main Execution
#=============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --json)
                OUTPUT_FORMAT="json"
                shift
                ;;
            --package)
                SINGLE_PACKAGE="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate single package exists
    if [[ -n "$SINGLE_PACKAGE" ]] && [[ ! -d "$REPO_ROOT/packages/$SINGLE_PACKAGE" ]]; then
        echo "Error: Package not found: $SINGLE_PACKAGE"
        exit 2
    fi

    # Run all checks
    scan_secrets
    check_script_quality
    check_python_safety
    verify_package_documentation
    verify_license_files
    audit_dependencies

    # Generate report
    generate_report

    # Exit with appropriate code
    if [[ "$OVERALL_STATUS" == "FAILED" ]]; then
        exit 2
    elif [[ "$OVERALL_STATUS" == "WARNING" ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
