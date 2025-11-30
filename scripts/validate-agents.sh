#!/usr/bin/env bash
# Validates that agent frontmatter versions match .claude/agents/registry.yaml
# Requires: yq (https://github.com/mikefarah/yq)
set -euo pipefail

REG=".claude/agents/registry.yaml"
if [[ ! -f "$REG" ]]; then
  echo "ERROR: Registry not found: $REG" >&2
  exit 1
fi

frontmatter() {
  awk 'f{print} /^---/{f=1;c++} c==2{exit}' "$1" | sed '1d'
}

fail=0
shopt -s nullglob
for agent in .claude/agents/*.md; do
  name=$(basename "$agent" .md)
  file_ver=$(frontmatter "$agent" | yq -r '.version' || echo "")
  reg_ver=$(yq -r ".agents.\"$name\".version" "$REG" || echo "")

  if [[ -z "$file_ver" || -z "$reg_ver" ]]; then
    echo "ERROR: $name missing version (file='$file_ver' registry='$reg_ver')"
    fail=1; continue
  fi
  if [[ "$file_ver" != "$reg_ver" ]]; then
    echo "ERROR: $name version mismatch: file=$file_ver registry=$reg_ver"
    fail=1
  fi
done

# Validate skill constraints (optional)
if yq -e '.skills' "$REG" >/dev/null 2>&1; then
  for skill in $(yq -r '.skills | keys[]' "$REG"); do
    deps=$(yq -r ".skills.\"$skill\".depends_on | keys[]" "$REG" 2>/dev/null || true)
    for agent in $deps; do
      agent_ver=$(yq -r ".agents.\"$agent\".version" "$REG" 2>/dev/null || echo "")
      constraint=$(yq -r ".skills.\"$skill\".depends_on.\"$agent\"" "$REG")

      if [[ -z "$agent_ver" ]]; then
        echo "ERROR: Skill '$skill' depends on undefined agent '$agent'"
        fail=1
        continue
      fi

      # Simple major-version check for constraints like "1.x"
      if [[ "$constraint" =~ ^([0-9]+)\.x$ ]]; then
        major="${BASH_REMATCH[1]}"
        agent_major="${agent_ver%%.*}"
        if [[ "$agent_major" != "$major" ]]; then
          echo "ERROR: Skill '$skill' requires $agent $constraint, but registry has $agent_ver"
          fail=1
        fi
      fi
    done
  done
fi

shopt -u nullglob

if [[ $fail -eq 0 ]]; then
  echo "All agent versions validated"
else
  exit 1
fi
