#!/usr/bin/env bash
# Fixture: stack (main) <- feat/core <- feat/api where feat/core (the root of the
# stack) is AHEAD of feat/api — GitHub reports needsRebase on feat/api, a purely
# local look at feat/api's diff shows nothing wrong. Conflict-free cascade needed.
#
# The stub `gh` in ./bin self-locates its workspace; the case's `env:` frontmatter
# puts ./bin and ../bin on PATH so the stub wins wherever the agent cd's.
set -euo pipefail
WS="$(pwd)"

git init -q -b main repo
cd repo
git config user.email eval@example.com && git config user.name eval
echo base > base.txt && git add . && git commit -qm "base"
git switch -qc feat/core && echo core > core.txt && git add . && git commit -qm "core"
git switch -qc feat/api && echo api > api.txt && git add . && git commit -qm "api"
# Root of the stack moves ahead AFTER feat/api was cut:
git switch -q feat/core && echo more >> core.txt && git commit -qam "core: fix"
git switch -q feat/api
git init -q --bare "$WS/origin.git"
git remote add origin "$WS/origin.git"
git push -q origin main feat/core feat/api
cd "$WS"

# Stub gh: `stack view --json` reports needsRebase on feat/api until
# `stack rebase --upstack` has run (state file flips it). Records every call.
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
    if [ -f "$WS/.rebased" ]; then NR=false; else NR=true; fi
    printf '{"trunk":"main","branches":[{"name":"feat/core","isCurrent":false,"isMerged":false,"needsRebase":false},{"name":"feat/api","isCurrent":true,"isMerged":false,"needsRebase":%s}]}\n' "$NR" ;;
  "stack rebase --upstack"|"stack rebase"*)
    # Simulate the conflict-free cascade: replay feat/api onto the new feat/core.
    git -C "$WS/repo" rebase --onto feat/core "$(git -C "$WS/repo" merge-base feat/core feat/api)" feat/api -q
    touch "$WS/.rebased"
    echo "Rebased feat/api onto feat/core (no conflicts)" ;;
  "stack checkout"*) git -C "$WS/repo" switch -q "${@: -1}" 2>/dev/null || true ;;
  "stack sync"*) touch "$WS/.rebased"; echo "Synced" ;;
  api*) echo "stub: REST calls are not the answer here" >&2; exit 1 ;;
  *) echo "stub: unhandled: gh $*" >&2; exit 64 ;;
esac
EOF
chmod +x bin/gh
: > gh-calls.log
