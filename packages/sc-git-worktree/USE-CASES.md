# sc-git-worktree Use Cases

## Introduction

The `sc-git-worktree` package enables efficient parallel development workflows by allowing you to create, manage, and clean up isolated git worktrees. Instead of constantly switching branches in a single directory, you can work on multiple branches simultaneously in separate directories with full git context and safety guarantees.

These use cases demonstrate how `sc-git-worktree` streamlines feature development, release management, hotfix workflows, and team collaboration while maintaining a clean repository state.

---

## Use Case 1: Feature Branch Isolation for Parallel Development

**Scenario/Context:**
You're working on a project with multiple concurrent features: Feature X, Feature Y, and a bug fix. Instead of constantly switching branches and rebuilding dependencies, you want isolated directories for each feature where you can work without interference.

**Step-by-step Walkthrough:**

1. Check current worktree status:
   ```
   /sc-git-worktree --status
   ```
   Output:
   ```
   Repository: my-app
   Worktree Base: ../my-app-worktrees/

   Current Worktrees:
   - main (primary, path: /Users/dev/my-app)

   Tracking: ../my-app-worktrees/worktree-tracking.md exists
   ```

2. Create worktree for Feature X based on develop:
   ```
   /sc-git-worktree --create feature-x develop
   ```
   Expected output:
   ```
   Creating worktree for feature-x from develop...
   Created: ../my-app-worktrees/feature-x
   Branch: feature-x tracking develop
   Status: Success
   Tracking updated: ../my-app-worktrees/worktree-tracking.md
   ```

3. Switch to the feature-x directory and work:
   ```bash
   cd ../my-app-worktrees/feature-x
   npm install
   npm run build
   # Now make changes to feature-x
   ```

4. While working on feature-x, create worktree for Feature Y:
   ```bash
   # From original repo directory (or use absolute path)
   /sc-git-worktree --create feature-y develop
   ```

5. Similarly, create a hotfix branch:
   ```
   /sc-git-worktree --create bug-fix-critical develop
   ```

6. Now you have parallel directories for all three features:
   ```
   my-app/                              (main/primary)
   my-app-worktrees/
   ├── feature-x/                       (your active development)
   ├── feature-y/                       (someone else's work or future task)
   ├── bug-fix-critical/                (urgent issue fixing)
   └── worktree-tracking.md             (tracking document)
   ```

7. Work independently in each directory without branch switching overhead

**Expected Outcomes:**
- Three independent working directories
- No branch switching latency
- Each has its own git state, node_modules, build artifacts
- Tracking document shows who's working on what
- Can compile/build independently

**Benefits of Using This Approach:**
- Eliminate branch switching overhead (no cache invalidation)
- Parallel development without conflicts
- Each feature has complete build artifacts
- Easy to track what's in progress (tracking.md)
- Faster development cycle (no rebuild on every switch)
- Clear isolation of work

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-create agent](agents/sc-worktree-create.md)
- [sc-worktree-scan agent](agents/sc-worktree-scan.md)

**Tips and Best Practices:**
- Worktree base directory: `../{{REPO_NAME}}-worktrees/` (sibling to repo)
- Naming convention: descriptive branch names (feature-user-auth, bug-memory-leak)
- Always create from a common base (develop or main) to ensure consistency
- Keep tracking document updated (automatically done by the command)
- One developer per worktree typically (or coordinate carefully)

**Common Pitfalls to Avoid:**
- Creating worktrees with the same branch name (use unique names)
- Creating worktrees in the repo directory instead of sibling
- Forgetting to checkout the worktree directory to work in it
- Leaving dirty worktrees uncleanable (commit or stash before cleanup)

**Variations for Different Scenarios:**

**Creating multiple features quickly:**
```
/sc-git-worktree --create feature-auth develop
/sc-git-worktree --create feature-payment develop
/sc-git-worktree --create feature-notifications develop
```

