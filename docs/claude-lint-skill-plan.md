# Claude Lint Skill Plan

## Initial Audit Process

This is the process used to audit `pg-x` and identify skill/agent installation defects, broken references, and contract drift. It should become the first workflow implemented by the `claude-lint` skill.

1. Inventory the local `.claude` surface.
   - list every file under `.claude/agents`, `.claude/skills`, and `.claude/assets`
   - identify missing expected surfaces such as registry files, installed skill assets, and assignment templates

2. Diff installed package payloads against consumer-repo copies.
   - compare `packages/<package>/agents`, `skills`, and `assets` against the consumer repo’s `.claude` mirror
   - classify differences as:
     - expected repo-local customization
     - stale copied content
     - incomplete install
     - package defect

3. Sweep prompt and skill docs for path references.
   - grep for:
     - `.claude/...`
     - `./...`
     - `../...`
     - `packages/...`
     - `~/.claude/...`
   - verify every referenced file exists in the appropriate resolution scope
   - distinguish live path breakage from harmless examples or placeholders

4. Trace dependency and delegation surfaces.
   - inspect `depends_on` declarations in skills
   - verify agent registry entries exist for every delegated agent
   - confirm the documented launch surface matches installed agent names
   - flag any prompt that instructs callers to use nonexistent agents or missing registries

5. Audit JSON contracts end to end.
   - inspect worker prompts for fenced JSON input requirements
   - inspect output contracts for consistent machine-readable envelopes
   - verify orchestrator prompts provide enough information to satisfy worker input schemas
   - trace assignment templates through the launch chain so required fields are available at the call site

6. Verify template execution mechanically.
   - render installed `.j2` assets with `sc-compose`
   - verify all required review modes
   - treat malformed example commands and stale renderer syntax as defects, not documentation trivia

7. Classify issues by ownership.
   - consumer-local issue:
     - missing repo-specific registry
     - missing repo-specific orchestration skill
     - stale local prompt customization
   - package issue:
     - broken shared template example
     - shared skill doc referencing missing packaged docs
     - incomplete packaged install surface

8. Produce a final review in three buckets.
   - blocking operational defects
   - should-fix inconsistencies
   - acceptable repo-local customization

## Skill Goal

Create a `claude-lint` skill that reviews Claude/Codex prompt surfaces for:
- invalid file paths
- missing installed dependencies
- stale copied package content
- broken or incomplete JSON fencing
- bad agent/skill dependency wiring
- malformed `sc-compose` examples
- relative and absolute path resolution defects caught by supplemental verification scripts
- obvious orchestration drift between prompts, templates, and installed agents

## Scope

The skill should handle:
- repo-local `.claude` directories
- package surfaces such as `packages/*/agents`, `packages/*/skills`, and `packages/*/assets`
- installed-consumer audits where a package is mirrored into a repo-local `.claude` surface
- supplemental scripts that mechanically verify path resolution for relative, repo-root, install-time, and home-scoped references

The skill should not try to prove semantic correctness of every agent policy. Its first responsibility is mechanical integrity and contract consistency.

## Planned Outputs

The skill should produce:
- a critical review report with severity and file references
- a package-vs-install drift summary when package sources are available
- a list of broken path references
- a script-produced path verification report showing which relative and absolute references resolved, failed, or were downgraded to warnings
- a list of JSON contract mismatches
- a list of missing registry entries or dependency declarations
- optional remediation guidance grouped by ownership:
  - consumer repo
  - source package

## Planned Structure

Proposed package layout:

```text
packages/sc-claude-lint/
├── manifest.yaml
├── scripts/
│   ├── verify-path-references.py
│   └── lint-path-resolution.py
├── skills/
│   └── claude-lint/
│       ├── SKILL.md
│       └── references/
│           ├── audit-workflow.md
│           ├── path-rules.md
│           ├── json-contract-rules.md
│           ├── package-install-diffing.md
│           └── sc-compose-template-checks.md
└── agents/
    ├── claude-lint-reviewer.md
    └── claude-install-diff-reviewer.md
```

