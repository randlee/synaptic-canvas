#!/usr/bin/env bash
# Prerequisite-gate fixture: same ordinary (non-stack) branch as
# non-stack-flow-normal, but the gh-stack toolchain is NOT installed --
# the stub's `gh extension list` omits gh-stack, and no
# managing-gh-stacks/SKILL.md marker exists anywhere the script looks. The
# unconditional hard gate in stack_guard.check_stack_prerequisites() must
# refuse with PREFLIGHT.STACK_PREREQS_MISSING before any git mutation,
# listing the exact install steps for BOTH missing pieces -- regardless of
# this branch never being a stack layer.
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
git push -q origin main develop

mkdir -p .claude/scripts
cp "$PKG_SCRIPTS"/*.py .claude/scripts/ 2>/dev/null || true
# Deliberately NOT creating .claude/skills/managing-gh-stacks/SKILL.md, and
# HOME is redirected by the harness to an isolated dir with no such skill
# either -- both prereqs (extension + skill) are missing.

mkdir -p .sc
cat > .sc/shared-settings.yaml <<'EOF'
git:
  protected_branches:
    - develop
    - main
EOF

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
  "extension list") echo "some-other-ext  someone/other  v1.0.0" ;;
  "pr create --title"*)
    echo "PR-CREATE-BEFORE-INSTALL" >> "$WS/gh-calls.log"
    echo "https://github.com/acme/widgets/pull/1" ;;
  "extension install github/gh-stack")
    echo "INSTALLED-GH-STACK" >> "$WS/gh-calls.log"
    echo "Installed extension github/gh-stack" ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