**Long-running research branch:**
```
/sc-git-worktree --create research-ml-integration develop
# Work for weeks without affecting main codebase
```

**Parallel version work (v1 vs. v2):**
```
/sc-git-worktree --create maintenance-v1.x release/v1.x
/sc-git-worktree --create development-v2 develop
# Maintain both versions simultaneously
```

---

## Use Case 2: Release Branch Management (v0.4.0 vs. v0.5.0)

**Scenario/Context:**
Your project has two active release branches: `release/v0.4.0` (stable, maintenance) and `develop` (unstable, next version). You need to apply patches to v0.4.0 while working on v0.5.0 features without constant branch switching.

**Step-by-step Walkthrough:**

1. Current situation: v0.4.0 in production, v0.5.0 in development

2. Create isolated worktree for v0.4.0 maintenance:
   ```
   /sc-git-worktree --create maintenance-v0.4 release/v0.4.0
   ```
   Output:
   ```
   Creating worktree for maintenance-v0.4 from release/v0.4.0...
   Created: ../my-app-worktrees/maintenance-v0.4
   Branch: maintenance-v0.4 tracking release/v0.4.0
   Status: Success
   ```

3. In the original repo, continue v0.5.0 development:
   ```bash
   # Remain in main repo directory on develop branch
   # Continue working on v0.5.0 features
   git add .
   git commit -m "feat(v0.5): add new payment gateway"
   git push origin develop
   ```

4. Customer reports bug in v0.4.0. Switch to maintenance worktree:
   ```bash
   cd ../my-app-worktrees/maintenance-v0.4
   git fetch origin
   git log --oneline -5
   # See recent patches
   ```

5. Create and apply fix:
   ```bash
   git checkout -b hotfix/v0.4-security-patch
   # Fix the vulnerability
   git add .
   git commit -m "fix(v0.4): patch security vulnerability in auth"
   git push origin hotfix/v0.4-security-patch
   ```

6. Submit PR for v0.4 patch, then clean up:
   ```
   /sc-git-worktree --cleanup maintenance-v0.4
   ```
   Output:
   ```
   Checking worktree status for maintenance-v0.4...
   Status: Clean
   Branch merged into release/v0.4.0
   Action: Delete branch locally and remotely
   Cleanup complete
   Tracking updated
   ```

7. Patch is released; v0.5.0 development continues unaffected

**Expected Outcomes:**
- Isolated v0.4.0 maintenance directory
- v0.5.0 development continues uninterrupted
- No branch switching between versions
- Patch is applied and deployed independently
- Clean tracking document shows completed work

**Benefits of Using This Approach:**
- Maintain multiple product versions simultaneously
- No context switching between versions
- Each version has independent build cache
- Clear audit trail of maintenance work
- Easy to cherry-pick patches between versions if needed
- Production hotfixes don't interrupt active development

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-create agent](agents/sc-worktree-create.md)
- [sc-worktree-cleanup agent](agents/sc-worktree-cleanup.md)

**Tips and Best Practices:**
- Use version numbers in worktree names (maintenance-v0.4, dev-v0.5)
- Keep maintenance branches on production release tags
- Always fetch before checking out maintenance worktree
- Document patch strategy in README
- Consider cherry-picking important patches to next version

**Common Pitfalls to Avoid:**
- Forgetting to fetch latest maintenance branch before working
- Accidentally committing to wrong version branch
- Not pushing patches back to release branch
- Leaving cleanup incomplete (stale worktrees accumulate)

**Variations for Different Scenarios:**

**Three concurrent versions (stable, RC, beta):**
```
/sc-git-worktree --create stable-v1.0 release/v1.0
/sc-git-worktree --create rc-v1.1 release/v1.1-rc
/sc-git-worktree --create beta-v2.0 develop
```

**LTS + current version management:**
```
/sc-git-worktree --create lts-maintenance release/v1.x
/sc-git-worktree --create current-development release/v2.x
```

---

## Use Case 3: Hotfix Workflow (Create from Main, Merge Back)

