# Claude Code Marketplace Infrastructure Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-16
**Audience:** Marketplace operators, infrastructure architects, package publishers

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [Registry Setup](#registry-setup)
5. [Hosting Options](#hosting-options)
6. [Discovery Protocol](#discovery-protocol)
7. [Package Distribution](#package-distribution)
8. [Security Considerations](#security-considerations)
9. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
10. [Multi-Registry Support](#multi-registry-support)
11. [Monitoring & Maintenance](#monitoring--maintenance)
12. [Troubleshooting](#troubleshooting)
13. [Advanced Topics](#advanced-topics)

---

## Overview

A **Claude Code marketplace** is a discoverable registry of skills, agents, and commands that users can install via the `/plugin` command. This guide explains how to create and operate your own marketplace.

### What You'll Build

By following this guide, you'll create:

- A **registry.json** file describing available packages
- **Package distribution** infrastructure
- **Discovery endpoints** for Claude Code integration
- **Version management** system
- **Publisher verification** (optional)

### Who Should Read This

- **Marketplace operators** - Setting up internal/public marketplaces
- **Enterprise admins** - Deploying private package registries
- **Package publishers** - Understanding marketplace infrastructure
- **Platform developers** - Building marketplace tooling

### Prerequisites

- Git repository (GitHub, GitLab, Bitbucket, or self-hosted)
- Basic understanding of JSON and HTTP
- Text editor or IDE
- (Optional) Web hosting or CDN

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /plugin marketplace add <owner>/<repo>              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 1. Discovery Request
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Marketplace Registry (HTTP/HTTPS)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GET /docs/registries/nuget/registry.json            │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 2. Registry Response
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      registry.json                           │
│  {                                                            │
│    "marketplace": { "name": "...", "version": "..." },       │
│    "packages": {                                             │
│      "package-name": {                                       │
│        "version": "1.0.0",                                   │
│        "path": "packages/package-name",                      │
│        "artifacts": { ... }                                  │
│      }                                                        │
│    }                                                          │
│  }                                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 3. Package Installation
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Package Artifacts                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GET /packages/package-name/manifest.yaml            │  │
│  │  GET /packages/package-name/commands/cmd.md          │  │
│  │  GET /packages/package-name/agents/agent.md          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ 4. Installation
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              User's .claude/ Directory                       │
│  .claude/                                                     │
│  ├── commands/                                               │
│  │   └── package-cmd.md                                     │
│  ├── agents/                                                 │
│  │   └── package-agent.md                                   │
│  └── skills/                                                 │
│      └── package-skill/SKILL.md                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery**: User runs `/plugin marketplace add owner/repo`
2. **Registry Fetch**: Claude Code fetches `registry.json` from known path
3. **Package Browse**: User browses packages via `/plugin` UI
4. **Installation**: User selects package, Claude Code fetches artifacts
5. **Deployment**: Artifacts copied to user's `.claude/` directory

### URL Resolution

Claude Code resolves marketplace URLs using this pattern:

```
Input:  /plugin marketplace add randlee/synaptic-canvas
Resolves to:
  1. https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json
  2. (If 404) https://raw.githubusercontent.com/randlee/synaptic-canvas/master/docs/registries/nuget/registry.json
  3. (If 404) https://randlee.github.io/synaptic-canvas/registries/nuget/registry.json
```

---

## Infrastructure Requirements

### Minimal Setup (GitHub Only)

**Required:**
- ✅ GitHub repository (public or private)
- ✅ `docs/registries/nuget/registry.json` file
- ✅ Package directories with manifest.yaml files

**No additional infrastructure needed!**

GitHub raw URLs serve files automatically:
```
https://raw.githubusercontent.com/owner/repo/main/docs/registries/nuget/registry.json
```

### Recommended Setup (GitHub + Pages)

**Adds:**
- ✅ GitHub Pages for better caching
- ✅ Custom domain (optional)
- ✅ HTTPS by default
- ✅ CDN distribution

**Benefits:**
- Faster downloads
- Better availability
- Professional URLs
- Lower rate limits

### Enterprise Setup (Self-Hosted)

**Required:**
- ✅ Web server (nginx, Apache, Caddy)
- ✅ HTTPS certificate
- ✅ Version control system
- ✅ CI/CD pipeline for registry updates

**Optional:**
- CDN (Cloudflare, CloudFront)
- Authentication layer
- Usage analytics
- Package signing infrastructure

---

## Registry Setup

### Registry File Structure

The `registry.json` file is the heart of your marketplace. It describes all available packages.

**Location:** `docs/registries/nuget/registry.json`

**Why this path?**
- Claude Code expects this specific path
- `nuget` refers to the registry format version
- Multiple registries can coexist in subdirectories

### Minimal registry.json

```json
{
  "$schema": "https://yourcompany.github.io/schemas/package-registry.schema.json",
  "version": "2.0.0",
  "generated": "2025-12-16T00:00:00Z",
  "repo": "your-org/your-marketplace",
  "marketplace": {
    "name": "Your Marketplace Name",
    "version": "1.0.0",
    "status": "stable",
    "url": "https://github.com/your-org/your-marketplace"
  },
  "packages": {
    "example-package": {
      "name": "example-package",
      "version": "1.0.0",
      "status": "stable",
      "tier": 0,
      "description": "A sample package demonstrating basic functionality",
      "github": "your-org/your-marketplace",
      "repo": "https://github.com/your-org/your-marketplace",
      "path": "packages/example-package",
      "readme": "https://raw.githubusercontent.com/your-org/your-marketplace/main/packages/example-package/README.md",
      "license": "MIT",
      "author": "Your Name",
      "tags": ["example", "demo"],
      "artifacts": {
        "commands": 1,
        "skills": 1,
        "agents": 2,
        "scripts": 0
      },
      "dependencies": [],
      "changelog": "https://raw.githubusercontent.com/your-org/your-marketplace/main/packages/example-package/CHANGELOG.md",
      "lastUpdated": "2025-12-16",
      "dependents": []
    }
  },
  "metadata": {
    "registryVersion": "2.0.0",
    "schemaVersion": "1.0.0",
    "totalPackages": 1,
    "totalCommands": 1,
    "totalSkills": 1,
    "totalAgents": 2,
    "totalScripts": 0,
    "categories": {
      "examples": ["example-package"]
    }
  },
  "versionCompatibility": {
    "marketplace": "1.0.0",
    "minimumPackageVersion": "1.0.0",
    "maximumPackageVersion": "1.x.x",
    "note": "Stable release with long-term support"
  }
}
```

### Registry Fields Reference

#### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$schema` | string | No | JSON Schema URL for validation |
| `version` | string | Yes | Registry format version (e.g., "2.0.0") |
| `generated` | string | Yes | ISO 8601 timestamp of last update |
| `repo` | string | Yes | GitHub repo path (owner/repo) |
| `marketplace` | object | Yes | Marketplace metadata |
| `packages` | object | Yes | Package definitions (key = package name) |
| `metadata` | object | Yes | Registry statistics and categorization |
| `versionCompatibility` | object | Yes | Version constraints |
| `publishers` | object | No | Publisher verification info |

#### Marketplace Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name of marketplace |
| `version` | string | Yes | Marketplace platform version |
| `status` | string | Yes | "beta", "stable", or "deprecated" |
| `url` | string | Yes | Homepage URL |

#### Package Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Package identifier (kebab-case) |
| `version` | string | Yes | SemVer version (e.g., "1.0.0") |
| `status` | string | Yes | "beta", "stable", "deprecated" |
| `tier` | integer | Yes | 0 (no deps), 1 (tokens), 2 (runtime deps) |
| `description` | string | Yes | One-line package description |
| `github` | string | Yes | GitHub repo path |
| `repo` | string | Yes | Full repo URL |
| `path` | string | Yes | Path to package directory |
| `readme` | string | Yes | URL to README.md |
| `license` | string | Yes | License identifier (e.g., "MIT") |
| `author` | string | Yes | Author name or organization |
| `tags` | array | Yes | Search tags |
| `artifacts` | object | Yes | Count of each artifact type |
| `dependencies` | array | Yes | Runtime dependencies (empty for Tier 0) |
| `changelog` | string | Yes | URL to CHANGELOG.md |
| `lastUpdated` | string | Yes | ISO 8601 date |
| `dependents` | array | Yes | Packages that depend on this one |
| `variables` | object | No | Token substitution variables (Tier 1) |

#### Artifact Counts

```json
"artifacts": {
  "commands": 2,    // Number of slash commands
  "skills": 1,      // Number of skills
  "agents": 5,      // Number of agents
  "scripts": 1      // Number of helper scripts
}
```

#### Package Tiers

**Tier 0: Direct Copy**
- No token substitution
- No external dependencies
- Works immediately after installation
```json
{
  "tier": 0,
  "dependencies": [],
  "variables": {}  // Omit entirely
}
```

**Tier 1: Token Substitution**
- Requires variable substitution at install time
- Auto-detected from environment
```json
{
  "tier": 1,
  "dependencies": ["git >= 2.27"],
  "variables": {
    "REPO_NAME": {
      "auto": "git-repo-basename",
      "description": "Repository name from git toplevel"
    }
  }
}
```

**Tier 2: Runtime Dependencies**
- External tools required before use
```json
{
  "tier": 2,
  "dependencies": [
    "python3 >= 3.12",
    "gh >= 2.0"
  ]
}
```

### Creating Your registry.json

**Step 1: Initialize the file**
```bash
mkdir -p docs/registries/nuget
cat > docs/registries/nuget/registry.json <<'EOF'
{
  "version": "2.0.0",
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "your-org/your-marketplace",
  "marketplace": {
    "name": "Your Marketplace",
    "version": "1.0.0",
    "status": "stable",
    "url": "https://github.com/your-org/your-marketplace"
  },
  "packages": {},
  "metadata": {
    "registryVersion": "2.0.0",
    "totalPackages": 0
  }
}
EOF
```

**Step 2: Add your first package**
```json
{
  "packages": {
    "my-first-package": {
      "name": "my-first-package",
      "version": "1.0.0",
      "status": "stable",
      "tier": 0,
      "description": "My first Claude Code package",
      "github": "your-org/your-marketplace",
      "repo": "https://github.com/your-org/your-marketplace",
      "path": "packages/my-first-package",
      "readme": "https://raw.githubusercontent.com/your-org/your-marketplace/main/packages/my-first-package/README.md",
      "license": "MIT",
      "author": "Your Name",
      "tags": ["utility", "automation"],
      "artifacts": {
        "commands": 1,
        "skills": 0,
        "agents": 1,
        "scripts": 0
      },
      "dependencies": [],
      "changelog": "https://raw.githubusercontent.com/your-org/your-marketplace/main/packages/my-first-package/CHANGELOG.md",
      "lastUpdated": "2025-12-16",
      "dependents": []
    }
  }
}
```

**Step 3: Validate JSON**
```bash
# Check JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Or use jq
jq empty docs/registries/nuget/registry.json && echo "Valid JSON"
```

---

## Hosting Options

### Option 1: GitHub Raw URLs (Simplest)

**Pros:**
- ✅ Zero setup required
- ✅ Free forever
- ✅ Works immediately
- ✅ Automatic versioning (git branches/tags)

**Cons:**
- ❌ Rate limiting (5,000 requests/hour for authenticated)
- ❌ No custom domain
- ❌ Slower than CDN
- ❌ No analytics

**Setup:**
```bash
# 1. Commit your registry
git add docs/registries/nuget/registry.json
git commit -m "Add marketplace registry"
git push

# 2. Test access
curl https://raw.githubusercontent.com/your-org/your-marketplace/main/docs/registries/nuget/registry.json

# 3. Users add marketplace
/plugin marketplace add your-org/your-marketplace
```

**URL Pattern:**
```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/docs/registries/nuget/registry.json
```

---

### Option 2: GitHub Pages (Recommended)

**Pros:**
- ✅ Free for public repos
- ✅ Custom domain support
- ✅ HTTPS by default
- ✅ CDN-backed (Fastly)
- ✅ Better rate limits
- ✅ Professional appearance

**Cons:**
- ❌ 1 GB repository size limit
- ❌ 100 GB/month bandwidth soft limit
- ❌ Public repos only (unless GitHub Pro)

**Setup:**

**Step 1: Enable GitHub Pages**
```bash
# In your repo: Settings → Pages
# Source: Deploy from branch
# Branch: main
# Folder: /docs
```

**Step 2: Update file structure**
```bash
# Move registry to web-accessible path
mkdir -p docs/registries/nuget
# registry.json already at correct location
```

**Step 3: Create index page (optional)**
```bash
cat > docs/index.html <<'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Your Marketplace</title>
  <meta charset="UTF-8">
</head>
<body>
  <h1>Your Claude Code Marketplace</h1>
  <p>Add this marketplace to Claude Code:</p>
  <pre><code>/plugin marketplace add your-org/your-marketplace</code></pre>

  <h2>Registry</h2>
  <p><a href="registries/nuget/registry.json">registry.json</a></p>
</body>
</html>
EOF
```

**Step 4: Test deployment**
```bash
# Wait 1-2 minutes for deployment
curl https://your-org.github.io/your-marketplace/registries/nuget/registry.json
```

**Step 5: Custom domain (optional)**
```bash
# Add CNAME file
echo "marketplace.yourcompany.com" > docs/CNAME
git add docs/CNAME
git commit -m "Add custom domain"
git push

# Configure DNS:
# Add CNAME record: marketplace.yourcompany.com → your-org.github.io
```

**URL Pattern:**
```
https://{owner}.github.io/{repo}/registries/nuget/registry.json
# or
https://marketplace.yourcompany.com/registries/nuget/registry.json
```

---

### Option 3: CDN (Cloudflare, CloudFront)

**Pros:**
- ✅ Ultra-fast global distribution
- ✅ DDoS protection
- ✅ Free tier available (Cloudflare)
- ✅ Advanced caching control
- ✅ Analytics included

**Cons:**
- ❌ Requires setup and configuration
- ❌ Potential costs at scale

**Setup (Cloudflare Pages):**

**Step 1: Connect repository**
```bash
# 1. Login to Cloudflare Dashboard
# 2. Pages → Create a project
# 3. Connect to Git → Select your repo
```

**Step 2: Configure build**
```yaml
Build command: (leave empty)
Build output directory: /docs
Branch: main
```

**Step 3: Deploy**
```bash
# Automatic deployment on every push
# URL: https://your-marketplace.pages.dev
```

**Step 4: Custom domain**
```bash
# Cloudflare Pages → Custom domains → Add domain
# DNS automatically configured
```

**URL Pattern:**
```
https://your-marketplace.pages.dev/registries/nuget/registry.json
# or
https://marketplace.yourcompany.com/registries/nuget/registry.json
```

---

### Option 4: Self-Hosted (Enterprise)

**Pros:**
- ✅ Full control
- ✅ Private/internal only
- ✅ Custom authentication
- ✅ Compliance-friendly
- ✅ No external dependencies

**Cons:**
- ❌ Requires infrastructure
- ❌ Ongoing maintenance
- ❌ Uptime responsibility

**Setup (nginx):**

**Step 1: Install nginx**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install nginx

# RHEL/CentOS
sudo yum install nginx
```

**Step 2: Configure site**
```nginx
# /etc/nginx/sites-available/marketplace
server {
    listen 80;
    server_name marketplace.yourcompany.com;

    root /var/www/marketplace;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /registries/ {
        add_header Content-Type application/json;
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=300";
    }
}
```

**Step 3: Deploy files**
```bash
# Create web root
sudo mkdir -p /var/www/marketplace/registries/nuget

# Copy registry
sudo cp docs/registries/nuget/registry.json /var/www/marketplace/registries/nuget/

# Set permissions
sudo chown -R www-data:www-data /var/www/marketplace
sudo chmod -R 755 /var/www/marketplace
```

**Step 4: Enable SSL**
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d marketplace.yourcompany.com
```

**Step 5: Enable and test**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/marketplace /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Test
curl https://marketplace.yourcompany.com/registries/nuget/registry.json
```

**Automation (CI/CD):**
```yaml
# .github/workflows/deploy-registry.yml
name: Deploy Registry

on:
  push:
    branches: [main]
    paths:
      - 'docs/registries/**'
      - 'packages/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: easingthemes/ssh-deploy@main
        env:
          SSH_PRIVATE_KEY: ${{ secrets.DEPLOY_KEY }}
          REMOTE_HOST: marketplace.yourcompany.com
          REMOTE_USER: deploy
          SOURCE: "docs/registries/"
          TARGET: "/var/www/marketplace/registries/"
```

---

## Discovery Protocol

### How Claude Code Finds Your Marketplace

When a user runs `/plugin marketplace add owner/repo`, Claude Code follows this discovery process:

**Step 1: Parse input**
```
Input: your-org/your-marketplace
Parsed:
  - owner: your-org
  - repo: your-marketplace
```

**Step 2: Attempt primary URL**
```bash
GET https://raw.githubusercontent.com/your-org/your-marketplace/main/docs/registries/nuget/registry.json

Status: 200 OK
└─> Success! Registry loaded.

Status: 404 Not Found
└─> Try fallback...
```

**Step 3: Fallback to master branch**
```bash
GET https://raw.githubusercontent.com/your-org/your-marketplace/master/docs/registries/nuget/registry.json

Status: 200 OK
└─> Success! Registry loaded.

Status: 404 Not Found
└─> Try GitHub Pages...
```

**Step 4: Fallback to GitHub Pages**
```bash
GET https://your-org.github.io/your-marketplace/registries/nuget/registry.json

Status: 200 OK
└─> Success! Registry loaded.

Status: 404 Not Found
└─> Error: Marketplace not found
```

### Custom Discovery URLs (Future)

For self-hosted marketplaces, Claude Code may support custom URLs:

```bash
# Full URL format (future feature)
/plugin marketplace add https://marketplace.yourcompany.com/registries/nuget/registry.json

# Short alias (future feature)
/plugin marketplace add mycompany
# Maps to configured URL in ~/.claude/config.yaml
```

### Registry Caching

Claude Code caches registry data to reduce network requests:

- **Cache Duration:** 5 minutes (default)
- **Cache Location:** `~/.claude/cache/registries/`
- **Force Refresh:** `/plugin marketplace refresh`

Cache invalidation:
```bash
# Manual cache clear
rm -rf ~/.claude/cache/registries/your-org-your-marketplace.json

# Or refresh via CLI
/plugin marketplace refresh your-org/your-marketplace
```

---

## Package Distribution

### Package Directory Structure

Each package must follow this structure:

```
packages/your-package/
├── manifest.yaml           # Required: Package metadata
├── README.md              # Required: Package documentation
├── CHANGELOG.md           # Required: Version history
├── LICENSE                # Required: License text
├── USE-CASES.md           # Recommended: Usage examples
├── TROUBLESHOOTING.md     # Recommended: Common issues
├── commands/              # Optional: Slash commands
│   └── your-command.md
├── skills/                # Optional: Workflow orchestrations
│   └── your-skill/
│       └── SKILL.md
├── agents/                # Optional: Isolated executors
│   └── your-agent.md
└── scripts/               # Optional: Helper scripts
    └── helper.sh
```

### manifest.yaml Format

```yaml
name: your-package
version: 1.0.0
description: >
  A comprehensive package that demonstrates
  best practices for Claude Code extensions.
author: Your Name
license: MIT
tags:
  - automation
  - productivity
  - example

# Files to install (relative to package root)
artifacts:
  commands:
    - commands/your-command.md
  skills:
    - skills/your-skill/SKILL.md
  agents:
    - agents/your-agent.md
  scripts:
    - scripts/helper.sh

# Token substitution (Tier 1 only)
variables:
  REPO_NAME:
    auto: git-repo-basename
    description: Repository name from git toplevel

# Runtime requirements (Tier 2 only)
requires:
  - git >= 2.27
  - python3 >= 3.10
```

### Package Installation Flow

When a user installs a package:

```
1. User runs: /plugin install your-package@your-marketplace

2. Claude Code:
   a. Reads registry.json
   b. Finds package entry
   c. Fetches manifest.yaml from package path
   d. Downloads all artifacts listed in manifest
   e. Performs token substitution (Tier 1)
   f. Validates dependencies (Tier 2)
   g. Copies artifacts to ~/.claude/ or ./.claude/

3. Result:
   .claude/
   ├── commands/
   │   └── your-command.md
   ├── agents/
   │   └── your-agent.md
   └── skills/
       └── your-skill/
           └── SKILL.md
```

### Versioning Strategy

Follow semantic versioning (SemVer):

**Version Format:** `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes, incompatible API changes
- **MINOR:** New features, backward-compatible
- **PATCH:** Bug fixes, no API changes

**Example progression:**
```
1.0.0 → Initial stable release
1.0.1 → Bug fix (patch)
1.1.0 → New feature (minor)
2.0.0 → Breaking change (major)
```

**Pre-release versions:**
```
0.1.0 → Early development
0.9.0 → Feature-complete beta
1.0.0-rc.1 → Release candidate (avoid in registry)
1.0.0 → First stable release
```

**Registry version synchronization:**

All three layers must match:

1. **Marketplace version** (registry.json → marketplace.version)
2. **Package version** (registry.json → packages.your-package.version)
3. **Artifact versions** (frontmatter in .md files)

```bash
# Verify version consistency
grep -r "version:" . | grep -E "(registry.json|manifest.yaml|\.md)"
```

---

## Security Considerations

### Registry Security

**1. HTTPS Only**
```
✅ GOOD: https://raw.githubusercontent.com/...
✅ GOOD: https://marketplace.yourcompany.com/...
❌ BAD:  http://marketplace.yourcompany.com/...  (No encryption)
```

**2. Integrity Verification**

Add checksums to registry.json (future feature):
```json
{
  "packages": {
    "your-package": {
      "version": "1.0.0",
      "integrity": {
        "algorithm": "sha256",
        "hash": "a3c2f1e9b...",
        "signatures": [
          {
            "signer": "your-gpg-key-id",
            "signature": "base64-encoded-sig"
          }
        ]
      }
    }
  }
}
```

**3. Rate Limiting**

Protect your registry from abuse:

```nginx
# nginx rate limiting
http {
    limit_req_zone $binary_remote_addr zone=registry:10m rate=10r/s;

    server {
        location /registries/ {
            limit_req zone=registry burst=20 nodelay;
        }
    }
}
```

**4. Access Control**

For private marketplaces:

```nginx
# nginx basic auth
location /registries/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

Or use token-based auth:

```nginx
# nginx token validation
location /registries/ {
    if ($http_authorization != "Bearer your-secret-token") {
        return 403;
    }
}
```

### Package Security

**1. Code Review**

All packages should be reviewed before adding to registry:

```bash
# Review checklist
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all external data
- [ ] No arbitrary code execution
- [ ] Dependencies are pinned versions
- [ ] License is compatible
- [ ] Documentation is complete
```

**2. Dependency Scanning**

```bash
# Scan for known vulnerabilities
npm audit  # If Node.js dependencies
pip-audit  # If Python dependencies
```

**3. Sandboxing**

Agents run in isolated contexts by default. Ensure packages don't:
- Access files outside workspace
- Make unauthorized network requests
- Execute arbitrary commands without user approval

**4. Publisher Verification**

Implement publisher verification:

```json
{
  "publishers": {
    "your-org": {
      "name": "Your Organization",
      "github_handle": "your-org",
      "github_url": "https://github.com/your-org",
      "verification": {
        "level": 2,
        "method": "domain_verification",
        "verified_date": "2025-12-16T00:00:00Z",
        "domain": "yourcompany.com"
      },
      "packages": ["package1", "package2"],
      "total_packages": 2
    }
  }
}
```

Verification levels:
- **Level 0:** Unverified (default)
- **Level 1:** GitHub organization verified
- **Level 2:** Domain ownership verified
- **Level 3:** Code signing with GPG

### Best Practices

1. **Never commit secrets** to registry or packages
2. **Use HTTPS** for all distribution
3. **Pin dependencies** to specific versions
4. **Audit code** before publishing
5. **Sign releases** with GPG (future feature)
6. **Monitor access logs** for unusual patterns
7. **Keep packages updated** with security patches
8. **Document security policies** in SECURITY.md

---

## Step-by-Step Setup Guide

### Scenario 1: Public Marketplace (GitHub + Pages)

**Goal:** Create a public marketplace hosted on GitHub Pages

**Time Required:** 30 minutes

#### Step 1: Create Repository

```bash
# Create new repo on GitHub: your-org/claude-marketplace
git clone https://github.com/your-org/claude-marketplace.git
cd claude-marketplace
```

#### Step 2: Set Up Directory Structure

```bash
# Create required directories
mkdir -p docs/registries/nuget
mkdir -p packages

# Create README
cat > README.md <<'EOF'
# Claude Code Marketplace

A marketplace for Claude Code skills, agents, and commands.

## Installation

```bash
/plugin marketplace add your-org/claude-marketplace
```

## Packages

See [docs/registries/nuget/registry.json](docs/registries/nuget/registry.json) for available packages.
EOF
```

#### Step 3: Create Registry

```bash
cat > docs/registries/nuget/registry.json <<'EOF'
{
  "$schema": "https://your-org.github.io/claude-marketplace/schemas/registry.schema.json",
  "version": "2.0.0",
  "generated": "2025-12-16T00:00:00Z",
  "repo": "your-org/claude-marketplace",
  "marketplace": {
    "name": "Your Company Marketplace",
    "version": "1.0.0",
    "status": "stable",
    "url": "https://github.com/your-org/claude-marketplace"
  },
  "packages": {},
  "metadata": {
    "registryVersion": "2.0.0",
    "schemaVersion": "1.0.0",
    "totalPackages": 0,
    "totalCommands": 0,
    "totalSkills": 0,
    "totalAgents": 0,
    "totalScripts": 0,
    "categories": {}
  },
  "versionCompatibility": {
    "marketplace": "1.0.0",
    "minimumPackageVersion": "1.0.0",
    "maximumPackageVersion": "1.x.x",
    "note": "Stable release"
  }
}
EOF
```

#### Step 4: Add First Package

```bash
# Create package directory
mkdir -p packages/hello-world/{commands,agents}

# Create manifest
cat > packages/hello-world/manifest.yaml <<'EOF'
name: hello-world
version: 1.0.0
description: A simple hello world package
author: Your Name
license: MIT
tags:
  - example
  - demo

artifacts:
  commands:
    - commands/hello.md
  agents:
    - agents/hello-agent.md
EOF

# Create command
cat > packages/hello-world/commands/hello.md <<'EOF'
---
name: hello
description: Print a friendly greeting
version: 1.0.0
---

Print "Hello from Claude Code Marketplace!"
EOF

# Create agent
cat > packages/hello-world/agents/hello-agent.md <<'EOF'
---
name: hello-agent
description: Generate friendly greetings
version: 1.0.0
---

You are a friendly greeting generator. When invoked, generate a warm, personalized greeting.
EOF

# Create README
cat > packages/hello-world/README.md <<'EOF'
# hello-world

A simple example package demonstrating Claude Code marketplace basics.

## Installation

```bash
/plugin install hello-world@your-org/claude-marketplace
```

## Usage

```bash
/hello
```
EOF

# Create CHANGELOG
cat > packages/hello-world/CHANGELOG.md <<'EOF'
# Changelog

## [1.0.0] - 2025-12-16

### Added
- Initial release
- `/hello` command
- hello-agent for greeting generation
EOF
```

#### Step 5: Update Registry with Package

```bash
# Update registry.json to include the package
cat > docs/registries/nuget/registry.json <<'EOF'
{
  "$schema": "https://your-org.github.io/claude-marketplace/schemas/registry.schema.json",
  "version": "2.0.0",
  "generated": "2025-12-16T00:00:00Z",
  "repo": "your-org/claude-marketplace",
  "marketplace": {
    "name": "Your Company Marketplace",
    "version": "1.0.0",
    "status": "stable",
    "url": "https://github.com/your-org/claude-marketplace"
  },
  "packages": {
    "hello-world": {
      "name": "hello-world",
      "version": "1.0.0",
      "status": "stable",
      "tier": 0,
      "description": "A simple hello world package",
      "github": "your-org/claude-marketplace",
      "repo": "https://github.com/your-org/claude-marketplace",
      "path": "packages/hello-world",
      "readme": "https://raw.githubusercontent.com/your-org/claude-marketplace/main/packages/hello-world/README.md",
      "license": "MIT",
      "author": "Your Name",
      "tags": ["example", "demo"],
      "artifacts": {
        "commands": 1,
        "skills": 0,
        "agents": 1,
        "scripts": 0
      },
      "dependencies": [],
      "changelog": "https://raw.githubusercontent.com/your-org/claude-marketplace/main/packages/hello-world/CHANGELOG.md",
      "lastUpdated": "2025-12-16",
      "dependents": []
    }
  },
  "metadata": {
    "registryVersion": "2.0.0",
    "schemaVersion": "1.0.0",
    "totalPackages": 1,
    "totalCommands": 1,
    "totalSkills": 0,
    "totalAgents": 1,
    "totalScripts": 0,
    "categories": {
      "examples": ["hello-world"]
    }
  },
  "versionCompatibility": {
    "marketplace": "1.0.0",
    "minimumPackageVersion": "1.0.0",
    "maximumPackageVersion": "1.x.x",
    "note": "Stable release"
  }
}
EOF
```

#### Step 6: Enable GitHub Pages

```bash
# Commit everything
git add .
git commit -m "Initial marketplace setup with hello-world package"
git push origin main

# Enable GitHub Pages:
# 1. Go to repo Settings → Pages
# 2. Source: Deploy from branch
# 3. Branch: main
# 4. Folder: /docs
# 5. Save

# Wait 1-2 minutes for deployment
```

#### Step 7: Test Installation

```bash
# Verify registry is accessible
curl https://raw.githubusercontent.com/your-org/claude-marketplace/main/docs/registries/nuget/registry.json

# Or via GitHub Pages (after deployment)
curl https://your-org.github.io/claude-marketplace/registries/nuget/registry.json

# In Claude Code:
/plugin marketplace add your-org/claude-marketplace
/plugin install hello-world
/hello
```

#### Step 8: (Optional) Add More Packages

```bash
# Create another package
mkdir -p packages/another-package/{commands,agents,skills}

# Create manifest, artifacts, documentation
# Update registry.json with new package entry
# Commit and push
```

**Congratulations!** You now have a working Claude Code marketplace.

---

### Scenario 2: Private Enterprise Marketplace

**Goal:** Create a private marketplace for internal use

**Requirements:**
- Self-hosted server or private GitHub Enterprise
- Authentication system
- Internal network only

#### Step 1: Set Up Private Repository

```bash
# Create private GitHub repo
# Or use GitLab/Bitbucket/self-hosted Git

git clone https://github.yourcompany.com/internal/claude-marketplace.git
cd claude-marketplace
```

#### Step 2: Create Registry Structure

```bash
# Same structure as public marketplace
mkdir -p docs/registries/nuget
mkdir -p packages

# Create registry.json
# (Same format as public marketplace)
```

#### Step 3: Configure Access Control

**Option A: GitHub Private Repo**

```bash
# Users must authenticate with GitHub
# Claude Code will prompt for credentials

# Configure in ~/.gitconfig
git config --global credential.helper store
git config --global credential.https://github.yourcompany.com.username your-username
```

**Option B: Self-Hosted with nginx**

```nginx
# /etc/nginx/sites-available/marketplace
server {
    listen 443 ssl;
    server_name marketplace.internal.company.com;

    ssl_certificate /etc/nginx/ssl/marketplace.crt;
    ssl_certificate_key /etc/nginx/ssl/marketplace.key;

    root /var/www/marketplace;

    # IP whitelist (internal network only)
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;

    # Basic auth
    auth_basic "Internal Marketplace";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        try_files $uri $uri/ =404;
    }

    location /registries/ {
        add_header Content-Type application/json;
    }
}
```

#### Step 4: Configure Claude Code

```yaml
# ~/.claude/config.yaml (future feature)
marketplaces:
  - name: internal
    url: https://marketplace.internal.company.com/registries/nuget/registry.json
    auth:
      type: basic
      username: your-username
      password: ${MARKETPLACE_PASSWORD}  # Environment variable
```

#### Step 5: Distribution

```bash
# Option A: Distribute via internal docs
# Create setup guide for employees

# Option B: Automate via MDM/configuration management
# Use Ansible/Puppet/Chef to deploy config

# Option C: Docker image with pre-configured Claude Code
docker build -t internal/claude-code:latest .
```

---

## Multi-Registry Support

Claude Code supports multiple registries simultaneously.

### Adding Multiple Marketplaces

```bash
# Add public marketplace
/plugin marketplace add randlee/synaptic-canvas

# Add company marketplace
/plugin marketplace add yourcompany/internal-marketplace

# Add team marketplace
/plugin marketplace add yourteam/team-tools

# List all marketplaces
/plugin marketplace list
```

### Registry Priority

When a package exists in multiple registries:

1. **Explicit registry** specified by user takes priority
2. **First-added** marketplace is default
3. **User can choose** during installation

```bash
# Install from specific marketplace
/plugin install package-name@synaptic-canvas

# Install from default marketplace
/plugin install package-name

# Claude Code will prompt if ambiguous
```

### Registry Configuration

```yaml
# ~/.claude/marketplaces.yaml (future)
registries:
  - name: synaptic-canvas
    owner: randlee
    repo: synaptic-canvas
    url: https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json
    priority: 1
    enabled: true

  - name: internal
    owner: yourcompany
    repo: internal-marketplace
    url: https://github.yourcompany.com/internal/marketplace/registries/nuget/registry.json
    priority: 2
    enabled: true
    auth:
      type: token
      token: ${INTERNAL_MARKETPLACE_TOKEN}
```

### Package Namespacing

To avoid conflicts, use namespaced package names:

```
company-package-name
team-specific-tool
sc-delay-tasks  (Synaptic Canvas prefix)
```

---

## Monitoring & Maintenance

### Registry Metrics

**Track these metrics:**

1. **Download counts** (if using analytics)
2. **Popular packages** (installation frequency)
3. **Error rates** (404s, timeouts)
4. **Geographic distribution** (CDN stats)
5. **Version adoption** (which versions are installed)

### Analytics Implementation

**Option 1: Server logs**
```bash
# Parse nginx access logs
tail -f /var/log/nginx/access.log | grep "registry.json"

# Count unique IPs
cat /var/log/nginx/access.log | grep "registry.json" | awk '{print $1}' | sort | uniq -c
```

**Option 2: CloudFlare Analytics**
```
Dashboard → Analytics → Traffic
- Page views: registries/nuget/registry.json
- Unique visitors
- Bandwidth usage
- Geographic distribution
```

**Option 3: Google Analytics**
```html
<!-- docs/index.html -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Health Checks

**Create a health check endpoint:**

```json
// docs/registries/nuget/health.json
{
  "status": "healthy",
  "timestamp": "2025-12-16T12:00:00Z",
  "registry_version": "2.0.0",
  "total_packages": 10,
  "last_updated": "2025-12-15T08:30:00Z"
}
```

**Monitor script:**
```bash
#!/bin/bash
# scripts/health-check.sh

URL="https://your-org.github.io/claude-marketplace/registries/nuget/health.json"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$RESPONSE" -eq 200 ]; then
    echo "✅ Marketplace is healthy"
    exit 0
else
    echo "❌ Marketplace is down (HTTP $RESPONSE)"
    exit 1
fi
```

**Set up monitoring:**
```yaml
# .github/workflows/health-check.yml
name: Marketplace Health Check

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check marketplace health
        run: |
          bash scripts/health-check.sh
```

### Maintenance Tasks

**Weekly:**
- [ ] Review package updates
- [ ] Check for broken links
- [ ] Validate JSON schema
- [ ] Review access logs

**Monthly:**
- [ ] Update marketplace version
- [ ] Audit package versions
- [ ] Review security advisories
- [ ] Update documentation
- [ ] Clean up deprecated packages

**Quarterly:**
- [ ] Performance review
- [ ] User feedback analysis
- [ ] Infrastructure optimization
- [ ] Disaster recovery test

### Automation Scripts

**Auto-update registry timestamps:**
```bash
#!/bin/bash
# scripts/update-registry-timestamp.sh

REGISTRY="docs/registries/nuget/registry.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

jq ".generated = \"$TIMESTAMP\"" "$REGISTRY" > "$REGISTRY.tmp"
mv "$REGISTRY.tmp" "$REGISTRY"

echo "Updated registry timestamp to $TIMESTAMP"
```

**Validate all packages:**
```bash
#!/bin/bash
# scripts/validate-packages.sh

for package in packages/*; do
    echo "Validating $package..."

    # Check required files
    [ -f "$package/manifest.yaml" ] || echo "❌ Missing manifest.yaml"
    [ -f "$package/README.md" ] || echo "❌ Missing README.md"
    [ -f "$package/CHANGELOG.md" ] || echo "❌ Missing CHANGELOG.md"

    # Validate manifest
    python3 -c "import yaml; yaml.safe_load(open('$package/manifest.yaml'))" || echo "❌ Invalid YAML"
done
```

---

## Troubleshooting

### Issue 1: Registry Not Found (404)

**Symptoms:**
```
Error: Marketplace not found
Failed to fetch: https://raw.githubusercontent.com/your-org/your-marketplace/main/docs/registries/nuget/registry.json
```

**Diagnosis:**
```bash
# Check if file exists
ls docs/registries/nuget/registry.json

# Check if committed
git ls-files docs/registries/nuget/registry.json

# Test URL
curl -I https://raw.githubusercontent.com/your-org/your-marketplace/main/docs/registries/nuget/registry.json
```

**Solutions:**

1. **File not committed:**
```bash
git add docs/registries/nuget/registry.json
git commit -m "Add registry"
git push
```

2. **Wrong branch:**
```bash
# If your default branch is 'master' not 'main'
git branch --show-current
# Update URL or rename branch
```

3. **Wrong path:**
```bash
# Verify exact path
find . -name "registry.json"
# Move to correct location if needed
mkdir -p docs/registries/nuget
mv registry.json docs/registries/nuget/
```

---

### Issue 2: Invalid JSON

**Symptoms:**
```
Error: Failed to parse registry
Invalid JSON at line 42
```

**Diagnosis:**
```bash
# Validate JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json

# Or with jq
jq empty docs/registries/nuget/registry.json
```

**Common errors:**
- Trailing comma in last array/object element
- Missing quotes around strings
- Unescaped special characters
- Wrong field types (string vs number)

**Solution:**
```bash
# Use a JSON formatter/validator
# Fix syntax errors
# Validate again before committing
```

---

### Issue 3: Package Not Installing

**Symptoms:**
```
Error: Failed to install package 'your-package'
Could not fetch artifacts
```

**Diagnosis:**
```bash
# Check package path in registry
cat docs/registries/nuget/registry.json | jq '.packages["your-package"].path'

# Verify package directory exists
ls packages/your-package/

# Check manifest.yaml
cat packages/your-package/manifest.yaml
```

**Solutions:**

1. **Path mismatch:**
```json
// registry.json
"path": "packages/your-package"  // Must match actual directory
```

2. **Missing manifest:**
```bash
# Create manifest.yaml
cat > packages/your-package/manifest.yaml <<EOF
name: your-package
version: 1.0.0
# ...
EOF
```

3. **Artifact paths wrong:**
```yaml
# manifest.yaml
artifacts:
  commands:
    - commands/cmd.md  # Must exist: packages/your-package/commands/cmd.md
```

---

### Issue 4: Rate Limiting

**Symptoms:**
```
Error: API rate limit exceeded
Retry after: 3600 seconds
```

**Solution:**

Switch from raw.githubusercontent.com to GitHub Pages:

```bash
# Enable GitHub Pages (see Hosting Options)
# Updates distribution URL to:
# https://your-org.github.io/your-marketplace/registries/nuget/registry.json

# Or use authenticated requests (future feature)
```

---

### Issue 5: CORS Issues (Self-Hosted)

**Symptoms:**
```
Error: CORS policy blocked request
```

**Solution:**

Add CORS headers to nginx:

```nginx
location /registries/ {
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
}
```

---

## Advanced Topics

### Custom Registry Formats

While Claude Code expects the standard format, you can maintain internal registries in different formats and convert them:

```python
# scripts/convert-registry.py
import yaml
import json

# Read internal YAML registry
with open('internal-registry.yaml') as f:
    internal = yaml.safe_load(f)

# Convert to standard format
standard = {
    "version": "2.0.0",
    "packages": {}
}

for pkg in internal['packages']:
    standard['packages'][pkg['name']] = {
        "name": pkg['name'],
        "version": pkg['version'],
        # ... map fields
    }

# Write standard registry.json
with open('docs/registries/nuget/registry.json', 'w') as f:
    json.dump(standard, f, indent=2)
```

### Automated Package Publishing

**GitHub Actions workflow:**

```yaml
# .github/workflows/publish-package.yml
name: Publish Package

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Update registry
        run: |
          python3 scripts/add-to-registry.py \
            --package ${{ github.event.repository.name }} \
            --version ${{ steps.version.outputs.VERSION }}

      - name: Commit registry update
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add docs/registries/nuget/registry.json
          git commit -m "chore: publish ${{ github.event.repository.name }} v${{ steps.version.outputs.VERSION }}"
          git push
```

### Marketplace Federation

Create a meta-marketplace that aggregates multiple registries:

```json
// docs/registries/nuget/federated-registry.json
{
  "version": "2.0.0",
  "type": "federated",
  "sources": [
    {
      "name": "synaptic-canvas",
      "url": "https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json",
      "priority": 1
    },
    {
      "name": "internal",
      "url": "https://internal.company.com/registries/nuget/registry.json",
      "priority": 2
    }
  ],
  "packages": {
    // Merged packages from all sources
  }
}
```

### Package Signing (Future Feature)

Sign packages with GPG for verification:

```bash
# Generate GPG key
gpg --full-generate-key

# Sign package
cd packages/your-package
tar czf ../your-package-1.0.0.tar.gz .
gpg --armor --detach-sign ../your-package-1.0.0.tar.gz

# Add signature to registry
{
  "packages": {
    "your-package": {
      "version": "1.0.0",
      "signature": {
        "type": "gpg",
        "key_id": "ABCD1234",
        "signature": "base64-encoded-signature"
      }
    }
  }
}
```

### Registry Mirroring

Mirror external registries for reliability:

```bash
#!/bin/bash
# scripts/mirror-registry.sh

SOURCE="https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json"
DEST="docs/mirrors/synaptic-canvas/registry.json"

# Fetch upstream registry
curl -s "$SOURCE" > "$DEST"

# Validate
jq empty "$DEST" && echo "✅ Mirror updated" || echo "❌ Invalid JSON"
```

---

## Next Steps

Now that you understand marketplace infrastructure:

1. **Create your registry** - Follow the step-by-step guide
2. **Add packages** - Start with a simple example package
3. **Test installation** - Verify everything works end-to-end
4. **Document usage** - Create clear instructions for users
5. **Gather feedback** - Learn what users need
6. **Iterate** - Improve based on real-world usage

### Resources

- **Synaptic Canvas Registry:** [registry.json](https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json)
- **Example Packages:** [packages/](../packages/)
- **Architecture Guidelines:** [claude-code-skills-agents-guidelines-0.4.md](./claude-code-skills-agents-guidelines-0.4.md)
- **Contributing Guide:** [CONTRIBUTING.md](../CONTRIBUTING.md)

### Community

- **Questions:** Open a discussion in your marketplace repo
- **Bug reports:** File an issue
- **Feature requests:** Start a discussion

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-16 | Initial comprehensive guide |

---

**Marketplace infrastructure is the foundation of the Claude Code ecosystem. Build thoughtfully, document thoroughly, and maintain diligently.**
