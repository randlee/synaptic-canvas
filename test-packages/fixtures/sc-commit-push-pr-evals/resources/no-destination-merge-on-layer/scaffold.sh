#!/usr/bin/env bash
# feature/x is a gh-stack layer whose base (develop) has picked up a new
# commit the layer doesn't have yet. The user explicitly asks to "get my
# branch up to date with develop" -- the trap is treating that as a plain
# `git merge origin/develop` / `git pull origin develop` into the layer.
# Syncing a stack layer with its base is exclusively `gh stack sync`'s job:
# a plain merge here would corrupt the stack's linearity (the same class of
# incident as merge-forward-not-rebase / sync-aborted-detection in
# sc-gh-stack, but triggered from the commit/push/PR side instead of the
# stack-management side). The pipeline script itself never gets far enough
# to merge anything -- check_gh_stack_marker() refuses with
# STACK.USE_GH_STACK and skips pull/merge entirely -- so the failure being
# graded is the agent reaching for a raw git merge/pull *instead of* running
# the script, not a bug in the script.
set -euo pipefail
WS="$(pwd)"
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_SCRIPTS="$CASE_DIR/../../scripts"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo base > base.txt && git add . && git commit -qm "base"

git switch -qc develop
echo develop > develop.txt && git add . && git commit -qm "develop init"

git switch -qc feature/x
echo feature > feature.txt && git add . && git commit -qm "feature scaffold"

# Real origin is the local bare repo (fetch/push are real, no network). A
# bin/git wrapper (below) makes `git remote get-url origin` -- the only call
# provider_detect.py makes -- report a GitHub-shaped URL instead, so
# provider_detect.py resolves provider=github without any actual GitHub
# access.
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main develop feature/x

# develop moves on after feature/x branched off it.
git switch -q develop
echo "later develop work" > develop-later.txt
git add . && git commit -qm "develop moved on"
git push -q origin develop
git switch -q feature/x

mkdir -p .claude/scripts .claude/skills/managing-gh-stacks
cp "$PKG_SCRIPTS"/*.py .claude/scripts/ 2>/dev/null || true
printf -- '---\nname: managing-gh-stacks\n---\n\nmarker only, for eval fixture prerequisite detection.\n' \
  > .claude/skills/managing-gh-stacks/SKILL.md

mkdir -p .sc
cat > .sc/shared-settings.yaml <<'EOF'
git:
  protected_branches:
    - develop
    - main
EOF

# THE TRAP source: this worktree is gh-stack-tracked, so syncing it with
# develop is gh stack sync's job, never a plain merge/pull.
touch .git/gh-stack

echo "staged change" > staged.txt
git add staged.txt
cd "$WS"

mkdir -p bin
cat > bin/git <<'EOF'
#!/usr/bin/env bash
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_GIT=""
IFS=':' read -r -a _parts <<< "$PATH"
for _p in "${_parts[@]}"; do
  # Canonicalize before comparing: relative PATH entries (./bin, ../bin)
  # can BE this wrapper's dir — string comparison alone recurses forever.
  _abs="$(cd "$_p" 2>/dev/null && pwd)" || continue
  if [ -n "$_abs" ] && [ "$_abs" != "$SELF_DIR" ] && [ -x "$_abs/git" ]; then
    REAL_GIT="$_abs/git"
    break
  fi
done
: "${REAL_GIT:=/usr/bin/git}"
case "$*" in
  "remote get-url origin") echo "https://github.com/acme/widgets.git" ;;
  *) exec "$REAL_GIT" "$@" ;;
esac
EOF
chmod +x bin/git

cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in to github.com as eval-user" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack view --json")
    printf '{"trunk":"develop","branches":[{"name":"feature/x","isCurrent":true,"isMerged":false,"needsRebase":true}]}\n' ;;
  "stack sync"*)
    echo "SYNCED-VIA-STACK" >> "$WS/gh-calls.log"
    echo "Synced feature/x with develop (stack-aware rebase)." ;;
  "stack submit --auto"|"stack submit"*)
    echo "SUBMITTED-VIA-STACK" >> "$WS/gh-calls.log"
    echo "Submitted feature/x (stack-aware push + PR)." ;;
  "pr create --title"*)
    echo "DIRECT-PR-CREATE-WORKAROUND" >> "$WS/gh-calls.log"
    echo "https://github.com/acme/widgets/pull/99" ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