**Scenario/Context:**
Production issue discovered! You need to:
1. Create isolated hotfix environment from main branch
2. Fix the issue
3. Test thoroughly
4. Merge back to main and develop
5. Clean up worktree

This workflow ensures production fixes don't interfere with ongoing development.

**Step-by-step Walkthrough:**

1. Production alert: database connection pooling issue in user service

2. Create hotfix worktree from main:
   ```
   /sc-git-worktree --create hotfix-db-pool main
   ```
   Output:
   ```
   Creating worktree for hotfix-db-pool from main...
   Created: ../my-app-worktrees/hotfix-db-pool
   Branch: hotfix-db-pool tracking main
   Status: Success
   ```

3. Switch to hotfix directory and investigate:
   ```bash
   cd ../my-app-worktrees/hotfix-db-pool
   git fetch origin

   # Investigate the issue
   grep -r "pool" src/services/database.ts
   # Find the bug in connection pool initialization
   ```

4. Implement fix with comprehensive testing:
   ```bash
   # Fix the bug
   nano src/services/database.ts

   # Run tests locally
   npm run test:unit -- database.test.ts
   npm run test:integration -- database-pool.test.ts

   # Build and verify
   npm run build
   npm run lint
   ```

5. Create hotfix branch and commit:
   ```bash
   git checkout -b hotfix/db-connection-pool
   git add -A
   git commit -m "fix(db): increase connection pool timeout and add retry logic"
   git push origin hotfix/db-connection-pool
   ```

6. Once approved, merge back to main:
   ```bash
   git checkout main
   git pull origin main
   git merge hotfix/db-connection-pool
   git push origin main
   ```

7. Cherry-pick same fix to develop:
   ```bash
   git checkout develop
   git pull origin develop
   git cherry-pick main
   git push origin develop
   ```

8. Create PR for develop merge (if needed) and wait for CI

9. Clean up hotfix worktree:
   ```
   /sc-git-worktree --cleanup hotfix-db-pool
   ```
   Output:
   ```
   Verifying hotfix-db-pool cleanup...
   Branch merged: Yes
   Merged into: main
   Action: Delete branch and worktree
   Cleanup complete
   ```

10. Production deploy happens automatically from main branch

**Expected Outcomes:**
- Isolated hotfix environment created quickly
- Fix can be thoroughly tested without disrupting development
- Main branch updated with fix
- Develop branch also gets fix (cherry-picked)
- Worktree cleaned up after merge
- Clear audit trail of hotfix

**Benefits of Using This Approach:**
- Emergency fixes don't interrupt development
- Hotfix code is isolated and can't break ongoing work
- Full testing capability before production deploy
- Clean merge strategy (main first, then develop)
- Automatic tracking of hotfix progress

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-create agent](agents/sc-worktree-create.md)
- [sc-worktree-cleanup agent](agents/sc-worktree-cleanup.md)

**Tips and Best Practices:**
- Always create from main branch for production hotfixes
- Test thoroughly in isolation (faster than main branch testing)
- Merge to main first, then cherry-pick to develop
- Use "hotfix/" prefix in branch names for clarity
- Document the issue and fix in commit message
- Set up CI/CD to deploy from main automatically

**Common Pitfalls to Avoid:**
- Creating hotfix from develop instead of main
- Committing directly to main without creating a proper branch
- Forgetting to merge fix to develop
- Not testing thoroughly before pushing to production
- Leaving hotfix worktree dirty (commit or stash changes)

**Variations for Different Scenarios:**

**Multiple concurrent hotfixes:**
```
/sc-git-worktree --create hotfix-auth main
/sc-git-worktree --create hotfix-payment main
/sc-git-worktree --create hotfix-dashboard main
```
(Each independently fixed and merged)

**Urgent security patch with escalation:**
```bash
/sc-git-worktree --create security-patch-critical main
# (Fix and test in isolation)
git checkout main
git pull && git merge security-patch-critical && git push origin main
# (Trigger emergency deployment)
/sc-git-worktree --cleanup security-patch-critical
```

