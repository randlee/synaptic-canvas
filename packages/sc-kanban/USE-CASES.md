# Use Cases (sc-kanban)

Detailed scenarios demonstrating sc-kanban workflows from backlog to archive.

---

## Use Case 1: Planning Sprint Items (Backlog → Board Expansion)

**Who**: Development team lead planning upcoming sprint work
**What**: Expand lean backlog entries into rich board cards with worktree assignments, agent specifications, and acceptance criteria
**Why**: Rich planning fields enable autonomous execution by PM/scrum-master agents while keeping backlog lean

### Prerequisites

- Board config initialized (`.project/board.config.yaml`)
- Backlog file exists (`.project/backlog.json`) with lean entries
- sc-git-worktree installed for worktree tracking

### Steps

1. **Review backlog for next sprint items**

   ```bash
   kanban-query --file .project/backlog.json
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "cards": [
         {
           "sprint_id": "1.1",
           "title": "Project Setup",
           "dependencies": []
         },
         {
           "sprint_id": "1.2",
           "title": "Database Schema",
           "dependencies": ["1.1"]
         }
       ]
     }
   }
   ```

2. **Create rich board entry for Sprint 1.1**

   ```bash
   kanban-card create --target-status planned \
     --card '{
       "sprint_id": "1.1",
       "title": "Project Setup",
       "worktree": "main/1-1-project-setup",
       "dev_agent": "dotnet-dev",
       "qa_agent": "integration-qa",
       "dev_prompt": "Initialize solution structure, configure CI/CD pipeline, setup development environment",
       "qa_prompt": "Verify build succeeds, all tests pass, CI pipeline runs successfully",
       "acceptance_criteria": [
         "Solution builds without errors",
         "CI/CD pipeline configured and passing",
         "Development environment documented in README"
       ],
       "max_retries": 3,
       "base_branch": "main"
     }'
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "title": "Project Setup",
         "worktree": "main/1-1-project-setup",
         "status": "planned",
         "dev_agent": "dotnet-dev",
         "qa_agent": "integration-qa",
         "dev_prompt": "Initialize solution structure...",
         "qa_prompt": "Verify build succeeds...",
         "acceptance_criteria": ["Solution builds...", "CI/CD...", "Development..."],
         "max_retries": 3,
         "base_branch": "main"
       }
     }
   }
   ```

3. **Verify card moved from backlog to board**

   Card is automatically removed from `backlog.json` and added to `board.json` with rich fields.

### Common Variations

- **Parallel sprints**: Create multiple rich cards for concurrent work (e.g., 1.2a, 1.2b)
- **Custom agents**: Specify project-specific dev/qa agents instead of defaults
- **Template prompts**: Use prompt templates for common sprint types

### Result

Backlog entry expanded into rich board card ready for autonomous execution, with worktree reference, agent assignments, prompts, and acceptance criteria.

---

## Use Case 2: Tracking Active Worktrees and PRs

**Who**: Team lead monitoring sprint progress
**What**: Query board for active work, filter by status and worktree, view execution metadata
**Why**: Understand current progress, identify blockers, track PR status and cycle counts

### Prerequisites

- Board file exists (`.project/board.json`) with active cards
- Cards have execution metadata (pr_url, status_report, actual_cycles)

### Steps

1. **List all active cards**

   ```bash
   kanban-query --status active
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "cards": [
         {
           "sprint_id": "1.1",
           "title": "Project Setup",
           "worktree": "main/1-1-project-setup",
           "status": "active",
           "pr_url": "https://github.com/org/repo/pull/42",
           "status_report": "Implementation complete, tests passing",
           "actual_cycles": 2,
           "started_at": "2026-01-01T09:00:00Z"
         }
       ]
     }
   }
   ```

2. **Filter by specific worktree**

   ```bash
   kanban-query --worktree main/1-1-project-setup
   ```

   Returns single card matching worktree.

3. **Check cards in review**

   ```bash
   kanban-query --status review
   ```

   Shows cards awaiting PR merge with pr_url, completion timestamps.

### Common Variations

- **Filter by sprint_id**: `kanban-query --sprint-id 1.1`
- **Multiple statuses**: Query across active and review simultaneously
- **Date ranges**: Filter cards by started_at or completed_at (future enhancement)

### Result

Clear visibility into active work, PR status, and execution progress. Team lead can identify blockers and coordinate next steps.

---

## Use Case 3: Moving to Review (PR Requirement Gate)

**Who**: Scrum-master agent or developer completing implementation
**What**: Transition card from active → review with PR URL gate validation
**Why**: Enforce workflow discipline - no review without PR for code review

### Prerequisites

- Card exists in board.json with status "active"
- Implementation complete, tests passing
- PR created and URL available

### Steps

1. **Attempt transition without PR URL (will fail)**

   ```bash
   kanban-transition --sprint-id 1.1 --target-status review
   ```

   Expected output (gate failure):
   ```json
   {
     "success": false,
     "data": null,
     "error": {
       "code": "GATE.VALIDATION",
       "message": "PR URL required before review",
       "recoverable": true,
       "suggested_action": "Add pr_url to card using kanban-card update, then retry transition"
     }
   }
   ```

