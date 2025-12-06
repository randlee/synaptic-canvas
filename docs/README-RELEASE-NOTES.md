# Release Notes Documentation Hub

This directory contains comprehensive templates and guides for creating professional release notes for Synaptic Canvas packages.

## Files in This Directory

### 1. RELEASE-NOTES-TEMPLATE.md (40KB, 1461 lines)
**The complete reference guide**

Comprehensive master template covering:
- Universal template for all package types
- Package-tier specific variants (Tier 0, 1, 2)
- Release type templates (patch, minor, major)
- Markdown formatting guidelines with examples
- Real-world scenarios and case studies
- Complete pre-publish checklist
- Troubleshooting and common pitfalls

**When to use:** First-time release notes, complex releases, need comprehensive guidance

**Time to read:** 20-30 minutes
**Time to write release notes:** 2-3 hours (major), 1 hour (minor), 30 minutes (patch)

### 2. RELEASE-NOTES-QUICK-REFERENCE.md (8KB, 380 lines)
**Print this and keep it handy!**

One-page quick reference with:
- Template selection flowchart
- Essential sections checklist
- Quick template swap-ins (copy/paste ready)
- Package-specific picks
- Emoji cheat sheet
- Code block templates
- Common pitfalls & fixes
- 30-second pre-publish checklist

**When to use:** During release notes writing, need quick answers, looking for examples

**Time to read:** 5 minutes
**Time to reference:** 1-2 minutes per section

---

## Quick Start Guide

### First Time Creating Release Notes?