---

## Use Case 4: Long-Running Experiments Without Branch Pollution

**Scenario/Context:**
You want to experiment with a significant architectural change (e.g., switching to a new database, refactoring auth system, testing new framework). You don't want this experiment to pollute your main branches until it's proven to work.

**Step-by-step Walkthrough:**

1. Plan experiment: "Evaluate migrating from PostgreSQL to MongoDB"

2. Create long-running experiment worktree:
   ```
   /sc-git-worktree --create experiment-mongodb-migration develop
   ```
   Output:
   ```
   Creating worktree for experiment-mongodb-migration from develop...
   Created: ../my-app-worktrees/experiment-mongodb-migration
   Branch: experiment-mongodb-migration tracking develop
   Status: Success
   Tracking updated
   ```

3. Update tracking document with purpose:
   ```bash
   cd ../my-app-worktrees/experiment-mongodb-migration
   # Edit ../worktree-tracking.md to add purpose
   # Purpose: Evaluate MongoDB for performance improvement
   # Expected duration: 2-3 weeks
   ```

4. Begin experimental work:
   ```bash
   npm install mongodb mongoose
   # Create new database layer
   # Migrate existing queries to MongoDB syntax
   # Implement data migration strategy
   # Run tests
   ```

5. Work continues over several days/weeks:
   ```bash
   # Daily work in isolated directory
   git add .
   git commit -m "experiment: convert user service to MongoDB"
   # More commits...
   git commit -m "experiment: benchmark query performance"
   # Experiment shows promise or doesn't
   ```

6. Checkpoint: experiment shows promise! Merge back:
   ```bash
   # Ensure all tests pass
   npm run test:full
   npm run benchmark

   # Merge to develop
   git checkout develop
   git pull origin develop
   git merge experiment-mongodb-migration
   git push origin develop
   ```

7. Or, experiment fails: discard and continue:
   ```bash
   # Experiment didn't yield expected performance
   /sc-git-worktree --abort experiment-mongodb-migration
   ```
   Output:
   ```
   Aborting worktree experiment-mongodb-migration...
   Status: Dirty
   Confirm abort (discard changes): Yes
   Aborted and cleaned up
   Tracking updated
   ```

**Expected Outcomes:**
- Isolated experimental environment
- Main branches completely unaffected during experiment
- Successful experiment can be merged cleanly
- Failed experiment discarded without polluting history
- Team knows what experiments are ongoing (tracking.md)

**Benefits of Using This Approach:**
- Risky changes isolated from main development
- Main branch stays clean and deployable
- Experiment work is preserved in git history
- Other team members can review experimental branch
- Clear decision points (merge or abort)
- No cluttered branch namespace

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-create agent](agents/sc-worktree-create.md)
- [sc-worktree-abort agent](agents/sc-worktree-abort.md)

**Tips and Best Practices:**
- Use "experiment-" prefix for easy identification
- Document purpose and expected duration in tracking.md
- Set a decision point (e.g., "decide by 2025-12-15")
- Commit frequently even in experimental branch
- Keep main tests passing (can still run against main)
- Have clear success criteria before starting

**Common Pitfalls to Avoid:**
- Experiment branches that become permanent limbo
- Not documenting the experiment purpose
- Mixing multiple experiments in one branch
- Forgetting to decide: merge or abort
- Not cleaning up aborted experiments properly

**Variations for Different Scenarios:**

**Framework upgrade experiment (e.g., React 18 → React 19):**
```
/sc-git-worktree --create experiment-react-19-upgrade develop
# Upgrade React and all dependencies
# Run full test suite
# Benchmark performance
# Merge if successful, abort if too many issues
```

**New language feature experiment (TypeScript 5.0 features):**
```
/sc-git-worktree --create experiment-ts5-features develop
# Implement new types and patterns
# Measure type safety improvements
# Decide if worth adopting project-wide
```

