# Release Notes Quick Reference Card

**Print this page and keep it handy!**

---

## 1. Choose Your Template Path

```
START
  └─ What release type?
     ├─ v0.x.y → v1.0.0?     → Use MAJOR template
     ├─ v0.x.y → v0.(x+1).0? → Use MINOR template
     └─ v0.x.y → v0.x.(y+1)? → Use PATCH template

START
  └─ What's your package tier?
     ├─ No dependencies?           → Add Tier 0 customization
     ├─ Uses {{REPO_NAME}} etc?    → Add Tier 1 section
     └─ Requires git/node/python?  → Add Tier 2 section
```

---

## 2. Essential Sections Checklist

| Section | For Patch? | For Minor? | For Major? | Required? |
|---------|-----------|-----------|-----------|-----------|
| Header (version, date, status) | ✓ | ✓ | ✓ | YES |
| Executive Summary | Brief | Full | Full | YES |
| What's New (Features/Improvements) | N/A | ✓ | ✓ | For minor+ |
| Bug Fixes | ✓ | ✓ | ✓ | For patches |
| Breaking Changes | N/A | N/A | ✓ | For majors |
| Migration Guide | N/A | N/A | ✓ | For breaking changes |
| Known Issues | Optional | ✓ | ✓ | Recommended |
| Dependencies & Setup | ✓ | ✓ | ✓ | For Tier 2 |
| Upgrade Instructions | ✓ | ✓ | ✓ | YES |
| Support & Resources | ✓ | ✓ | ✓ | YES |

---

## 3. Quick Template Swap-In

### Patch Release (Bug Fix)

```markdown
# Release Notes: {{PKG}} v0.x.Y

**Release Date:** {{DATE}}
**Status:** {{status}}

## Summary
Patch release fixing {{N}} bugs. Fully backward compatible.

## Bug Fixes
- 🐛 {{Issue 1}} — {{description}}
- 🐛 {{Issue 2}} — {{description}}

## Upgrade
```bash
python3 tools/sc-install.py install {{PKG}} --dest {{DEST}} --upgrade
```

## Support
- Issues: [GitHub Issues](link)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
```

### Minor Release (Features)

```markdown
# Release Notes: {{PKG}} v0.{{X+1}}.0

**Release Date:** {{DATE}}
**Status:** {{status}}

## Executive Summary
{{PKG}} v0.{{X+1}}.0 introduces {{N}} features and {{M}} improvements.
Fully backward compatible with v0.{{X}}.0.

**Highlights:**
- 🎯 {{Feature 1 impact}}
- 🚀 {{Feature 2 impact}}
- ⚡ {{Improvement impact}}

## What's New

### Features
- **{{Feature}}**: {{description}} — {{use case}}

### Improvements
- **{{Area}}**: {{improvement}} ({{metric}} impact)

## Upgrade
No special steps. Existing config continues to work.

```bash
python3 tools/sc-install.py install {{PKG}} --dest {{DEST}} --upgrade
```

## Support
- Issues: [GitHub Issues](link)
```

### Major Release (v1.0.0+)

```markdown
# Release Notes: {{PKG}} v1.0.0

**Release Date:** {{DATE}}
**Status:** stable
**Milestone:** Initial stable release

## Executive Summary
🎉 {{PKG}} v1.0.0 is our first stable release with {{features}}.

## Breaking Changes

> ⚠️ BREAKING — Action required

**Change:** {{description}}
```
Old: {{old usage}}
New: {{new usage}}
```

## Migration Guide

### Upgrading from v0.x.0 to v1.0.0

1. {{Step 1}}
2. {{Step 2}}
3. Verify: {{test command}}

## API Stability

v1.0.0 API is stable. Full semver enforced from now on.

## Support
- Docs: [README](./README.md)
- Issues: [GitHub Issues](link)
```

---

## 4. Package-Specific Quick Picks

### delay-tasks (Tier 2 + Global/Local)
- Use: **Tier 2 Template** + **Universal Template**
- Key sections: System Requirements, Installation, Dependency troubleshooting
- Example new feature: `/delay --adaptive --poll --every 30`

### sc-git-worktree (Tier 1 + Local-only)
- Use: **Tier 1 Template** + **Universal Template**
- Key sections: Variable Substitution ({{REPO_NAME}}), Token expansion troubleshooting
- Example new feature: Worktree layout options, tracking document automation

