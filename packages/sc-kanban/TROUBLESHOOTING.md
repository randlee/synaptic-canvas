# Troubleshooting (sc-kanban)

Common issues, diagnostics, and solutions for sc-kanban v0.7.0.

---

## Issue 1: Board Config Invalid (Schema Validation Errors)

**Symptom**: Agent fails with `CONFIG.INVALID` error when attempting any operation.

**Root Cause**: Board config YAML has missing required fields, wrong field types, invalid values, or unsupported version.

### Diagnostic Steps

1. Check config file exists:
   ```bash
   ls -la .project/board.config.yaml
   ```

2. Validate YAML syntax:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('.project/board.config.yaml'))"
   ```

3. Check for validation errors:
   ```bash
   python3 -m sc_cli.board_config --validate .project/board.config.yaml
   ```

### Solution

1. Verify required fields present:
   - `version: 0.7`
   - `board.backlog_path`
   - `board.board_path`
   - `board.done_path`
   - `board.provider` (must be "kanban" or "checklist")

2. Fix common issues:
   ```yaml
   # WRONG: Missing version
   board:
     provider: kanban

   # CORRECT: Version specified
   version: 0.7
   board:
     provider: kanban
   ```

3. Use template as reference:
   ```bash
   cp templates/board.config.example.yaml .project/board.config.yaml
   # Edit with your paths
   ```

### Example

Error:
```
CONFIG.INVALID: Missing required field 'version'
```

Fix:
```yaml
version: 0.7  # Add this line
board:
  backlog_path: .project/backlog.json
  board_path: .project/board.json
  done_path: .project/done.json
  provider: kanban
```

---

## Issue 2: Card Not Found

**Symptom**: Query or transition fails with `CARD.NOT_FOUND` error.

**Root Cause**: Selector (sprint_id or worktree) doesn't match any card, or card is in wrong file (backlog vs board vs done).

### Diagnostic Steps

1. Check all three files for the card:
   ```bash
   grep "1.1" .project/backlog.json
   grep "1.1" .project/board.json
   grep "1.1" .project/done.json
   ```

2. Verify exact field values (case-sensitive):
   ```bash
   cat .project/board.json | python3 -m json.tool | grep -A5 "sprint_id"
   ```

3. List all cards to find correct selector:
   ```bash
   kanban-query --file .project/board.json
   ```

### Solution

1. Ensure selector matches card exactly:
   - Sprint ID: `"1.1"` not `"1-1"` or `"sprint-1.1"`
   - Worktree: `"main/1-1-project-setup"` not `"main/1.1-project-setup"`

2. Check if card is in expected file:
   - Backlog cards: use `--file .project/backlog.json`
   - Board cards: use `--file .project/board.json`
   - Done cards: use `--file .project/done.json`

3. Recreate card if missing:
   ```bash
   kanban-card create --target-status planned \
     --card '{"sprint_id":"1.1","title":"Project Setup","worktree":"main/1-1-setup"}'
   ```

### Example

Error:
```json
{
  "error": {
    "code": "CARD.NOT_FOUND",
    "message": "No card found with sprint_id=1-1"
  }
}
```

Fix:
```bash
# Use correct sprint_id format (dot not dash)
kanban-transition --sprint-id 1.1 --target-status active
```

---

## Issue 3: Provider Mismatch (Checklist vs Kanban)

**Symptom**: Agent returns `PROVIDER.CHECKLIST` advisory error when attempting kanban operations.

**Root Cause**: Board config has `provider: checklist` but kanban agents are being called.

### Diagnostic Steps

1. Check provider setting:
   ```bash
   grep "provider:" .project/board.config.yaml
   ```

2. Verify which agent is appropriate:
   - `provider: kanban` → Use kanban-transition, kanban-query, kanban-card
   - `provider: checklist` → Use checklist-agent

### Solution

**Option A: Switch to Kanban Provider**

1. Edit board config:
   ```yaml
   board:
     provider: kanban  # Change from checklist
   ```

2. Create JSON files:
   ```bash
   echo '[]' > .project/backlog.json
   echo '[]' > .project/board.json
   echo '[]' > .project/done.json
   ```

**Option B: Use Checklist Agent**

1. Keep `provider: checklist` in config

2. Call checklist agent instead:
   ```bash
   checklist-agent query --sprint-id 1.1
   checklist-agent update --sprint-id 1.1 --status active
   ```

### Example

Advisory error:
```json
{
  "success": false,
  "error": {
    "code": "PROVIDER.CHECKLIST",
    "message": "Board config provider=checklist; call checklist agent",
    "suggested_action": "Invoke checklist-agent/query-update with same card selector"
  }
}
```

Resolution: Use checklist-agent or switch provider to kanban.

---

## Issue 4: Scrubbing Missing Fields

**Symptom**: Transition to done fails with `SCRUB.MISSING_FIELD` error.

**Root Cause**: Card lacks required lean fields (`sprint_id`, `title`) that must be preserved in done.json.

### Diagnostic Steps

1. Inspect card before archiving:
   ```bash
   kanban-query --sprint-id 1.1
   ```

2. Check for missing required fields:
   - `sprint_id` (required)
   - `title` (required)

### Solution

1. Add missing fields before archiving:
   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"title":"Project Setup"}'
   ```