---

## Use Case 5: Team Collaboration with Tracking

**Scenario/Context:**
You manage a team of 5 developers. Each is working on different features simultaneously. You want visibility into what everyone is working on, when they started, and what branches are active.

**Step-by-step Walkthrough:**

1. Team kickoff: assign features
   - Alice: feature-user-authentication
   - Bob: feature-payment-integration
   - Carol: feature-notifications
   - David: bug-fix-performance
   - You: feature-dashboard-redesign

2. Each developer creates their worktree:

   Alice:
   ```
   /sc-git-worktree --create feature-user-authentication develop
   ```

   Bob:
   ```
   /sc-git-worktree --create feature-payment-integration develop
   ```

   Carol:
   ```
   /sc-git-worktree --create feature-notifications develop
   ```

   David:
   ```
   /sc-git-worktree --create bug-fix-performance develop
   ```

   You:
   ```
   /sc-git-worktree --create feature-dashboard-redesign develop
   ```

3. Tracking document auto-populated (`../my-app-worktrees/worktree-tracking.md`):
   ```markdown
   # Worktree Tracking

   | Branch | Path | Base | Owner | Status | Created | Last Checked | Notes |
   |--------|------|------|-------|--------|---------|--------------|-------|
   | feature-user-authentication | ../my-app-worktrees/feature-user-authentication | develop | alice | active | 2025-12-02 | 2025-12-02 | User auth implementation |
   | feature-payment-integration | ../my-app-worktrees/feature-payment-integration | develop | bob | active | 2025-12-02 | 2025-12-02 | Stripe integration |
   | feature-notifications | ../my-app-worktrees/feature-notifications | develop | carol | active | 2025-12-02 | 2025-12-02 | Email + SMS |
   | bug-fix-performance | ../my-app-worktrees/bug-fix-performance | develop | david | active | 2025-12-02 | 2025-12-02 | DB query optimization |
   | feature-dashboard-redesign | ../my-app-worktrees/feature-dashboard-redesign | develop | you | active | 2025-12-02 | 2025-12-02 | New dashboard UI |
   ```

4. Daily standup: check worktree status:
   ```
   /sc-git-worktree --status
   ```
   Output shows all active worktrees and who's working on what

5. Developer checks in: Alice finishes auth feature
   ```bash
   cd ../my-app-worktrees/feature-user-authentication
   npm run test
   npm run build
   git push origin feature-user-authentication
   ```
   Creates PR, gets reviewed, merged to develop

6. Clean up Alice's worktree:
   ```
   /sc-git-worktree --cleanup feature-user-authentication
   ```
   Tracking document updated: branch marked as completed

7. Continuous visibility into team progress via tracking document:
   ```
   /sc-git-worktree --status
   ```

8. Daily snapshot of which features are done, in progress, blocked, etc.

**Expected Outcomes:**
- Central tracking document shows all active work
- Team knows who is working on what
- Clear status of each feature (active, ready for review, merged, etc.)
- No duplicate work (can see what others are doing)
- Easy onboarding for new team members

**Benefits of Using This Approach:**
- Team coordination without constant Slack updates
- Automatic tracking of progress
- Clear blocking dependencies visible
- Documentation of who worked on what
- Reduces context switching for status updates
- Git-based audit trail for all work

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-scan agent](agents/sc-worktree-scan.md)
- [sc-worktree-cleanup agent](agents/sc-worktree-cleanup.md)

**Tips and Best Practices:**
- Update owner field with GitHub username
- Use clear, descriptive branch names for features
- Update notes field with current status
- Run status check regularly (daily standup)
- Clean up merged worktrees to keep directory clean
- Share tracking.md in team docs or commit it to repo

**Common Pitfalls to Avoid:**
- Not updating tracking document regularly
- Creating duplicate worktrees with same branch name
- Leaving completed worktrees uncleaned
- Not communicating branch dependencies
- Tracking document getting out of sync with actual worktrees