### sc-manage (Tier 2 + Global)
- Use: **Tier 2 Template** + **Universal Template**
- Key sections: Package policy documentation, scope enforcement
- Example new feature: Package search, advanced filtering

### sc-repomix-nuget (Tier 2 + Local-only)
- Use: **Tier 2 Template** + **Universal Template**
- Key sections: Node.js requirement, .NET context generation
- Example new feature: Registry integration, metadata enrichment

---

## 5. Emoji Cheat Sheet

| Emoji | Usage | Example |
|-------|-------|---------|
| 🎯 | Goals, features achieved | 🎯 New API endpoint |
| 🚀 | Launch, acceleration, speed | 🚀 50% faster performance |
| ⚡ | Energy, efficiency | ⚡ Reduced memory by 40% |
| 🐛 | Bug fix | 🐛 Fixed timeout issue |
| ⚠️  | Warning, breaking change | ⚠️ Breaking change ahead |
| ✅ | Approved, working | ✅ Now tested on Windows |
| ❌ | Removed, deprecated | ❌ Dropped Python 3.7 support |
| 🔒 | Security | 🔒 CVE-2025-1234 patched |
| 📊 | Metrics, data | 📊 200% increase in reliability |
| 🎉 | Celebration, milestone | 🎉 First stable release! |
| 📝 | Documentation | 📝 Added troubleshooting guide |
| 🔧 | Setup, configuration | 🔧 New config options |

**Rule:** Max 1 emoji per bullet, none in code blocks

---

## 6. Code Block Template

```markdown
$ bash example
```bash
command --with flags
```

Output:
```
$ command output here
SUCCESS!
```

$ Config example
```json
{"key": "value"}
```

$ Python example
```python
result = function()
print(result)
```
```

**Remember:**
- Specify language: ` ```bash `, ` ```python `, ` ```json `
- Use `$` prefix to show it's runnable
- Show output after
- Keep to 15 lines max

---

## 7. Table Formatting

```markdown
# Good: Clear headers and alignment

| Feature | Before | After | Impact |
|---------|--------|-------|--------|
| Speed | 5s | 1s | 80% faster |
| Memory | 100MB | 50MB | 50% less |

# Good: Left-align text, right-align numbers
| Description | Count |
|:-----------|------:|
| Features | 5 |
| Bugs fixed | 3 |
```

**Tips:**
- Use alignment: `:--` (left), `:--:` (center), `--:` (right)
- Max 6 columns (split if more)
- Keep cells concise

---

## 8. Common Pitfalls → Quick Fixes

| Pitfall | What to Do |
|---------|-----------|
| "Too technical" | Rewrite for non-tech user: "Reduced CPU by 40%" not "Optimized async polling loop" |
| "Too vague" | Add specifics: "Fixed timeout handling" not "Various improvements" |
| "Missing examples" | Add commands: `/delay --poll --adaptive` |
| "Unclear breaking change" | Put at top with ⚠️, add migration steps |
| "No troubleshooting" | Add FAQ section: "Node not found? Install from nodejs.org" |
| "Bad links" | Verify all GitHub issues exist, relative paths work |
| "Grammar errors" | Use spell-check, read aloud for flow |
| "Too long" | Should scan in 5 min; use more headers and lists |

---

## 9. Pre-Publish Checklist (30 seconds)

- [ ] Version matches package.json/manifest
- [ ] Date is today
- [ ] Status is correct (alpha/beta/stable)
- [ ] All example commands tested and work
- [ ] All GitHub issue links valid (not 404)
- [ ] Relative paths correct (./README.md works)
- [ ] No {{TEMPLATE_VARIABLES}} left unreplaced
- [ ] Markdown renders without errors
- [ ] Breaking changes at top with ⚠️
- [ ] Upgrade instructions clear
- [ ] Support links point to real resources

---

## 10. File Locations

**Release Notes Location:**

```
packages/
├── delay-tasks/
│   ├── README.md                    ← Usage & installation
│   ├── CHANGELOG.md                 ← Detailed change log
│   ├── RELEASE-NOTES-v0.5.0.md      ← User-friendly release (optional)
│   └── TROUBLESHOOTING.md           ← Common issues
├── sc-git-worktree/
├── sc-manage/
└── sc-repomix-nuget/