Script responsibilities:

- `verify-path-references.py`
  - crawl prompt, skill, command, and asset surfaces for path-like references
  - apply the path-resolution rules below
  - emit machine-readable results for resolved, missing, ambiguous, and warning-only references

- `lint-path-resolution.py`
  - provide a narrower entry point for validating a specific file, package, or installed `.claude` mirror
  - support regression fixtures so path bugs can be reproduced without running the full skill orchestration

## Authoring Plan

1. Write the core skill entrypoint.
   - define triggers
   - describe the audit categories
   - define when to compare a consumer repo against a source package

2. Write the audit workflow reference.
   - use the `pg-x` audit process above as the canonical first-pass procedure

3. Write the path validation reference.
   - classify local vs package vs global references
   - document how to resolve relative paths from the owning file
   - document how packaged prompt surfaces resolve installed `.claude/...` paths back to source-package artifacts

4. Design and implement the supplemental path verification scripts.
   - define the accepted path classes:
     - repo-root-relative install paths such as `.claude/...`
     - owner-relative paths such as `./...` and `../...`
     - package-source paths used only during development
     - informational runtime home paths such as `~/.claude/...`
   - make the scripts emit machine-readable findings that the skill can summarize
   - add regression fixtures for broken relative paths, stale absolute paths, and package/install mismatches

5. Write the JSON contract reference.
   - define what counts as a valid fenced JSON input contract
   - define expected output-envelope checks
   - define how to trace orchestrator -> template -> worker compatibility

6. Write the package-install diff reference.
   - explain how to compare `agents/`, `skills/`, and `assets/`
   - explain how to ignore package-root docs not intended for `.claude`

7. Write the `sc-compose` verification reference.
   - require real render verification for `.j2` prompt assets
   - define failure classes:
     - broken examples
     - stale CLI syntax
     - undeclared required vars

8. Add a reviewer agent if needed.
   - keep the agent prompt sparse
   - make the skill docs the policy source of truth

9. Validate the skill on real repos.
   - re-run against `pg-x`
   - run against at least one repo with a more mature `.claude` surface
   - run the supplemental path scripts directly against both package source and installed mirrors
   - compare findings quality and noise level

## Success Criteria

The skill is successful when it can reliably catch:
- missing registry files
- invalid or missing referenced docs
- relative and absolute path resolution failures verified by scripts, not just prose review
- package/install drift
- stale agent names in orchestrators
- malformed JSON contract examples
- malformed `sc-compose` render examples
- incomplete dependency wiring between skills and agents

without producing large volumes of low-value prose findings.

## Path Resolution Rules

These rules should drive both the `claude-lint` skill guidance and the mechanical validator.

1. Repo-local installed paths: `.claude/...`
   - In a consumer repo, treat these as repo-root-relative.
   - Example: `.claude/agents/req-qa.md` resolves from repo root.

2. Owner-relative paths: `./...` and `../...`
   - Resolve from the file that contains the reference.
   - Example: `skills/codex-orchestration/SKILL.md` can refer to `./templates/dev-assignment.json.j2`.

3. Packaged prompt surfaces that mention installed `.claude/...` paths
   - When the source file lives under `packages/<package>/agents`, `commands`, `skills`, or `assets`, resolve install-time `.claude/...` references back to the package source tree first.
   - Example:
     - source prompt: `packages/sc-rust/agents/rust-developer.md`
     - reference: `.claude/skills/rust-development/guidelines.txt`
     - source target: `packages/sc-rust/skills/rust-development/guidelines.txt`
   - If there is no packaged artifact match, fall back to repo-local runtime dependencies such as `.claude/agents/registry.yaml`.

4. Source-tree-only references: `packages/...`
   - Treat these as invalid inside installable prompt surfaces.
   - Prompt artifacts should reference either installed `.claude/...` paths or owner-relative files.

5. Runtime home paths: `~/.claude/...`
   - Do not treat these as hard install-time file dependencies.
   - Keep them as warnings or informational notes unless the specific lint mode is auditing runtime operations.