1. **Read:** [Quick Start](#quick-start-guide) section below (5 min)
2. **Choose:** Your package and release type using the flowchart (1 min)
3. **Copy:** Appropriate template from RELEASE-NOTES-TEMPLATE.md
4. **Fill:** Replace all {{PLACEHOLDER}} variables
5. **Test:** Run all example commands to verify they work
6. **Verify:** Use the pre-publish checklist
7. **Publish:** Create GitHub release and update registry.json

**Total time:** 1-3 hours depending on release type

### I'm in a Hurry!

1. **Quick Reference:** Open RELEASE-NOTES-QUICK-REFERENCE.md
2. **Find your package:** sc-delay-tasks | sc-git-worktree | sc-manage | sc-repomix-nuget
3. **Find your release type:** patch | minor | major
4. **Copy template:** From section 3 "Quick Template Swap-In"
5. **Fill blanks:** {{DATE}}, {{PKG}}, features, etc.
6. **Verify with checklist:** Section 9 (30 seconds)

**Total time:** 30-60 minutes

---

## Decision Tree

```
┌─ What release type is this?
│  ├─ Patch (0.x.y → 0.x.y+1)? Bug fixes only
│  │  └─ Use: PATCH template + package tier supplement
│  │
│  ├─ Minor (0.x.y → 0.x+1.0)? Features + improvements
│  │  └─ Use: MINOR template + package tier supplement
│  │
│  └─ Major (0.x.y → 1.0.0)? Stable API + breaking changes
│     └─ Use: MAJOR template + migration guide
│
└─ What package tier?
   ├─ Tier 0 (no dependencies)? ← Simple
   │  └─ Simplify: Remove Dependencies/Setup section
   │
   ├─ Tier 1 (token substitution)? ← Uses {{REPO_NAME}}
   │  └─ Add: Variable Substitution section
   │
   └─ Tier 2 (external tools)? ← Needs git/node/python
      └─ Add: System Requirements + Troubleshooting sections
```

---

## Package Quick Reference

| Package | Tier | Scope | Release Path |
|---------|------|-------|--------------|
| **sc-delay-tasks** | 2 | Global/Local | [Tier 2](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies) + [Universal](./RELEASE-NOTES-TEMPLATE.md#universal-template) |
| **sc-git-worktree** | 1 | Local-only | [Tier 1](./RELEASE-NOTES-TEMPLATE.md#tier-1-token-substitution) + [Universal](./RELEASE-NOTES-TEMPLATE.md#universal-template) |
| **sc-manage** | 2 | Global | [Tier 2](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies) + [Universal](./RELEASE-NOTES-TEMPLATE.md#universal-template) |
| **sc-repomix-nuget** | 2 | Local-only | [Tier 2](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies) + [Universal](./RELEASE-NOTES-TEMPLATE.md#universal-template) |

---

## Template Selection Flowchart

### By Release Type

**Patch Release (v0.x.y → v0.x.y+1)**
- Content: Bug fixes only
- Length: 1-2 paragraphs
- Time: 30 minutes
- Template: [RELEASE-NOTES-TEMPLATE.md#patch-release](./RELEASE-NOTES-TEMPLATE.md#patch-release-v0xy--v0xy1)
- Quick ref: [Quick Reference § 3](./RELEASE-NOTES-QUICK-REFERENCE.md#3-quick-template-swap-in)

**Minor Release (v0.x.y → v0.x+1.0)**
- Content: Features + improvements (backward compatible)
- Length: 3-5 sections
- Time: 1 hour
- Template: [RELEASE-NOTES-TEMPLATE.md#minor-release](./RELEASE-NOTES-TEMPLATE.md#minor-release-v0xy--v0x10)
- Quick ref: [Quick Reference § 3](./RELEASE-NOTES-QUICK-REFERENCE.md#3-quick-template-swap-in)

**Major Release (v0.x.y → v1.0.0)**
- Content: Breaking changes + stable API
- Length: 6+ sections including migration guide
- Time: 2-3 hours
- Template: [RELEASE-NOTES-TEMPLATE.md#major-release](./RELEASE-NOTES-TEMPLATE.md#major-release-v0xy--v100)
- Quick ref: [Quick Reference § 3](./RELEASE-NOTES-QUICK-REFERENCE.md#3-quick-template-swap-in)

### By Package Tier

**Tier 0 (No Dependencies)**
- Simplest setup
- Skip Dependencies section
- Template: [RELEASE-NOTES-TEMPLATE.md#tier-0](./RELEASE-NOTES-TEMPLATE.md#tier-0-no-dependencies)
- Example: Simple utility packages

**Tier 1 (Token Substitution)**
- Includes variable expansion (e.g., {{REPO_NAME}})
- Add Variable Substitution section
- Template: [RELEASE-NOTES-TEMPLATE.md#tier-1](./RELEASE-NOTES-TEMPLATE.md#tier-1-token-substitution)
- Example: sc-git-worktree uses {{REPO_NAME}} for path expansion

**Tier 2 (External Dependencies)**
- Requires external tools (git, Node.js, Python)
- Add System Requirements + Installation sections
- Template: [RELEASE-NOTES-TEMPLATE.md#tier-2](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies)
- Examples: sc-delay-tasks, sc-repomix-nuget, sc-manage

---

## Content Checklist

### Essential for All Releases

- [ ] Release header with version, date, and status
- [ ] Executive summary (1-2 sentences)
- [ ] Upgrade instructions
- [ ] Support resources (issues, docs)
- [ ] Link to CHANGELOG.md

### For Minor Releases

- [ ] What's New section (features + improvements)
- [ ] Bug fixes (if any)
- [ ] Known issues/limitations
- [ ] Installation instructions (if new)

### For Patch Releases

- [ ] Bug fixes section (with before/after)
- [ ] Workarounds for older versions (if applicable)
- [ ] Minimal new content

### For Major Releases

- [ ] **Breaking Changes** section (prominently marked ⚠️)
- [ ] **Migration Guide** (step-by-step)
- [ ] API stability guarantees
- [ ] Versioning policy
- [ ] Roadmap

### For Tier 2 Packages

- [ ] System requirements (with version constraints)
- [ ] Dependency verification commands
- [ ] Installation troubleshooting
- [ ] Common issues & solutions

### For Tier 1 Packages

- [ ] Variable substitution documentation
- [ ] Token expansion examples
- [ ] Troubleshooting token issues

---

## Examples

### Good Release Notes Example

See [RELEASE-NOTES-TEMPLATE.md#good-release-notes-example](./RELEASE-NOTES-TEMPLATE.md#good-release-notes-example)

Real-world example for sc-delay-tasks v0.5.0:
- Clear feature descriptions with use cases
- Before/after comparison for improvements
- Specific bug references
- Troubleshooting section
- Upgrade path clearly explained

### Poor Release Notes Example (What to Avoid)

See [RELEASE-NOTES-TEMPLATE.md#poor-release-notes-example-what-to-avoid](./RELEASE-NOTES-TEMPLATE.md#poor-release-notes-example-what-to-avoid)

Common mistakes:
- Too technical ("Refactored async polling loop")
- Too vague ("Various improvements")
- Missing examples
- No migration guide
- Unclear breaking changes

---

## Markdown Formatting Guidelines

### Emoji Usage
- 🎯 Features & goals
- 🚀 Performance improvements
- ⚡ Efficiency gains
- 🐛 Bug fixes
- ⚠️  Breaking changes & warnings
- ✅ Approved & working
- 🔒 Security improvements
- 📊 Metrics & data
- 🎉 Milestones & celebrations

See [Quick Reference § 5](./RELEASE-NOTES-QUICK-REFERENCE.md#5-emoji-cheat-sheet) for full guide

### Code Blocks

Always specify language:
```bash
# Good
command --flag
```

```python
# Good
result = function()
```

```json
# Good
{"key": "value"}
```

See [Quick Reference § 6](./RELEASE-NOTES-QUICK-REFERENCE.md#6-code-block-template) for examples

### Tables

Use for structured comparisons:
```markdown
| Feature | Before | After | Impact |
|---------|--------|-------|--------|
| Speed | 5s | 1s | 80% faster |
```

See [Quick Reference § 7](./RELEASE-NOTES-QUICK-REFERENCE.md#7-table-formatting) for guidance

### Lists

Unordered (-) for concepts:
```markdown
- Feature 1
- Feature 2
  - Sub-feature 2a
```

Ordered (1, 2, 3) for procedures:
```markdown
1. First step
2. Second step
3. Third step
```

---

## File Organization

```
docs/
├── README-RELEASE-NOTES.md          ← You are here
├── RELEASE-NOTES-TEMPLATE.md        ← Full comprehensive template (1461 lines)
└── RELEASE-NOTES-QUICK-REFERENCE.md ← Quick card (380 lines)

packages/
├── sc-delay-tasks/
│   ├── README.md                    ← Usage & installation
│   ├── CHANGELOG.md                 ← Detailed changelog
│   └── RELEASE-NOTES-v0.5.0.md      ← User-friendly summary (optional)
├── sc-git-worktree/
│   ├── README.md
│   ├── CHANGELOG.md
│   └── RELEASE-NOTES-v0.4.1.md
├── sc-manage/
│   └── (same structure)
└── sc-repomix-nuget/
    └── (same structure)
```

---

## Writing Tips

### Golden Rules

1. **Clarity First** - Write for both technical and non-technical users
2. **Scannability** - Use headers, bullets, and tables (read in 5 minutes max)
3. **Actionability** - Users should know exactly what to do
4. **Transparency** - Highlight breaking changes and risks prominently
5. **Completeness** - Include everything needed to make informed decisions

### Avoid These Pitfalls

| Issue | Solution |
|-------|----------|
| Too technical | Rewrite for a non-technical user |
| Too vague | Add specifics and examples |
| Missing examples | Include copy-paste ready commands |
| Unclear breaking changes | Put at top with ⚠️ and migration steps |
| No troubleshooting | Add FAQ with common issues |
| Bad or broken links | Verify all links work before publishing |

---

## Pre-Publish Checklist (30 seconds)

- [ ] Version matches manifest
- [ ] Date is correct
- [ ] Status is correct (alpha/beta/stable)
- [ ] All example commands tested
- [ ] All GitHub issue links valid
- [ ] All relative paths work
- [ ] No {{TEMPLATE_VARIABLES}} left
- [ ] Markdown renders without errors
- [ ] Breaking changes at top with ⚠️
- [ ] Upgrade instructions clear
- [ ] Support links point to real resources

See [RELEASE-NOTES-TEMPLATE.md#release-notes-checklist](./RELEASE-NOTES-TEMPLATE.md#release-notes-checklist) for detailed checklist

---

## Release Workflow

```
1. Feature/bugfix complete
   ↓
2. Update CHANGELOG.md (under [Unreleased])
   ↓
3. Bump version in manifest
   ↓
4. Create release notes from template
   ↓
5. Run pre-publish checklist
   ↓
6. Create GitHub release
   ↓
7. Update registry.json (version, lastUpdated)
   ↓
8. Announce in Discussions/Twitter
   ↓
9. Archive for historical reference
```

---

## Registry Metadata

When publishing a release, update `docs/registries/nuget/registry.json`:

```json
{
  "name": "package-name",
  "version": "X.Y.Z",
  "status": "alpha|beta|stable",
  "changelog": "https://raw.githubusercontent.com/randlee/synaptic-canvas/main/packages/package-name/CHANGELOG.md",
  "lastUpdated": "2025-12-02"
}
```

The registry points to:
1. **README.md** - Installation & usage
2. **CHANGELOG.md** - Detailed change log
3. **RELEASE-NOTES-vX.Y.Z.md** (optional) - User-friendly summary
4. **TROUBLESHOOTING.md** (optional) - Common issues

---

## Frequently Asked Questions

### Q: How long should release notes be?

**A:** Should scan in 5 minutes max. Use headers, lists, and tables for scannability.
- Patch: 1-2 sections
- Minor: 3-5 sections  
- Major: 6+ sections

### Q: Do I need both CHANGELOG.md and RELEASE-NOTES.md?

**A:** 
- **CHANGELOG.md:** Detailed, technical change log (Keep a Changelog format)
- **RELEASE-NOTES.md:** User-friendly summary with context (optional but recommended)

The registry points to CHANGELOG.md. RELEASE-NOTES.md is supplementary.

### Q: Should I include security advisories every release?

**A:**
- If there are CVEs or security fixes: YES, include dedicated section with ⚠️
- If there are no security updates: Write "None for this release"

### Q: What if I'm not sure about version number?

**A:** Use Semantic Versioning (semver.org):
- PATCH (0.x.y → 0.x.y+1): Bug fixes
- MINOR (0.x.y → 0.x+1.0): Features, backward compatible
- MAJOR (0.x.y → 1.0.0+): Breaking changes

### Q: How do I handle breaking changes?

**A:** 
1. Put in dedicated section at top with ⚠️
2. Show old vs new usage
3. Provide migration guide with steps
4. Offer rollback instructions
5. Link to issue for discussion

### Q: Template too long. Can I skip sections?

**A:** Use tier-specific templates:
- **Tier 0:** Skip Dependencies, simplify Installation
- **Tier 1:** Skip Dependencies, add Variable Substitution
- **Tier 2:** Include full Dependencies section
- **Patch:** Skip Features/Improvements, focus on fixes
- **Minor:** Include Features/Improvements
- **Major:** Include Breaking Changes + Migration Guide

---

## Getting Help

### I need more examples
→ See [RELEASE-NOTES-TEMPLATE.md#examples](./RELEASE-NOTES-TEMPLATE.md#examples) for good and bad examples

### I'm writing a major release
→ See [RELEASE-NOTES-TEMPLATE.md#major-release](./RELEASE-NOTES-TEMPLATE.md#major-release-v0xy--v100) template

### I need a quick 30-second reference
→ Print [RELEASE-NOTES-QUICK-REFERENCE.md](./RELEASE-NOTES-QUICK-REFERENCE.md)

### I don't know which template to use
→ Use flowchart in [RELEASE-NOTES-TEMPLATE.md#template-selection-guide](./RELEASE-NOTES-TEMPLATE.md#template-selection-guide)

### I want to see a real example
→ Check [Real-World Scenarios](#real-world-scenarios) section or look at actual releases in `packages/*/CHANGELOG.md`

---

## Real-World Scenarios

### Scenario 1: You're releasing sc-delay-tasks v0.5.0 (minor release, Tier 2)

1. Use: [Minor Release template](./RELEASE-NOTES-TEMPLATE.md#minor-release-v0xy--v0x10) + [Tier 2 template](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies)
2. Sections: Features, Improvements, Dependencies, Installation, Upgrade
3. Example: [See in template](./RELEASE-NOTES-TEMPLATE.md#scenario-1-user-with-sc-delay-tasks-tier-2)
4. Time: ~1 hour

### Scenario 2: You're releasing sc-git-worktree v0.4.1 (patch release, Tier 1)

1. Use: [Patch Release template](./RELEASE-NOTES-TEMPLATE.md#patch-release-v0xy--v0xy1) + [Tier 1 template](./RELEASE-NOTES-TEMPLATE.md#tier-1-token-substitution)
2. Sections: Bug fixes, Token substitution section, Upgrade
3. Example: [See in template](./RELEASE-NOTES-TEMPLATE.md#scenario-2-user-with-sc-repomix-nuget-tier-2)
4. Time: ~30 minutes

### Scenario 3: You're releasing v1.0.0 (major, stable)

1. Use: [Major Release template](./RELEASE-NOTES-TEMPLATE.md#major-release-v0xy--v100) + your package tier
2. Sections: Breaking changes, Migration guide, API stability, Everything else
3. Example: [See in template](./RELEASE-NOTES-TEMPLATE.md#major-release-v0xy--v100)
4. Time: ~2-3 hours

---

## Contributing to This Guide

Found an issue or want to improve these templates?

- Open issue: [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- Submit feedback: [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
- Edit template: Submit PR to `docs/RELEASE-NOTES-*.md`

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-02 | Initial comprehensive release with all templates |
| 1.0.0 | — | Planned for future updates |

**Last Updated:** 2025-12-02
**Maintained By:** Synaptic Canvas Team
**License:** MIT (same as project)

---

**Ready to write release notes? Start here:**

1. **Quick:** [RELEASE-NOTES-QUICK-REFERENCE.md](./RELEASE-NOTES-QUICK-REFERENCE.md)
2. **Comprehensive:** [RELEASE-NOTES-TEMPLATE.md](./RELEASE-NOTES-TEMPLATE.md)
3. **Questions?** Check FAQ section above