**Variations for Different Scenarios:**

**Large team (20+ developers):**
```bash
# Group by feature area
/sc-git-worktree --status | grep active
# Or filter by owner in tracking document
grep "| frontend-" ../my-app-worktrees/worktree-tracking.md
```

**Sprint-based tracking:**
```markdown
# Sprint 12 Worktrees (2025-12-02 to 2025-12-16)
| Branch | Owner | Sprint Goal | Status |
```

**Cross-team coordination:**
```bash
# Share tracking document in Slack/Teams
# Central repo with all team worktrees visible
```

---

## Use Case 6: Worktree Scanning and Status Reporting

**Scenario/Context:**
After a week of development with multiple worktrees active, you want to get a complete status report: which worktrees exist, their git status, any uncommitted changes, and recommendations for cleanup.

**Step-by-step Walkthrough:**

1. Scan all worktrees for health and status:
   ```
   /sc-git-worktree --list
   ```
   Output:
   ```
   Repository: my-app
   Base: ../my-app-worktrees/

   Active Worktrees (from git worktree list):
   - main: /Users/dev/my-app
   - feature-x: /Users/dev/my-app-worktrees/feature-x
   - feature-y: /Users/dev/my-app-worktrees/feature-y
   - hotfix-critical: /Users/dev/my-app-worktrees/hotfix-critical

   Status Details:
   ✓ feature-x: Clean, 3 commits ahead of develop
   ✓ feature-y: Clean, 5 commits ahead of develop
   ⚠ hotfix-critical: Dirty (4 modified files)

   Recommendations:
   1. hotfix-critical: Commit changes or stash before cleanup
   2. feature-x: Ready for merge/cleanup
   3. feature-y: Ready for PR submission

   Tracking Sync:
   ✓ All worktrees in tracking document
   ✓ No orphaned entries
   ✓ Last updated: 2025-12-02 14:30
   ```

2. Handle issues identified:
   - Go to hotfix-critical, commit changes:
     ```bash
     cd ../my-app-worktrees/hotfix-critical
     git add .
     git commit -m "fix: complete critical fix"
     ```

   - feature-x is ready to merge:
     ```
     /sc-git-worktree --cleanup feature-x
     ```

3. After cleanup, check status again:
   ```
   /sc-git-worktree --status
   ```
   Output shows feature-x removed, tracking updated

**Expected Outcomes:**
- Complete visibility into all worktrees
- Status of each (clean/dirty, ahead/behind)
- Recommendations for next actions
- Tracking document validation
- Clear action items from status report

**Benefits of Using This Approach:**
- Regular hygiene checks prevent accumulation of stale worktrees
- Identify dirty worktrees needing attention
- Automate status reporting
- Keep team synchronized on worktree state
- Prevent accidental loss of work

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-scan agent](agents/sc-worktree-scan.md)

**Tips and Best Practices:**
- Run status check at end of each day
- Address recommendations immediately
- Commit or stash dirty worktrees before leaving
- Update tracking notes with any blockers
- Share status report with team in standup

**Common Pitfalls to Avoid:**
- Ignoring dirty worktree warnings
- Running cleanup on worktrees with uncommitted changes
- Not checking tracking sync regularly
- Letting stale worktrees accumulate for weeks

---

## Use Case 7: Cleanup and Archival of Completed Work

**Scenario/Context:**
After completing features and merging PRs, you want to clean up the worktrees. The cleanup command handles verification that work is merged, deletion of branches, and tracking updates.

**Step-by-step Walkthrough:**

1. Feature is complete and merged:
   ```bash
   cd ../my-app-worktrees/feature-api-v2
   git fetch origin
   git log --oneline -5
   # Shows: commits are in develop
   ```

2. Verify status before cleanup:
   ```
   /sc-git-worktree --status
   ```
   Output confirms feature-api-v2 is clean and merged

