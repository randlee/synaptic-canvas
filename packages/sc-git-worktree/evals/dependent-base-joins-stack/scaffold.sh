#!/usr/bin/env bash
# Fixture for DESIGN.md stage 4 (Dependency) -> product C: feat/bottom is
# unmerged and already checked out in its own worktree carrying gh-stack
# tracking (the `gh-stack` marker under that worktree's git-dir - simulating
# what `gh stack init` leaves behind). The repo is therefore stack-active via
# the tracking-marker signal alone (no always_stack needed). Creating
# feature/next off feat/bottom must join that EXISTING stack worktree as a
# new layer - NO new worktree directory - via `git checkout -b` + `gh stack
# add`, per "Product C" in DESIGN.md.
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo "init" > README.md && git add . && git commit -qm "init"
# Protected branches must be resolvable (no always_stack here - stack
# activity comes from the tracking marker alone) so the dependency stage
# doesn't fail closed to "independent" for lack of a configured trunk.
mkdir -p .sc
cat > .sc/shared-settings.yaml <<'YAML'
git:
  protected_branches:
    - main
YAML
git add .sc && git commit -qm "declare protected branches"
git switch -qc feat/bottom
echo "on-bottom" > bottom.txt && git add . && git commit -qm "wip on feat/bottom"
git switch -q main
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main feat/bottom
mkdir -p .claude/scripts .claude/skills/managing-gh-stacks
cp "$CASE_DIR"/../../scripts/*.py .claude/scripts/ 2>/dev/null || true
rm -rf .claude/scripts/__pycache__
echo "# managing-gh-stacks" > .claude/skills/managing-gh-stacks/SKILL.md

# feat/bottom's own worktree, at the same sibling path a create would have
# used, carrying gh-stack tracking (this IS "the stack lives here").
git worktree add -q "$WS/repo-worktrees/feat/bottom" feat/bottom
STACK_GITDIR="$(git -C "$WS/repo-worktrees/feat/bottom" rev-parse --git-dir)"
touch "$STACK_GITDIR/gh-stack"
cd "$WS"

# Stub `gh`: extension is installed, `stack add` succeeds.
mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack add"*) echo "Added to stack."; exit 0 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
