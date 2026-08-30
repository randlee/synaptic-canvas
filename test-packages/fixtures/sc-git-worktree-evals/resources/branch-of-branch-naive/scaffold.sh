#!/usr/bin/env bash
# Fixture for the "distribution guarantee" in DESIGN.md: a stack-naive repo
# (no always_stack, no worktree anywhere carries gh-stack tracking) with an
# UNMERGED branch (feat/base). Creating a branch-of-branch off feat/base must
# still resolve to product A - dependency is never even evaluated, because
# the stack-activity probe (stage 2) short-circuits first. This is the
# "auto-upgrade for legacy prompts": existing branch-off-branch workflows
# must be completely unaffected until the repo actually starts using stacks.
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo "init" > README.md && git add . && git commit -qm "init"
git switch -qc feat/base
echo "on-base" > base.txt && git add . && git commit -qm "wip on feat/base"
git switch -q main
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main feat/base
mkdir -p .claude/scripts
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__
cd "$WS"

# Stub `gh` so a mistaken stack invocation (or prerequisite probe) is
# observable, but a compliant create never touches it: feat/base is unmerged,
# yet the repo is stack-naive, so dependency is never evaluated.
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
