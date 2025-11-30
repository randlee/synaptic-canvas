# Claude Skill/Agent Upgrade Plan (v0.4 Guidelines)

**Created:** 2025-11-29  
**Status:** Ready for Implementation  
**Target Guidelines:** `docs/claude-code-skills-agents-guidelines-0.4.md`  
**Target Version:** 0.4.0  
**Central Version File:** `version.yaml` at repo root (single source of truth for CLI, manifests, and agent frontmatter)

---

## Executive Summary

This plan migrates existing Synaptic Canvas packages (`delay-tasks`, `git-worktree`) to be compatible with the v0.4 Claude Code Skills and Agents Architecture Guidelines. Key changes include adding version metadata, standardizing JSON output format, and updating invocation instructions to use the Task tool.

---

## Current State Assessment

### Packages to Migrate

| Package | Tier | Agents | Skills | Commands |
|---------|------|--------|--------|----------|
| `delay-tasks` | 0 | 2 (`delay-once`, `delay-poll`) | 1 (`delaying-tasks`) | 1 (`/delay`) |
| `git-worktree` | 1 | 4 (`worktree-create`, `worktree-scan`, `worktree-cleanup`, `worktree-abort`) | 1 (`managing-worktrees`) | 1 (`/git-worktree`) |

### Gap Analysis

| Guideline Requirement | Current State | Gap Severity |
|-----------------------|---------------|--------------|
| YAML frontmatter with `version` | Missing `version` field | **Medium** |
| Fenced JSON output (`\`\`\`json`) | Unfenced JSON ("Return ONLY valid JSON, no markdown fences") | **High (Breaking)** |
| Minimal response envelope (`success`, `data`, `error`) | Domain-specific structures | **High (Breaking)** |
| Task tool invocation in skills | Not explicitly mentioned | **Medium** |
| Registry.yaml for version tracking | Not present | **Low** |
| Skill descriptions with trigger words | Basic descriptions | **Low** |

---

## Decisions (Resolved)

- All agents (including delay-tasks) will return fenced JSON using the minimal envelope with lowercase keys:
  - Envelope: `{ "success": boolean, "data": { ... }, "error": null|{ code, message, recoverable?, suggested_action? } }`
  - Use `canceled: boolean` and optional `aborted_by: "user"|"timeout"|"policy"` only when a task is deliberately aborted; otherwise return `success: false` with an `error` object.
- Invocation: Agents are invoked via the Claude Task tool. Each agent prompt will include an "Invocation" note. Do not reference an Agent Runner at this time.
- Frontmatter: Preserve `model` and `color`; add `version: 0.4.0` to every agent.
- delay-run.sh: Deprecated. Replace with Python helper usage in prompts and manifests.
- JSON key style: Lowercase keys across all JSON contracts (including the stop-on-success prompt contract used by delay polling).
- Registry policy: Generate/merge `.claude/agents/registry.yaml` entries during install.
- Centralized versioning: Create `version.yaml` at repo root and validate that CLI, package manifests, and agent frontmatter versions match `0.4.0`.
- CLI cleanup: Keep `tools/sc-install.py` as the user-facing entrypoint; rename implementation to `src/sc_cli/install.py` to eliminate same-name confusion and update the shim import. Mark `tools/sc-install.sh` as deprecated in docs.

---

## Migration Tasks (Final)

### Phase 0: Repo plumbing and CLI cleanup

0.1. Create `version.yaml` with:
```yaml
version: "0.4.0"
```
0.2. Rename `src/sc_cli/sc_install.py` → `src/sc_cli/install.py`; update `tools/sc-install.py` to `from sc_cli.install import main`.
0.3. Deprecate `tools/sc-install.sh` in README; keep only the Python CLI examples.

### Phase 1: Metadata & Structure (Non-Breaking)

1. **Add `version: 0.4.0` to all agent YAML frontmatter; preserve `model` and `color`**
   - `delay-once.md`, `delay-poll.md`
   - All `worktree-*.md`