2. Retry transition:
   ```bash
   kanban-transition --sprint-id 1.1 --target-status done
   ```

### Example

Error:
```json
{
  "error": {
    "code": "SCRUB.MISSING_FIELD",
    "message": "Card missing required field 'title' for scrubbing"
  }
}
```

Fix:
```bash
# Add title field
kanban-card update --sprint-id 1.1 --card '{"title":"Project Setup"}'

# Retry archive
kanban-transition --sprint-id 1.1 --target-status done
```

---

## Issue 5: Missing Dependencies (PyYAML, pydantic)

**Symptom**: Import errors or module not found when running agents.

**Root Cause**: Required Python packages not installed.

### Diagnostic Steps

1. Check Python version:
   ```bash
   python3 --version  # Should be 3.8+
   ```

2. Test imports:
   ```bash
   python3 -c "import yaml; import pydantic"
   ```

### Solution

1. Install from requirements file:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Or install packages directly:
   ```bash
   pip install PyYAML pydantic
   ```

3. Verify installation:
   ```bash
   python3 -c "import yaml, pydantic; print('Success')"
   ```

### Example

Error:
```
ModuleNotFoundError: No module named 'yaml'
```

Fix:
```bash
pip install PyYAML pydantic
```

---

## Issue 6: WIP Limit Exceeded

**Symptom**: Transition fails with `WIP.EXCEEDED` error when moving card to active or review column.

**Root Cause**: Target column already contains maximum allowed cards per WIP limit in board config.

### Diagnostic Steps

1. Check current WIP limits:
   ```bash
   grep -A5 "wip:" .project/board.config.yaml
   ```

2. Count cards in target column:
   ```bash
   kanban-query --status review | grep -c "sprint_id"
   ```

### Solution

**Option A: Complete Existing Work**

1. Archive completed cards:
   ```bash
   kanban-transition --sprint-id 1.1 --target-status done
   ```

2. Retry transition after freeing space.

**Option B: Increase WIP Limit**

1. Edit board config:
   ```yaml
   board:
     wip:
       per_column:
         active: 5    # Increase from 3
         review: 3    # Increase from 2
   ```

2. Retry transition.

### Example

Error:
```json
{
  "error": {
    "code": "WIP.EXCEEDED",
    "message": "Review column WIP limit (2) exceeded",
    "suggested_action": "Complete existing review items or increase WIP limit"
  }
}
```

Current state: 2 cards in review, limit is 2.

Fix: Archive one review card, then retry transition.

---

## Issue 7: PR URL Gate Failure

**Symptom**: Transition from active → review or review → done fails requiring pr_url.

**Root Cause**: Card missing `pr_url` field, which is required gate in v0.7.0.

### Diagnostic Steps

1. Check card for pr_url:
   ```bash
   kanban-query --sprint-id 1.1 | grep pr_url
   ```

### Solution

1. Add PR URL to card:
   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"pr_url":"https://github.com/org/repo/pull/42"}'
   ```

2. Retry transition:
   ```bash
   kanban-transition --sprint-id 1.1 --target-status review
   ```

### Example

Error:
```json
{
  "error": {
    "code": "GATE.VALIDATION",
    "message": "PR URL required before review",
    "suggested_action": "Add pr_url to card using kanban-card update, then retry"
  }
}
```

Fix:
```bash
kanban-card update --sprint-id 1.1 \
  --card '{"pr_url":"https://github.com/org/repo/pull/42"}'