2. **Update card with PR URL**

   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"pr_url": "https://github.com/org/repo/pull/42"}'
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "pr_url": "https://github.com/org/repo/pull/42",
         "status": "active"
       }
     }
   }
   ```

3. **Retry transition (will succeed)**

   ```bash
   kanban-transition --sprint-id 1.1 --target-status review
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "status": "review",
         "pr_url": "https://github.com/org/repo/pull/42"
       }
     }
   }
   ```

### Common Variations

- **WIP limit enforcement**: If review column full, transition blocked until space available
- **v0.7.1 gates**: Future gates validate PR state (open, checks passing)

### Result

Card successfully moved to review with PR URL validated. Workflow ensures all review items have associated PRs for code review.

---

## Use Case 4: Archiving with Scrubbing (Review → Done)

**Who**: Team lead archiving completed sprint
**What**: Transition card from review → done with automatic field scrubbing
**Why**: Keep done archive lean, remove rich planning/execution fields, preserve essential metrics

### Prerequisites

- Card exists in board.json with status "review"
- PR merged (v0.7.1 gate)
- Worktree cleaned up (v0.7.1 gate)

### Steps

1. **Review card before archiving**

   Card in board.json (rich):
   ```json
   {
     "sprint_id": "1.1",
     "title": "Project Setup",
     "worktree": "main/1-1-project-setup",
     "status": "review",
     "dev_agent": "dotnet-dev",
     "qa_agent": "integration-qa",
     "dev_prompt": "Initialize solution structure...",
     "qa_prompt": "Verify build succeeds...",
     "acceptance_criteria": ["Solution builds...", "CI/CD...", "Development..."],
     "max_retries": 3,
     "base_branch": "main",
     "pr_url": "https://github.com/org/repo/pull/42",
     "status_report": "All checks passing, ready to merge",
     "actual_cycles": 2,
     "started_at": "2026-01-01T09:00:00Z",
     "completed_at": "2026-01-01T15:30:00Z"
   }
   ```

2. **Transition to done (automatic scrubbing)**

   ```bash
   kanban-transition --sprint-id 1.1 --target-status done
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "title": "Project Setup",
         "pr_url": "https://github.com/org/repo/pull/42",
         "completed_at": "2026-01-01T15:30:00Z",
         "actual_cycles": 2
       }
     }
   }
   ```

3. **Verify card in done.json (scrubbed)**

   Card in done.json (lean):
   ```json
   {
     "sprint_id": "1.1",
     "title": "Project Setup",
     "pr_url": "https://github.com/org/repo/pull/42",
     "completed_at": "2026-01-01T15:30:00Z",
     "actual_cycles": 2
   }
   ```

### What Gets Scrubbed

**Removed fields**:
- `worktree`, `dev_agent`, `qa_agent`
- `dev_prompt`, `qa_prompt`, `acceptance_criteria`
- `max_retries`, `base_branch`, `status`, `status_report`, `started_at`

**Preserved fields**:
- `sprint_id`, `title` (identity)
- `pr_url` (traceability)
- `completed_at`, `actual_cycles` (metrics)

### Common Variations

- **Bulk archiving**: Archive multiple completed sprints in sequence
- **Historical analysis**: Query done.json for velocity metrics (actual_cycles)

### Result

Card archived in done.json with only essential fields. Rich planning/execution details removed, lean archive maintained for long-term storage.

---

## Use Case 5: Checklist Fallback for Small Projects

**Who**: Solo developer working on small project without full kanban overhead
**What**: Use checklist provider for markdown-based workflow without gates or WIP enforcement
**Why**: Lightweight alternative for projects that don't need full kanban features

### Prerequisites

- Board config exists (`.project/board.config.yaml`)
- Roadmap markdown file prepared

### Steps

1. **Configure checklist provider**

   Edit `.project/board.config.yaml`:
   ```yaml
   version: 0.7
   board:
     provider: checklist  # Switch from kanban to checklist
     roadmap_path: .project/roadmap.md
     prompts_dir: .project/prompts
   ```

2. **Create roadmap.md**

   ```markdown
   # Project Roadmap

   ## Sprint 1.1: Project Setup
   - Status: ⏳ Pending
   - Deliverables:
     - [ ] Initialize solution structure
     - [ ] Configure CI/CD pipeline

   ## Sprint 1.2: Database Schema
   - Status: ⏳ Pending
   - Depends On: 1.1
   ```

3. **Query checklist (returns advisory)**

   ```bash
   kanban-query --sprint-id 1.1
   ```

   Expected output (provider advisory):
   ```json
   {
     "success": false,
     "error": {
       "code": "PROVIDER.CHECKLIST",
       "message": "Board config provider=checklist; call checklist agent",
       "recoverable": true,
       "suggested_action": "Invoke checklist-agent/query-update with same card selector"
     }
   }
   ```

4. **Use checklist agent directly**

   ```bash
   checklist-agent query --sprint-id 1.1
   ```

   Returns markdown-based card data without gates/WIP.

### Differences from Kanban Provider

| Feature | Kanban Provider | Checklist Provider |
|---------|----------------|-------------------|
| Files | 3 JSON files (backlog/board/done) | 1 markdown + prompts |
| Gates | PR, git, worktree validation | None |
| WIP | Enforced per column | Not enforced |
| Scrubbing | Automatic on archive | Manual markdown edits |
| Fields | Rich structured schema | Markdown sections |

### Common Variations

- **Hybrid mode**: Use checklist for planning, kanban for execution (switch provider mid-project)
- **Migration**: Export checklist to kanban JSON when project scales

### Result

Lightweight markdown-based workflow suitable for small projects. Same agent interface (v0.5 envelope), simpler implementation.

---

## Use Case 6: Updating Execution Metadata

**Who**: Scrum-master agent during sprint execution
**What**: Update card with execution metadata (pr_url, status_report, actual_cycles) as work progresses
**Why**: Track progress without full transitions, capture cycle counts and status reports

### Prerequisites

- Card exists in board.json with status "active" or "review"
- Execution in progress or recently completed

### Steps

1. **Update PR URL after creation**

   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"pr_url": "https://github.com/org/repo/pull/42"}'
   ```

