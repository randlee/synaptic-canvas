#!/usr/bin/env bash
# Convert N existing branches (each currently based on trunk) into one linear stack.
#
#   scripts/convert.sh <trunk> <bottom-branch-or-PR#> ... <top-branch-or-PR#>
#
# Bottom to top. Arguments may be branch names or PR numbers (resolved via `gh pr view`).
# Idempotent: layers already chained are skipped, so re-run after resolving a conflict.
# Compatible with bash 3.2 (macOS default).
#
# Exit codes:
#   0  all layers chained and `gh stack init` done — next step is `gh stack submit --auto`
#   3  rebase conflict; layer and files printed; resolve, `git add`, `git rebase --continue`, re-run
#   5  bad arguments / missing branch / missing remote trunk
set -u

[ $# -ge 3 ] || { echo "usage: $0 <trunk> <b1> <b2> ... <bN>  (bottom to top, >=2 layers)" >&2; exit 5; }
trunk=$1; shift

remote=$(git config --get remote.pushDefault || true)
[ -n "$remote" ] || remote=$(git remote | head -n1)
[ -n "$remote" ] || { echo "no remote" >&2; exit 5; }

git config rerere.enabled true
git fetch "$remote" --prune || exit 1
# Always chain against the remote trunk tip, never a possibly-stale local trunk.
trunkref="$remote/$trunk"
git show-ref --verify --quiet "refs/remotes/$trunkref" || { echo "trunk not on remote: $trunkref" >&2; exit 5; }

# Resolve PR numbers to head branch names.
branches=()
for a in "$@"; do
  if [[ "$a" =~ ^[0-9]+$ ]]; then
    b=$(gh pr view "$a" --json headRefName -q .headRefName) || { echo "cannot resolve PR #$a" >&2; exit 5; }
    echo "PR #$a -> $b"
  else
    b=$a
  fi
  branches+=("$b")
done
last=${branches[$((${#branches[@]}-1))]}

# Ensure every branch exists locally and tracks the remote.
for b in "${branches[@]}"; do
  if git show-ref --verify --quiet "refs/heads/$b"; then :
  elif git show-ref --verify --quiet "refs/remotes/$remote/$b"; then git branch --track "$b" "$remote/$b" >/dev/null
  else echo "branch not found locally or on $remote: $b" >&2; exit 5; fi
done

echo
echo "target: ($trunk) <- $(IFS=' '; echo "${branches[*]}" | sed 's/ / <- /g')"
echo

# Chain bottom-up. Layer i is rebased onto layer i-1, replaying only commits not already in trunk.
prev=$trunkref
for b in "${branches[@]}"; do
  if git merge-base --is-ancestor "$prev" "$b"; then
    echo "skip   $b  (already on top of $prev)"
  else
    echo "rebase $b  --onto $prev"
    if ! git rebase --onto "$prev" "$trunkref" "$b" >/dev/null 2>&1; then
      echo
      echo "CONFLICT in layer: $b (rebasing onto $prev)"
      git diff --name-only --diff-filter=U | sed 's/^/  /'
      echo
      echo "resolve the files above, then:"
      echo "  git add <files> && git rebase --continue"
      echo "  $0 $trunk ${branches[*]}     # re-run; finished layers are skipped"
      exit 3
    fi
  fi
  prev=$b
done

git checkout -q "$last"

# Adopt the chained branches as a stack (init adopts existing branches; nothing is pushed yet).
if gh stack view --json >/dev/null 2>&1; then
  echo "existing local stack detected; leaving it. If its composition differs: gh stack unstack --local, then re-run."
else
  gh stack init --base "$trunk" "${branches[@]}" || exit $?
fi

echo
gh stack view --json
echo
echo "NEXT: review the JSON above (every branch listed, bottom-to-top order, needsRebase=false),"
echo "      then push and fix PR bases with:   gh stack submit --auto"