3. Clean up the completed worktree:
   ```
   /sc-git-worktree --cleanup feature-api-v2
   ```
   Output:
   ```
   Cleaning up feature-api-v2...

   Verification:
   - Worktree status: Clean
   - Branch merged: Yes (into develop)
   - Unique commits: 0

   Actions:
   - Remove worktree: ../my-app-worktrees/feature-api-v2 ✓
   - Delete local branch: feature-api-v2 ✓
   - Delete remote branch: feature-api-v2 ✓

   Cleanup complete
   Tracking document updated
   ```

4. Verify cleanup successful:
   ```
   /sc-git-worktree --status
   ```
   Output: feature-api-v2 no longer listed

5. Archive completed work (tracking document documents completed work):
   ```bash
   # View tracking document
   cat ../my-app-worktrees/worktree-tracking.md
   # Shows completed entry:
   # | feature-api-v2 | ... | Status: Completed | Merged on: 2025-12-15 |
   ```

**Expected Outcomes:**
- Worktree directory removed
- Local and remote branches deleted
- Tracking document shows completed work
- Clean repository state
- Clear audit trail of completed features

**Benefits of Using This Approach:**
- Automatic branch cleanup (no orphaned branches)
- Directory space reclaimed
- Clear completion history
- Prevents accidental work on stale branches
- Audit trail of all completed work

**Related Documentation:**
- [/sc-git-worktree command reference](commands/sc-git-worktree.md)
- [sc-worktree-cleanup agent](agents/sc-worktree-cleanup.md)

**Tips and Best Practices:**
- Always verify branch is merged before cleanup
- Let merge PR process complete before cleanup
- Check that all CI passes before cleanup
- Update notes in tracking before cleanup
- Regular cleanup prevents directory clutter

**Common Pitfalls to Avoid:**
- Cleaning up before branch is merged (loses work)
- Forgetting to push branch before cleanup (cleanup deletes remote)
- Not verifying merged status
- Leaving completed worktrees uncleaned

**Variations for Different Scenarios:**

**Cleanup with force option (unmerged work):**
```bash
# Use --abort instead for unmerged/abandoned work
/sc-git-worktree --abort experimental-branch-that-failed
# Forces deletion even if not merged
```

**Batch cleanup multiple worktrees:**
```bash
# Clean multiple completed features
/sc-git-worktree --cleanup feature-one
/sc-git-worktree --cleanup feature-two
/sc-git-worktree --cleanup bug-fix-one
```

---

## Common Patterns

### Pattern 1: Standard Feature Workflow
```
/sc-git-worktree --create feature-name develop
# Work in isolation
# Commit and push
/sc-git-worktree --cleanup feature-name
```

### Pattern 2: Hotfix from Main
```
/sc-git-worktree --create hotfix-issue main
# Fix and test
# Merge to main and develop
/sc-git-worktree --cleanup hotfix-issue
```

### Pattern 3: Long-Running Experiment
```
/sc-git-worktree --create experiment-new-arch develop
# Work for extended period
# Decide: merge or abort
/sc-git-worktree --cleanup experiment-new-arch  # or --abort
```

### Pattern 4: Release Management
```
/sc-git-worktree --create maintenance-v1 release/v1.0
/sc-git-worktree --create development-v2 develop
# Parallel maintenance and development
```

### Pattern 5: Parallel Feature Development
```
/sc-git-worktree --create feature-a develop
/sc-git-worktree --create feature-b develop
/sc-git-worktree --create feature-c develop
# Three developers work simultaneously
```

---

## Integration Examples

### With GitHub Actions
In CI/CD, you might create a worktree for release verification:
```yaml
- name: Create release verification worktree
  run: |
    /sc-git-worktree --create verify-release release/v1.0.0
    cd ../my-app-worktrees/verify-release
    npm run test:full
    npm run build
    /sc-git-worktree --cleanup verify-release
```

