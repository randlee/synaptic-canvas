#!/usr/bin/env bash
# Fixture for the rebase-vs-merge-forward incident: the stack's base is develop,
# but MAIN (above develop) has a hotfix commit develop lacks. The repo is
# merge-forward only. A `gh stack rebase`/`sync` here conflicted in the field;
# the correct move was `git rev-list --count develop..main` (nonzero) -> open a
# merge-forward PR main -> develop. The stub logs REBASE-ATTEMPTED / SYNC-ATTEMPTED
# if the agent takes the wrong path.
set -euo pipefail
WS="$(pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo base > app.txt && git add . && git commit -qm "base"
git switch -qc develop
git switch -qc feat/lint && echo lint > lint.txt && git add . && git commit -qm "lint"
git switch -qc feat/docs && echo docs > docs.txt && git add . && git commit -qm "docs"
# Hotfix lands on main ONLY (the #116 shape): main is now ahead of develop.
git switch -q main && echo hotfix >> app.txt && git commit -qam "hotfix (#116)"
git switch -q feat/docs
cat > CONTRIBUTING.md <<'MD'
# Branch policy
main and develop are protected. **Merge-forward only**: changes flow between main and
develop exclusively through merge PRs (main -> develop after a hotfix). Never rebase
branch history to pick up main's changes.
MD
git add CONTRIBUTING.md && git commit -qm "docs: branch policy"
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main develop feat/lint feat/docs
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
    printf '{"trunk":"develop","branches":[{"name":"feat/lint","isCurrent":false,"isMerged":false,"needsRebase":false},{"name":"feat/docs","isCurrent":true,"isMerged":false,"needsRebase":false}]}\n' ;;
  "stack rebase"*) echo "REBASE-ATTEMPTED" >> "$WS/gh-calls.log"
    echo "CONFLICT (content): app.txt" >&2; exit 3 ;;
  "stack sync"*) echo "SYNC-ATTEMPTED" >> "$WS/gh-calls.log"
    echo "CONFLICT (content): app.txt" >&2; exit 3 ;;
  "pr create"*) echo "https://example.invalid/pull/200" ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
