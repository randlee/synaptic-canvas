#!/usr/bin/env bash
# Fixture for the baseline: a stack-naive repo (no .sc/shared-settings.yaml,
# no worktree anywhere carries gh-stack tracking). The factory decision model's
# stack-activity probe (DESIGN.md stage 2) must resolve "not stack-active"
# immediately and produce product A - a plain flat worktree, no settings read
# beyond the one always_stack lookup, no prerequisite check, no gh invocation
# at all. This locks in DESIGN.md's row: "Not stack-active -> product A
# immediately" / SKILL.md's "positive-signal rule" and "auto-upgrade for
# legacy prompts".
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo "init" > README.md && git add . && git commit -qm "init"
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main
mkdir -p .claude/scripts
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__
cd "$WS"

# Stub `gh` so a mistaken stack invocation is observable in gh-calls.log, but
# the correct behavior here is that this stub is NEVER invoked at all.
mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack init"*) echo "Stack initialized." ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