2. **Update status report after iteration**

   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"status_report": "Dev cycle 1 complete, tests passing, ready for QA"}'
   ```

3. **Increment cycle count after dev-QA iteration**

   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"actual_cycles": 2}'
   ```

4. **Update completion timestamp**

   ```bash
   kanban-card update --sprint-id 1.1 \
     --card '{"completed_at": "2026-01-01T15:30:00Z"}'
   ```

5. **Verify accumulated updates**

   ```bash
   kanban-query --sprint-id 1.1
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "status": "active",
         "pr_url": "https://github.com/org/repo/pull/42",
         "status_report": "Dev cycle 1 complete...",
         "actual_cycles": 2,
         "completed_at": "2026-01-01T15:30:00Z"
       }
     }
   }
   ```

### Common Variations

- **Bulk updates**: Update multiple fields in single operation
- **Automated tracking**: Scrum-master updates actual_cycles after each dev→QA iteration

### Result

Card execution metadata updated incrementally without triggering transitions. Captures progress, cycle counts, and status reports for PM visibility.

---

## Use Case 7: Within-Board Status Transitions (Planned → Active → Review)

**Who**: Scrum-master coordinating sprint execution
**What**: Move card through board columns (planned → active → review) without file changes
**Why**: Track detailed status progression while keeping card in board.json until archive

### Prerequisites

- Card exists in board.json with status "planned"
- Board config defines status columns (planned, active, review, done)

### Steps

1. **Start sprint (planned → active)**

   ```bash
   kanban-transition --sprint-id 1.1 --target-status active
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "status": "active",
         "started_at": "2026-01-01T09:00:00Z"
       }
     }
   }
   ```

   Card remains in board.json, status field updated, started_at timestamp added.

2. **Complete implementation (active → review)**

   ```bash
   # First add PR URL (required gate)
   kanban-card update --sprint-id 1.1 \
     --card '{"pr_url": "https://github.com/org/repo/pull/42"}'

   # Then transition
   kanban-transition --sprint-id 1.1 --target-status review
   ```

   Expected output:
   ```json
   {
     "success": true,
     "data": {
       "card": {
         "sprint_id": "1.1",
         "status": "review",
         "pr_url": "https://github.com/org/repo/pull/42"
       }
     }
   }
   ```

3. **Check WIP limits**

   If review column has WIP limit (e.g., 2) and already contains 2 cards:

   ```bash
   kanban-transition --sprint-id 1.2 --target-status review
   ```

   Expected output (WIP limit exceeded):
   ```json
   {
     "success": false,
     "error": {
       "code": "WIP.EXCEEDED",
       "message": "Review column WIP limit (2) exceeded",
       "recoverable": true,
       "suggested_action": "Complete existing review items or increase WIP limit in board config"
     }
   }
   ```

4. **Query board status by column**

   ```bash
   kanban-query --status active
   kanban-query --status review
   ```

   Returns cards grouped by status column.

### Common Variations

- **Rollback transitions**: Move card backwards (review → active) if issues found
- **Skip columns**: Direct planned → review if implementation trivial (still requires pr_url gate)
- **Custom statuses**: Define additional columns in board config (blocked, testing, etc.)

### Result

Card progresses through board columns with status field updates, automatic timestamps, gate enforcement, and WIP limits. All transitions occur within board.json until final archive to done.json.

---

## Summary

These 7 use cases demonstrate sc-kanban's complete workflow:

1. **Planning**: Expand lean backlog → rich board cards
2. **Tracking**: Query active work, filter by status/worktree
3. **Gating**: Enforce PR requirements before review
4. **Archiving**: Automatic scrubbing on completion
5. **Fallback**: Checklist provider for lightweight projects
6. **Metadata**: Update execution fields during progress
7. **Transitions**: Move through board columns with gates/WIP

For additional scenarios, see [Troubleshooting](./TROUBLESHOOTING.md) for error handling and [README](./README.md) for integration patterns.
