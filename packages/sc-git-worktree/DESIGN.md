# sc-git-worktree Design

## Core Principles

1. **Git is source of truth** - Always query git for actual state
2. **JSONL is supplemental metadata** - Tracks owner, created date, purpose
3. **Auto-reconciliation** - JSONL stays in sync via scan
4. **Safe defaults** - Never delete unmerged or remote-ahead branches without explicit approval

## Branch Tracking (JSONL)

### Purpose

The tracking file (`worktree-tracking.jsonl`) stores metadata that git doesn't capture:
- **owner** - Who created the branch (from first commit author)
- **created** - When it was created (from first commit date)
- **purpose** - Why it was created (user-provided)

### Entry Lifecycle

| State | local_worktree | remote_exists | Action |
|-------|----------------|---------------|--------|
| Active worktree | true | true | Keep |
| Local only (not pushed) | true | false | Keep |
| Orphaned remote | false | true | **Keep** until cleanup deletes remote |
| Fully cleaned | false | false | **Remove** from JSONL |

Key rule: Entry is only removed when **both** local worktree and remote branch are gone.

### Schema

```json
{
  "branch": "feature/login",
  "owner": "Rand Lee",
  "created": "2024-01-15T10:30:00Z",
  "purpose": "implement OAuth login",
  "path": "/path/to/worktrees/feature/login",
  "local_worktree": true,
  "remote_exists": true,
  "remote_ahead": 0
}
```

## Operations

### Scan (default)

Reconciles existing JSONL entries with git state:

1. Load JSONL entries
2. For each entry:
   - Update `local_worktree` (does path exist?)
   - Update `remote_exists` (does `origin/<branch>` exist?)
   - Update `remote_ahead` (commits on remote not in local)
   - If `!local_worktree && !remote_exists` → remove entry
3. Save JSONL
4. Report status

### Scan --all

Discovers all remote branches and adds to JSONL:

1. Run default scan first
2. Query all remote branches (e.g., `feature/*`, `hotfix/*`)
3. For each branch not in JSONL:
   - Get first unique commit → extract author + date
   - Add entry with real owner/created
4. Enables cleanup by owner across large repos

### Create

1. Create worktree via git
2. Add JSONL entry with:
   - owner = git config user.name
   - created = now
   - purpose = user-provided
   - local_worktree = true
   - remote_exists = false (until pushed)

### Cleanup (default - batch)

1. Run scan/reconcile to refresh JSONL from git
2. Add untracked local worktrees to JSONL (rogue-agent safety)
2. For each entry:
   - Skip if dirty (uncommitted changes)
   - Skip if unmerged (has unique commits)
   - Skip if `remote_ahead > 0` (remote has unpulled commits)
   - Delete local worktree
   - Delete local branch
   - Delete remote branch
3. Next scan removes entries where both local and remote are gone

### Cleanup --owner="Name"

Filter cleanup to only branches created by specified owner. Useful for cleaning up your own branches in a shared repo with many contributors.

### Cleanup (orphaned remotes)

For entries where `local_worktree=false` and `remote_exists=true`:
- Local was deleted (manually or by rogue agent)
- Remote still exists
- Cleanup deletes the remote branch
- Next scan removes the entry

### Abort

Force-remove a worktree, discarding uncommitted changes:

1. Remove worktree with `--force`
2. Optionally delete branch (requires explicit approval for non-protected)
3. Update JSONL entry (local_worktree=false)
4. Remote deletion handled by subsequent cleanup

## Safety Guards

### Protected Branches

Resolved from `.sc/shared-settings.yaml` (`git.protected_branches`) or auto-detected from gitflow config and cached there:
- Worktree can be removed
- Branch is **never** deleted (local or remote)

### Remote Ahead Check

Before deleting a remote branch:
- Check `git rev-list --count <branch>..origin/<branch>`
- If `remote_ahead > 0`, preserve remote with warning
- Prevents data loss when someone pushed commits you haven't pulled

### Dirty Worktree Check

Before cleanup:
- Check `git status --porcelain`
- If dirty, report files and skip (or require `--force`)

### Unmerged Check

Before cleanup:
- Check `git branch --merged` and unique commit count
- If unmerged, preserve branch and report

## File Layout

```
<repo>/                          # Main repository
<repo>-worktrees/                # Sibling worktree directory
├── worktree-tracking.jsonl      # Tracking metadata
├── feature/
│   └── login/                   # Worktree for feature/login branch
├── hotfix/
│   └── urgent-fix/              # Worktree for hotfix/urgent-fix branch
└── develop/                     # Worktree for develop branch (protected)
```