1.1. **Explicitly state execution context in every agent**
   - Add a short section near the top: "Invocation: This agent is invoked via the Claude Task tool by a skill or command (not via Agent Runner)."
   - Purpose: Aligns with the constraint that we are not migrating to Agent Runner yet.

1.2. **Fix YAML frontmatter/metadata hygiene**
   - Normalize indentation (e.g., options lists in `commands/delay.md`)
   - Ensure frontmatter is valid YAML across commands/skills/agents

2. **Update skill descriptions with trigger words**
   ```yaml
   # Before
   description: Manage git worktrees with the required layout...
   
   # After
   description: Create, manage, scan, and clean up git worktrees for parallel 
     development. Use when working on multiple branches, isolating experiments, 
     or when user mentions "worktree", "parallel branches", or "feature isolation".
   ```

3. **Add Task tool invocation instructions to skills**
   - Update SKILL.md files to reference Task tool explicitly
   - Example: *"Invoke the `worktree-create` agent using the Task tool with the following parameters..."*
   - Also remove or avoid any references to an Agent Runner for now.

### Phase 2: Output Format (Breaking)

4. **Migrate all agents to fenced JSON with minimal envelope and lowercase keys**
   - Wrap existing domain payload under `data`
   - Add `success: boolean`, `error: null|{...}`; use `canceled`/`aborted_by` only for deliberate aborts
   - Add markdown fence around JSON output
   - Apply to delay agents as well (no plaintext heartbeats; return a final JSON summary)

5. **Set all versions to 0.4.0**
   - Update agent frontmatter and package `manifest.yaml` versions
   - Ensure CLI reports `0.4.0` from `version.yaml` and validates during `install`/`validate`

### Phase 3: Tooling & Validation

6. **Add registry.yaml generation to installer**
   - Modify `src/sc_cli/install.py` (and the CLI) to generate/merge `.claude/agents/registry.yaml`
   - Include agent paths and versions; fail fast on missing files or version mismatches

7. **Add validation**
   - Provide a CLI subcommand `validate` or ship `scripts/validate-agents.sh`
   - Validate: frontmatter versions == registry == `version.yaml`

### Phase 4: Documentation

8. **Create migration guide for existing consumers**
   - Document output format changes
   - Provide parsing examples for new envelope

9. **Update package READMEs**
   - Document new output format
   - Include examples

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change for existing consumers | High | Clear migration guide; sample parsers; semver tag 0.4.0 |
| delay-tasks switch to JSON (loss of streaming) | Medium | Provide concise progress messaging at skill layer if needed; document behavior |
| Registry.yaml merge conflicts | Low | Deterministic merge strategy; idempotent installer |
| CLI rename/import drift | Low | Keep `tools/sc-install.py` stable; add CI check |
| Test suite requires updates | Medium | Update fixtures and assertions; add validation step in CI |

---

## Open Items

- None — decisions above incorporated. Optional: add marketplace metadata (`repository`, `keywords`, optional `min_claude_version`, icon) in package manifests.

---

## Appendix: Current vs Target Agent Output

### Example: worktree-create

**Current (v1.x):**
```json
{
  "action": "create",
  "branch": "feature-x",
  "base": "main",
  "path": "../repo-worktrees/feature-x",
  "status": "clean",
  "tracking_row": {...},
  "tracking_update_required": true,
  "warnings": [],
  "errors": []
}
```

**Target (0.4.0 with minimal envelope):**
````markdown
```json
{
  "success": true,
  "data": {
    "action": "create",
    "branch": "feature-x",
    "base": "main",
    "path": "../repo-worktrees/feature-x",
    "status": "clean",
    "tracking_row": {...},
    "tracking_update_required": true
  },
  "error": null
}
```
````

*Note: `warnings` and `errors` arrays folded into `error` object when non-empty, or remain in `data` as metadata.*

---

## Appendix: delay-tasks Target Output (JSON)

````markdown
```json
{
  "success": true,
  "data": {
    "mode": "poll|once",
    "interval_seconds": 60,
    "total_duration_seconds": 180,
    "attempts": 3,
    "stopped_early": false,
    "action": "verify gh pr actions passed",
    "message": null
  },
  "error": null
}
```
````
