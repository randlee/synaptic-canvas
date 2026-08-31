#!/usr/bin/env bash
# Baseline/control fixture: an ordinary (non-stack) branch, gh-stack toolchain
# prerequisites fully present, no gh-stack marker on the worktree. Everything
# here should proceed exactly like it did before sc-commit-push-pr grew
# gh-stack awareness -- no refusal codes, no `gh stack` commands, a real
# `gh pr create` at the end. This is the control case the other three cases'
# guarded failure modes are contrasted against.
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
# access. (`git config url.<x>.insteadOf` was tried first but it also
# rewrites what `remote get-url` itself reports, defeating the split.)
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main develop

mkdir -p .claude/scripts .claude/skills/managing-gh-stacks
cp "$PKG_SCRIPTS"/*.py .claude/scripts/ 2>/dev/null || true
# Marker: managing-gh-stacks skill installed (satisfies the prerequisite gate).
printf -- '---\nname: managing-gh-stacks\n---\n\nmarker only, for eval fixture prerequisite detection.\n' \
  > .claude/skills/managing-gh-stacks/SKILL.md

mkdir -p .sc
cat > .sc/shared-settings.yaml <<'EOF'
git:
  protected_branches:
    - develop
    - main
EOF

# The staged-but-uncommitted change the prompt refers to.
echo "staged change" > staged.txt
git add staged.txt
cd "$WS"

mkdir -p bin
cat > bin/git <<'EOF'
#!/usr/bin/env bash
# Passthrough wrapper: reports a GitHub-shaped URL for `remote get-url
# origin` (the only call provider_detect.py makes) so the fixture's provider
# resolves to github without touching real fetch/push transport, which stay
# on the real local bare repo untouched.
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
  "pr list --head feature/x --base develop --json number,url,headRefName,baseRefName --limit 1")
    echo "[]" ;;
  "pr create --title"*)
    echo "PR-CREATED" >> "$WS/gh-calls.log"
    echo "https://github.com/acme/widgets/pull/42" ;;
  "stack "*) echo "stub: unexpected gh stack call in the non-stack baseline: gh $*" >&2; exit 64 ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
