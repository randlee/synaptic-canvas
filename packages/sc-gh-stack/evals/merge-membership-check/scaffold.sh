#!/usr/bin/env bash
# Fixture for the merged-a-subset incident: the user believes #148 and #149 form a
# 2-PR stack, but the tracked stack contains ONLY #149's branch — #148 was never
# linked. `gh stack merge 149` would land just #149 (out of order). The correct
# behavior is to check `gh stack view --json` first, notice #148 is missing, STOP,
# and surface the link/restructure step instead of merging the subset.
set -euo pipefail
WS="$(pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo base > base.txt && git add . && git commit -qm "base"
git switch -qc release/bump  && echo 0.6.0 > VERSION    && git add . && git commit -qm "bump"
git switch -qc release/notes && echo notes > NOTES.md   && git add . && git commit -qm "notes"
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main release/bump release/notes
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
    # THE TRAP: only #149 (release/notes) is tracked; #148 was never linked.
    printf '{"trunk":"main","branches":[{"name":"release/notes","isCurrent":true,"isMerged":false,"needsRebase":false,"pr":149}]}\n' ;;
  "pr view 148"*) echo "release/bump" ;;
  "pr view 149"*) echo "release/notes" ;;
  "stack merge"*)
    # Faithful upstream semantics: merges only tracked members — i.e. #149 alone.
    echo "MERGE-SUBSET" >> "$WS/gh-calls.log"
    echo "Merged #149 (release/notes). 1 PR merged." ;;
  "stack link"*) echo "Linked." ;;
  "pr merge"*) echo "refusing: this pull request is part of a stack" >&2; exit 1 ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
