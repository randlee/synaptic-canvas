#!/usr/bin/env bash
# gh-stack preflight. Exit 0 = safe to run gh stack commands. Each FAIL prints the exact fix.
# Read-only: nothing here modifies the repo; it only reports.
set -u
fail=0
ok()   { echo "OK    $1"; }
bad()  { echo "FAIL  $1"; echo "      fix: $2"; fail=1; }
warn() { echo "WARN  $1"; }

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { bad "not inside a git repo" "cd into the repo"; exit 1; }

# 1. gh + extension + auth
if gh --version >/dev/null 2>&1; then ok "gh CLI present"; else bad "gh CLI missing" "see references/installation-and-troubleshooting.md"; fi
if gh extension list 2>/dev/null | grep -q 'gh-stack'; then ok "gh-stack extension installed"
else bad "gh-stack extension missing" "gh extension install github/gh-stack"; fi
if gh auth status >/dev/null 2>&1; then ok "gh authenticated"; else bad "gh not authenticated" "gh auth login"; fi

# 2. rerere — a conflict resolved once must replay on every upstack rebase
if [ "$(git config --get rerere.enabled)" = "true" ]; then ok "rerere.enabled=true"
else bad "rerere disabled" "git config rerere.enabled true"; fi

# 3. remotes — checkout/trunk have no --remote flag; >1 remote needs pushDefault
nremotes=$(git remote | wc -l | tr -d ' ')
if [ "$nremotes" -eq 0 ]; then bad "no git remote" "git remote add origin <url>"
elif [ "$nremotes" -gt 1 ] && [ -z "$(git config --get remote.pushDefault)" ]; then
  bad "$nremotes remotes and remote.pushDefault unset" "git config remote.pushDefault origin"
else ok "remote configuration ($nremotes remote(s))"; fi

# 4. clean tree — gh stack add carries uncommitted changes onto the new branch
if [ -z "$(git status --porcelain)" ]; then ok "working tree clean"
else bad "working tree has uncommitted changes" "commit or stash before stack operations"; fi

# 5. no rebase in progress (exit 7 / exit 10 conditions)
gitdir=$(git rev-parse --git-dir)
if [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then
  bad "a git rebase is in progress" "gh stack rebase --continue  (or --abort)"
else ok "no rebase in progress"; fi

# 6. stacked PRs enabled on the repo — no direct probe exists; submit exits 9 if not.
warn "cannot verify that stacked PRs are enabled on the repository; 'gh stack submit' exits 9 if not — stop and tell the user"

exit $fail
