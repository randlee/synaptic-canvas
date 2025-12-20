#!/usr/bin/env bash
set -euo pipefail

# Smoke tests for /sc-startup using readonly/fast paths and dependency fail path.
# Assumes:
# - repo root is current directory
# - Agent Runner is available via /sc-startup command
# - python3 available

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${ROOT_DIR}/.claude/.tmp/sc-startup-smoke"
CONFIG="${TMP_DIR}/sc-startup.yaml"
CHECKLIST="${TMP_DIR}/checklist.md"
PROMPT="${TMP_DIR}/prompt.md"

mkdir -p "${TMP_DIR}"

cat > "${PROMPT}" <<'EOF'
You are the startup agent. State your role and wait.
EOF

cat > "${CHECKLIST}" <<'EOF'
# Master Checklist
- [ ] Init repo
EOF

cat > "${CONFIG}" <<EOF
startup-prompt: ${PROMPT#${ROOT_DIR}/}
check-list: ${CHECKLIST#${ROOT_DIR}/}
worktree-scan: none
pr-enabled: false
worktree-enabled: false
EOF

echo "== FAST MODE =="
SC_STARTUP_CONFIG="${CONFIG}" /sc-startup --fast || true

echo "== READONLY, NO DEPS ENABLED =="
SC_STARTUP_CONFIG="${CONFIG}" /sc-startup --readonly || true

echo "== DEPENDENCY FAIL (PR ENABLED, NO AGENT) =="
cat > "${CONFIG}" <<EOF
startup-prompt: ${PROMPT#${ROOT_DIR}/}
check-list: ${CHECKLIST#${ROOT_DIR}/}
worktree-scan: none
pr-enabled: true
worktree-enabled: false
EOF
SC_STARTUP_CONFIG="${CONFIG}" /sc-startup --pr --readonly || true

echo "Smoke tests complete. Check outputs above for DEPENDENCY.MISSING and prompt-only behavior."