```

---

## Issue 8: File Permission Errors

**Symptom**: Cannot write to backlog.json, board.json, or done.json with permission denied error.

**Root Cause**: Insufficient file permissions or directory doesn't exist.

### Diagnostic Steps

1. Check file permissions:
   ```bash
   ls -la .project/*.json
   ```

2. Check directory permissions:
   ```bash
   ls -lad .project
   ```

### Solution

1. Fix file permissions:
   ```bash
   chmod 644 .project/*.json
   ```

2. Fix directory permissions:
   ```bash
   chmod 755 .project
   ```

3. Create directory if missing:
   ```bash
   mkdir -p .project
   ```

4. Initialize files if missing:
   ```bash
   echo '[]' > .project/backlog.json
   echo '[]' > .project/board.json
   echo '[]' > .project/done.json
   ```

### Example

Error:
```
PermissionError: [Errno 13] Permission denied: '.project/board.json'
```

Fix:
```bash
chmod 644 .project/board.json
```

---

## Issue 9: Card Duplication Across Files

**Symptom**: Same sprint_id appears in multiple files (backlog.json, board.json, done.json).

**Root Cause**: Manual editing of JSON files or interrupted transitions created duplicates.

### Diagnostic Steps

1. Search for sprint_id across all files:
   ```bash
   grep "\"sprint_id\": \"1.1\"" .project/*.json
   ```

### Solution

1. Determine correct location:
   - Backlog: Unplanned work (lean fields only)
   - Board: Active/review work (rich fields)
   - Done: Completed work (scrubbed lean)

2. Manually remove duplicates:
   ```bash
   # Edit files to keep card in only one location
   vim .project/backlog.json  # Remove if also in board
   vim .project/board.json    # Keep if active/review
   ```

3. Validate JSON after editing:
   ```bash
   python3 -m json.tool .project/board.json > /dev/null && echo "Valid"
   ```

### Example

Found in two files:
```bash
$ grep "1.1" .project/*.json
.project/backlog.json:  "sprint_id": "1.1"
.project/board.json:    "sprint_id": "1.1"
```

Fix: Remove from backlog.json, keep in board.json (active work).

---

## Issue 10: Invalid Card Schema

**Symptom**: Card creation or update fails with Pydantic validation error.

**Root Cause**: Card JSON has missing required fields, wrong field types, or unsupported fields.

### Diagnostic Steps

1. Identify validation error:
   ```bash
   kanban-card create --card '{"sprint_id":1.1}' 2>&1 | grep "validation error"
   ```

### Solution

1. Fix common schema issues:
   - Sprint ID must be string: `"1.1"` not `1.1`
   - Worktree required for board cards
   - Arrays must use array syntax: `["item1","item2"]` not `"item1,item2"`

2. Reference field types:
   - `sprint_id`: string (required)
   - `title`: string (required for done)
   - `worktree`: string (required for board)
   - `acceptance_criteria`: array of strings
   - `actual_cycles`: integer
   - `max_retries`: integer

3. Use correct format:
   ```bash
   kanban-card create --card '{
     "sprint_id": "1.1",
     "title": "Project Setup",
     "worktree": "main/1-1-setup",
     "acceptance_criteria": ["Build succeeds", "Tests pass"]
   }'
   ```

### Example

Error:
```
ValidationError: sprint_id must be string, got int
```

Fix:
```bash
# WRONG: sprint_id as number
--card '{"sprint_id":1.1}'

# CORRECT: sprint_id as string
--card '{"sprint_id":"1.1"}'
```

---

## Issue 11: Board Config Path Not Found

**Symptom**: Agent fails to find board config at default or specified path.

**Root Cause**: Config file doesn't exist at expected location or wrong path provided.

### Diagnostic Steps

1. Check default location:
   ```bash
   ls -la .project/board.config.yaml
   ```

2. Search for config file:
   ```bash
   find . -name "board.config.yaml"
   ```

### Solution

1. Create config from template:
   ```bash
   mkdir -p .project
   cp templates/board.config.example.yaml .project/board.config.yaml
   ```

2. Edit paths in config:
   ```yaml
   version: 0.7
   board:
     backlog_path: .project/backlog.json
     board_path: .project/board.json
     done_path: .project/done.json
     provider: kanban
   ```

3. Initialize JSON files:
   ```bash
   echo '[]' > .project/backlog.json
   echo '[]' > .project/board.json
   echo '[]' > .project/done.json
   ```

4. Specify custom path if needed:
   ```bash
   kanban-query --config /path/to/board.config.yaml
   ```

### Example

Error:
```
FileNotFoundError: .project/board.config.yaml not found
```

Fix:
```bash
cp templates/board.config.example.yaml .project/board.config.yaml
```

---

## Issue 12: Gate Execution Failures (v0.7.1+)

**Symptom**: Transition fails with gate validation errors for PR state, git cleanliness, or worktree validation.

**Root Cause**: Future v0.7.1 gates detect uncommitted changes, unmerged PR, or missing worktree.

**Note**: Full gate suite deferred to v0.7.1. Currently only pr_url presence checked in v0.7.0.

### Expected Diagnostics (v0.7.1)

1. Check git status:
   ```bash
   git status --porcelain
   ```

2. Check PR state:
   ```bash
   gh pr view 42 --json state,mergeable
   ```

3. Verify worktree exists:
   ```bash
   test -d ../worktrees/main/1-1-setup && echo "Exists" || echo "Missing"
   ```

### Expected Solutions (v0.7.1)

**Git Cleanliness Gate**:
```bash
git add .
git commit -m "Complete sprint 1.1"
git push
```

**PR Merge Gate**:
```bash
gh pr merge 42 --squash
```

**Worktree Cleanup Gate**:
```bash
sc-git-worktree cleanup main/1-1-setup
```

### Example (v0.7.1)

Error:
```json
{
  "error": {
    "code": "GIT.DIRTY",
    "message": "Worktree has uncommitted changes",
    "suggested_action": "Commit and push changes before transitioning to review"
  }
}
```

Fix: Commit changes, then retry transition.

---

## Additional Resources

- **README.md**: Installation and quick start
- **USE-CASES.md**: 7 detailed workflow scenarios
- **board.config.example.yaml**: Configuration reference
- **GitHub Issues**: https://github.com/randlee/synaptic-canvas/issues

For issues not covered here, please file a GitHub issue with:
- sc-kanban version
- Board config (sanitized)
- Full error message
- Steps to reproduce