docs/
├── RELEASE-NOTES-TEMPLATE.md        ← This file
├── RELEASE-NOTES-QUICK-REFERENCE.md ← Quick card
└── registries/nuget/
    └── registry.json                ← Points to release notes
```

**Registry Metadata:**

```json
{
  "name": "package-name",
  "version": "X.Y.Z",
  "changelog": "https://raw.githubusercontent.com/randlee/synaptic-canvas/main/packages/package-name/CHANGELOG.md",
  "lastUpdated": "2025-12-02"
}
```

---

## 11. Release Workflow

```
1. Feature/bug complete
   ↓
2. Update CHANGELOG.md under [Unreleased]
   ↓
3. Bump version in package.json/manifest
   ↓
4. Create release notes from template
   ↓
5. Run checklist (section 9)
   ↓
6. Create GitHub release
   ↓
7. Update registry.json (lastUpdated, version)
   ↓
8. Announce in Discussions/Twitter
```

---

## 12. Quick Template Links

**Full Templates:** [docs/RELEASE-NOTES-TEMPLATE.md](./RELEASE-NOTES-TEMPLATE.md)

**By Release Type:**
- [Universal Template](./RELEASE-NOTES-TEMPLATE.md#universal-template)
- [Patch Release](./RELEASE-NOTES-TEMPLATE.md#patch-release-v0xy--v0xy1)
- [Minor Release](./RELEASE-NOTES-TEMPLATE.md#minor-release-v0xy--v0x10)
- [Major Release](./RELEASE-NOTES-TEMPLATE.md#major-release-v0xy--v100)

**By Package Tier:**
- [Tier 0 (Simple)](./RELEASE-NOTES-TEMPLATE.md#tier-0-no-dependencies)
- [Tier 1 (Tokens)](./RELEASE-NOTES-TEMPLATE.md#tier-1-token-substitution)
- [Tier 2 (Dependencies)](./RELEASE-NOTES-TEMPLATE.md#tier-2-external-dependencies)

**By Package:**
- [delay-tasks](#package-specific-quick-picks)
- [sc-git-worktree](#package-specific-quick-picks)
- [sc-manage](#package-specific-quick-picks)
- [sc-repomix-nuget](#package-specific-quick-picks)

---

## 13. Example: Copy & Go

**You:** "I'm releasing v0.5.0 of delay-tasks with 2 features and 1 bug fix. What template?"

**Answer:**
1. Minor release (0.4.0 → 0.5.0) → Use **Minor Release template**
2. Tier 2 (needs Python) → Add **Tier 2 section** about system requirements
3. Copy template → Fill in {{PLACEHOLDERS}} → Test commands → Publish!

**You:** "I'm releasing v0.4.1 patch of sc-git-worktree with a token expansion bug fix"

**Answer:**
1. Patch release (0.4.0 → 0.4.1) → Use **Patch Release template**
2. Tier 1 (token substitution) → Add **Tier 1 section** about {{REPO_NAME}} fix
3. Keep it short → Template, fill, test, done!

**You:** "v1.0.0 major for sc-manage with breaking changes to the API"

**Answer:**
1. Major release (0.4.0 → 1.0.0) → Use **Major Release template**
2. Has breaking changes → Add **Breaking Changes section** with ⚠️
3. Include **Migration Guide** with step-by-step upgrade
4. Full comprehensive release notes!

---

## Quick Wins

**Want to save 30 minutes?**

1. Copy the appropriate template (patch/minor/major)
2. Replace {{PLACEHOLDERS}} with your data
3. Add 3-4 feature/bug descriptions
4. Run checklist
5. Done! Publish.

**Format takes: ~2-3 hours for comprehensive notes**
**Patch notes: ~30 minutes**
**Minor notes: ~1 hour**
**Major notes: ~2 hours**

---

## Still Confused?

Check the [Full Template Documentation](./RELEASE-NOTES-TEMPLATE.md) for:
- Complete examples (good & bad)
- Real-world scenarios
- In-depth formatting guide
- Full checklist with explanations

---

**Print this page for quick reference while writing!**

Last updated: 2025-12-02