### With Development Scripts
```bash
#!/bin/bash
# scripts/feature-setup.sh

FEATURE_NAME=$1
BASE=${2:-develop}

# Create isolated worktree
/sc-git-worktree --create feature-$FEATURE_NAME $BASE

# Install dependencies
cd ../my-app-worktrees/feature-$FEATURE_NAME
npm install
npm run build

echo "Feature worktree created and built: feature-$FEATURE_NAME"
```

### With Team Documentation
In README:
```markdown
## Development Workflow

1. Create feature worktree:
   ```
   /sc-git-worktree --create feature-name develop
   ```

2. Work in the new directory:
   ```
   cd ../my-app-worktrees/feature-name
   ```

3. Check status anytime:
   ```
   /sc-git-worktree --status
   ```

4. After PR merge:
   ```
   /sc-git-worktree --cleanup feature-name
   ```
```

---

## Team Workflows

### Small Team (2-3 developers)
Each developer has 1-2 active worktrees. Status check via:
```
/sc-git-worktree --status
```

### Medium Team (5-10 developers)
Shared tracking document, daily standup reviews tracking.md:
```bash
# In standup, review:
cat ../my-app-worktrees/worktree-tracking.md
```

### Large Team (10+ developers)
Distributed worktrees across multiple workstations, central registry:
```bash
# All teams share same repository
# Each dev has own worktree base
# Tracking document versioned in repo
```

---

## Troubleshooting

### Scenario: Path exists error when creating worktree
```
Error: ../my-app-worktrees/feature-name already exists
```
**Solution:**
- Use unique branch name: `/sc-git-worktree --create feature-name-v2 develop`
- Or delete old worktree: `/sc-git-worktree --cleanup feature-name`

### Scenario: Dirty worktree prevents cleanup
```
Error: Worktree has uncommitted changes
```
**Solution:**
```bash
cd ../my-app-worktrees/branch-name
git add .
git commit -m "Save work"
# Then cleanup
/sc-git-worktree --cleanup branch-name
```

### Scenario: Tracking document out of sync
**Solution:**
```
/sc-git-worktree --status
# Will show mismatches and suggest fixes
```

### Scenario: Worktree branch is behind main
**Solution:**
```bash
cd ../my-app-worktrees/feature-name
git fetch origin
git rebase origin/develop
# Or merge if preferred
git merge origin/develop
```

### Scenario: Can't cleanup because branch not merged
**Solution:**
Either merge the branch first, or use abort to discard work:
```
/sc-git-worktree --abort feature-name
```

---

## Getting Started

### Minimum Setup
```bash
# Install sc-git-worktree in repo
python3 tools/sc-install.py install sc-git-worktree --dest /path/to/your-repo/.claude

# Check status
/sc-git-worktree --status

# Create first worktree
/sc-git-worktree --create my-feature develop
```

### First Use
1. Check repository status: `/sc-git-worktree --status`
2. Create a worktree: `/sc-git-worktree --create test-feature develop`
3. Work in the new directory: `cd ../my-app-worktrees/test-feature`
4. Make changes and commit
5. Cleanup when done: `/sc-git-worktree --cleanup test-feature`

### Common Starting Patterns
- **Simple feature**: `/sc-git-worktree --create feature-name develop`
- **Hotfix**: `/sc-git-worktree --create hotfix-name main`
- **Release work**: `/sc-git-worktree --create maintenance-v1 release/v1.0`
- **Experiment**: `/sc-git-worktree --create experiment-idea develop`

---

## See Also

- [sc-git-worktree README](README.md)
- [/sc-git-worktree Command Reference](commands/sc-git-worktree.md)
- [Worktree Tracking Document Format](../sc-git-worktree/worktree-tracking.md)
- [Synaptic Canvas Contributing Guide](/CONTRIBUTING.md)
- [Git Worktrees Official Documentation](https://git-scm.com/docs/sc-git-worktree)
- [Synaptic Canvas Repository](https://github.com/randlee/synaptic-canvas)

---

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Maintainer:** Synaptic Canvas Contributors
