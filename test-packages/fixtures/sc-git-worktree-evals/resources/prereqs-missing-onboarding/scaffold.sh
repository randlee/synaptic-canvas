#!/usr/bin/env bash
# Fixture for DESIGN.md stage 3 (the mandatory prerequisite gate):
# git.always_stack: true makes the repo stack-active, but the gh-stack
# extension is NOT installed (`gh extension list` is empty) and the
# managing-gh-stacks skill is NOT present either. This must refuse with
# CREATE.STACK_PREREQS_MISSING BEFORE any mutation (including `git fetch`) -
# naming the exact install commands - rather than silently falling back to a
# flat worktree or improvising stack operations.
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo "init" > README.md && git add . && git commit -qm "init"
git branch develop main
mkdir -p .sc
cat > .sc/shared-settings.yaml <<'YAML'
git:
  always_stack: true
  stack_root: develop
  protected_branches:
    - main
    - develop
YAML
git add .sc && git commit -qm "declare always_stack policy"
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main develop
mkdir -p .claude/scripts
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__
# Deliberately NO .claude/skills/managing-gh-stacks/SKILL.md marker here.
cd "$WS"

# Stub `gh`: gh CLI itself is present and working, but the gh-stack
# extension is NOT installed - `extension list` returns nothing.
mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") exit 0 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
