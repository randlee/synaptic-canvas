#!/usr/bin/env bash
# Fixture for the unconditional destructive-safety gate documented in
# gh-stack-support.md ("Interop rules" #2): batch cleanup must skip ANY
# worktree carrying gh-stack tracking, regardless of merge state - deleting
# it would silently orphan stack metadata for every layer above it. Two
# worktrees exist, both merged into main: feature/tracked-stack (carries the
# gh-stack marker - must be SKIPPED) and feature/merged-plain (no marker -
# must be auto-cleaned normally, local+remote branch deleted).
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo "init" > README.md && git add . && git commit -qm "init"
mkdir -p .sc
cat > .sc/shared-settings.yaml <<'YAML'
git:
  protected_branches:
    - main
YAML
git add .sc && git commit -qm "declare protected branches"
mkdir -p .claude/scripts
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__

# Both branches point at the same commit as main - trivially merged.
git branch feature/tracked-stack main
git branch feature/merged-plain main

git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main feature/tracked-stack feature/merged-plain

git worktree add -q "$WS/repo-worktrees/feature/tracked-stack" feature/tracked-stack
git worktree add -q "$WS/repo-worktrees/feature/merged-plain" feature/merged-plain

STACK_GITDIR="$(git -C "$WS/repo-worktrees/feature/tracked-stack" rev-parse --git-dir)"
touch "$STACK_GITDIR/gh-stack"
cd "$WS"

# Stub `gh` - cleanup itself never needs to call gh (tracking is a plain
# filesystem marker), this only catches an agent that improvises.
mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
