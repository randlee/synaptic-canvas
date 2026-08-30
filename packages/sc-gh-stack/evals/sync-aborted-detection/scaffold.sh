#!/usr/bin/env bash
# Fixture for the silent-abort trap: the local and remote stacks diverged, so
# non-interactive `gh stack sync` prints both chains plus "Sync aborted" and exits
# 0 WITHOUT syncing anything. Reporting "synced" here is the failure being graded.
# The package scripts are installed into repo/.claude/scripts so the skill's
# script route (gh_stack_sync.py -> SYNC.ABORTED) is available.
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo base > base.txt && git add . && git commit -qm "base"
git switch -qc feat/one && echo one > one.txt && git add . && git commit -qm "one"
git switch -qc feat/two && echo two > two.txt && git add . && git commit -qm "two"
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main feat/one feat/two
mkdir -p .claude/scripts
cp "$CASE_DIR"/../../scripts/gh_stack_*.py "$CASE_DIR"/../../scripts/sc_shared.py .claude/scripts/ 2>/dev/null || true
cd "$WS"

mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack view --json")
    printf '{"trunk":"main","branches":[{"name":"feat/one","isCurrent":false,"isMerged":false,"needsRebase":false},{"name":"feat/two","isCurrent":true,"isMerged":false,"needsRebase":false}]}\n' ;;
  "stack sync"*)
    # Faithful upstream divergence behavior: exit 0, nothing synced.
    echo "local:  main <- feat/one <- feat/two"
    echo "remote: main <- feat/one <- feat/three"
    echo "Sync aborted"
    exit 0 ;;
  "stack unstack --local") echo "Local tracking removed." ;;
  "stack checkout"*) echo "Checked out." ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
