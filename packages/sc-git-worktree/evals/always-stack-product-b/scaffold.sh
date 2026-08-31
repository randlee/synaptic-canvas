#!/usr/bin/env bash
# Fixture for DESIGN.md stage 5 (Policy): git.always_stack: true, stack_root
# develop (develop exists), and all mandatory prerequisites present (gh CLI,
# gh-stack extension, the managing-gh-stacks skill marker). Creating off
# develop (an independent base - it IS the stack_root) with the base
# genuinely independent must resolve to product B: SAME path a flat worktree
# would use (no `stack/` prefix anywhere), plus `git config rerere.enabled
# true` and `gh stack init --base develop <branch>` in the new worktree.
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
mkdir -p .claude/scripts .claude/skills/managing-gh-stacks
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__
# Marker for check_sc_gh_stack_skill - the mandatory prerequisite gate looks
# for this exact path under the repo root.
echo "# managing-gh-stacks" > .claude/skills/managing-gh-stacks/SKILL.md
git add .claude && git commit -qm "install managing-gh-stacks skill marker"
git push -q origin main
cd "$WS"

# Stub `gh`: extension IS installed, stack init succeeds.
mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack init"*) echo "Stack initialized."; exit 0 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
