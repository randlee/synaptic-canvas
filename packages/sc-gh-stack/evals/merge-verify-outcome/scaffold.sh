#!/usr/bin/env bash
# Happy-path landing with mandatory post-merge verification. Both PRs ARE tracked
# in the stack; `gh stack merge` really merges them into main (in the fixture's
# origin). The graders check the agent verified MERGED state + VERSION on main
# before reporting, per the "ideal transcript is ~4 calls" incident note.
set -euo pipefail
WS="$(pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo 0.5.0 > VERSION && git add . && git commit -qm "base 0.5.0"
git switch -qc release/bump  && echo 0.6.0 > VERSION  && git commit -qam "bump to 0.6.0"
git switch -qc release/notes && echo notes > NOTES.md && git add . && git commit -qm "notes"
git switch -q main
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main release/bump release/notes
cd "$WS"

mkdir -p bin
cat > bin/gh <<'EOF'
#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "gh $*" >> "$WS/gh-calls.log"
merged() { [ -f "$WS/.merged" ]; }
case "$*" in
  --version) echo "gh version 2.60.0" ;;
  "auth status") echo "Logged in" ;;
  "extension list") echo "gh stack  github/gh-stack  v0.1.0" ;;
  "stack view --json")
    if merged; then M=true; else M=false; fi
    printf '{"trunk":"main","branches":[{"name":"release/bump","isCurrent":false,"isMerged":%s,"needsRebase":false,"pr":148},{"name":"release/notes","isCurrent":false,"isMerged":%s,"needsRebase":false,"pr":149}]}\n' "$M" "$M" ;;
  "pr view 148"*|"pr view 149"*)
    if merged; then echo '{"state":"MERGED","mergedAt":"2026-08-30T12:00:00Z"}'
    else echo '{"state":"OPEN","mergedAt":null}'; fi ;;
  "stack merge"*)
    # Really land bottom-up in the fixture repo and push, like upstream would.
    git -C "$WS/repo" switch -q main
    git -C "$WS/repo" merge -q --no-ff --no-edit release/bump
    git -C "$WS/repo" merge -q --no-ff --no-edit release/notes
    git -C "$WS/repo" push -q origin main
    touch "$WS/.merged"
    echo "Merged #148, #149. 2 PRs merged." ;;
  "stack sync --prune"|"stack sync"*) echo "Synced." ;;
  "pr merge"*) echo "refusing: this pull request is part of a stack" >&2; exit 1 ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
