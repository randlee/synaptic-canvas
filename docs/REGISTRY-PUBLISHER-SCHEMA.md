# Registry Publisher Schema

## Overview

This document defines the schema for publisher information in the Synaptic Canvas package registry. The publisher schema provides structured, validated information about package publishers, their verification status, and their published packages.

## Purpose

The publisher schema serves several critical functions:

1. **Identity Management**: Establishes and validates publisher identities
2. **Verification Tracking**: Documents verification level and method
3. **Package Attribution**: Links packages to verified publishers
4. **Trust Signals**: Provides data for trust badges and indicators
5. **Programmatic Access**: Enables tools to query publisher information

## Schema Location

Publisher information is stored in the registry at:

```
docs/registries/nuget/registry.json
```

Under the `publishers` object:

```json
{
  "packages": { ... },
  "metadata": { ... },
  "versionCompatibility": { ... },
  "publishers": {
    "publisher-handle": { ... }
  }
}
```

## Schema Structure

### Top-Level Publishers Object

```json
{
  "publishers": {
    "publisher-handle-1": { PublisherProfile },
    "publisher-handle-2": { PublisherProfile },
    ...
  }
}
```

**Key**: Publisher's GitHub handle (string)
**Value**: PublisherProfile object

### PublisherProfile Object

Complete schema for a single publisher:

```json
{
  "name": "string (required)",
  "github_handle": "string (required)",
  "github_url": "string (required, URL)",
  "verification": {
    "level": "integer (required, 0-3)",
    "method": "string (required)",
    "verified_date": "string (required, ISO 8601)"
  },
  "packages": ["string (required, array)"],
  "total_packages": "integer (required)"
}
```

## Field Definitions

### name

**Type**: String
**Required**: Yes
**Description**: Publisher's full name or organization name

**Validation Rules**:
- Length: 2-100 characters
- Must not be empty or whitespace only
- Should match GitHub profile name when possible
- Special characters allowed: hyphens, spaces, periods

**Examples**:
```json
"name": "Randall Lee"
"name": "Acme Corporation"
"name": "John Smith-Johnson"
```

**Usage**:
- Displayed in package attribution
- Shown in publisher listings
- Used in verification badges
- Searchable in marketplace

### github_handle

**Type**: String
**Required**: Yes
**Description**: Publisher's GitHub username

**Validation Rules**:
- Length: 1-39 characters (GitHub limit)
- Must match pattern: `^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$`
- Must be a valid, existing GitHub username
- Cannot contain consecutive hyphens
- Cannot start or end with hyphen

**Examples**:
```json
"github_handle": "randlee"
"github_handle": "acme-corp"
"github_handle": "user123"
```

**Usage**:
- Primary identifier for publisher
- Used to construct github_url
- Key in publishers object
- Verification validation

**Common Errors**:
- Using display name instead of handle
- Including @ symbol
- Capitalization mismatches (GitHub is case-insensitive but registry should match profile)

### github_url

**Type**: String (URL)
**Required**: Yes
**Description**: Full URL to publisher's GitHub profile

**Validation Rules**:
- Must be valid URL
- Must start with `https://github.com/`
- Must match pattern: `https://github.com/{github_handle}`
- Handle in URL must match `github_handle` field
- URL must return HTTP 200 (profile exists and is public)

**Examples**:
```json
"github_url": "https://github.com/randlee"
"github_url": "https://github.com/acme-corp"
```

**Usage**:
- Linked from verification badges
- Displayed in publisher profiles
- Used for profile verification
- Enables user research on publisher

**Validation Process**:
1. Parse URL to extract handle
2. Compare extracted handle to `github_handle` field
3. HTTP GET request to verify profile exists
4. Confirm profile is publicly accessible

### verification

**Type**: Object
**Required**: Yes
**Description**: Publisher verification information

**Schema**:
```json
{
  "level": integer,
  "method": string,
  "verified_date": string
}
```

#### verification.level

**Type**: Integer
**Required**: Yes
**Description**: Verification tier (0-3)

**Valid Values**:
- `0`: Unverified (default)
- `1`: GitHub organization verified
- `2`: Organization + security audit (future)
- `3`: Extended security features (future)

**Validation Rules**:
- Must be integer 0, 1, 2, or 3
- Cannot be null or undefined
- Must match publisher's actual verification status

**Examples**:
```json
"level": 1
```

**Semantics**:
- `0`: No verification performed
- `1`: GitHub identity confirmed, basic security standards met
- `2`: Level 1 + independent security audit passed
- `3`: Level 2 + enterprise security features

#### verification.method

**Type**: String
**Required**: Yes
**Description**: Method used to verify publisher identity

**Valid Values** (Current):
- `"github_organization"`: GitHub account/org ownership verified

**Valid Values** (Future):
- `"security_audit"`: Third-party security audit
- `"legal_entity"`: Legal business entity verification
- `"code_signing"`: Cryptographic identity verification

**Validation Rules**:
- Must be non-empty string
- Must be from valid values list
- Must correspond to verification level:
  - Level 0: method not applicable (omit verification object)
  - Level 1: `"github_organization"`
  - Level 2: `"security_audit"`
  - Level 3: `"legal_entity"` or `"code_signing"`

**Examples**:
```json
"method": "github_organization"
```

**Usage**:
- Documents verification approach
- Enables verification audits
- Clarifies trust basis
- Supports multiple verification paths

#### verification.verified_date

**Type**: String (ISO 8601 timestamp)
**Required**: Yes
**Description**: Date and time when verification was completed

**Format**: ISO 8601 combined date-time with timezone

**Validation Rules**:
- Must be valid ISO 8601 timestamp
- Must include timezone (Z for UTC recommended)
- Cannot be in the future
- Should not be more than 2 years old (triggers re-verification)

**Examples**:
```json
"verified_date": "2025-12-04T00:00:00Z"
"verified_date": "2025-12-04T15:30:00-08:00"
```

**Usage**:
- Shows verification recency
- Triggers re-verification when old
- Displayed in publisher profiles
- Audit trail for verification

**Recommended Practice**:
- Use UTC timezone (Z suffix)
- Include time even if only date is significant
- Update on re-verification

### packages

**Type**: Array of Strings
**Required**: Yes
**Description**: List of package names published by this publisher

**Validation Rules**:
- Must be array (can be empty for new publishers)
- Each element must be string
- Each element must match a package name in `packages` object
- No duplicate entries
- Package names must follow package naming rules
- Array should be sorted alphabetically (recommended)

**Examples**:
```json
"packages": [
  "delay-tasks",
  "git-worktree",
  "sc-manage",
  "sc-repomix-nuget"
]
```

**Usage**:
- Links publisher to their packages
- Enables "all packages by publisher" queries
- Validates package ownership
- Displays in publisher profiles

**Validation Process**:
1. For each package in array:
   - Verify package exists in registry `packages` object
   - Confirm package metadata matches publisher
2. Ensure all packages in registry with this publisher are listed

**Maintenance**:
- Add package name when new package published
- Remove package name if package delisted
- Keep synchronized with `packages` object

### total_packages

**Type**: Integer
**Required**: Yes
**Description**: Count of published packages

**Validation Rules**:
- Must be non-negative integer
- Must equal length of `packages` array
- Must match count of packages in registry with this publisher

**Examples**:
```json
"total_packages": 4
```

**Usage**:
- Quick metric of publisher activity
- Displayed in publisher profiles
- Used in search result sorting (future)
- Reputation scoring (future)

**Derivation**:
```javascript
total_packages = packages.length
```

**Common Errors**:
- Forgetting to update when adding/removing packages
- Manual count that doesn't match array length
- Including unpublished or pending packages

## Complete Example

Here's a complete, valid publisher profile:

```json
{
  "publishers": {
    "randlee": {
      "name": "Randall Lee",
      "github_handle": "randlee",
      "github_url": "https://github.com/randlee",
      "verification": {
        "level": 1,
        "method": "github_organization",
        "verified_date": "2025-12-04T00:00:00Z"
      },
      "packages": [
        "delay-tasks",
        "git-worktree",
        "sc-repomix-nuget",
        "sc-manage"
      ],
      "total_packages": 4
    }
  }
}
```

## Validation Rules Summary

### Required Fields

All fields are required:
- `name`
- `github_handle`
- `github_url`
- `verification` (object with `level`, `method`, `verified_date`)
- `packages`
- `total_packages`

### Cross-Field Validation

1. **Handle/URL Consistency**:
   ```
   github_url must equal "https://github.com/" + github_handle
   ```

2. **Package Count Consistency**:
   ```
   total_packages must equal packages.length
   ```

3. **Package Existence**:
   ```
   For each package_name in packages:
     package_name must exist in registry.packages
   ```

4. **Verification Level/Method**:
   ```
   level 1 requires method "github_organization"
   level 2 requires method "security_audit"
   level 3 requires method "legal_entity" or "code_signing"
   ```

### Data Type Validation

```javascript
{
  name: typeof string && length > 0,
  github_handle: typeof string && /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(),
  github_url: typeof string && isValidURL() && startsWith("https://github.com/"),
  verification: {
    level: typeof number && 0 <= level <= 3,
    method: typeof string && validMethods.includes(method),
    verified_date: typeof string && isValidISO8601()
  },
  packages: Array.isArray() && packages.every(p => typeof p === "string"),
  total_packages: typeof number && total_packages >= 0
}
```

## Schema Versioning

The publisher schema is versioned independently from the package schema:

**Current Version**: 1.0.0

**Version History**:
- 1.0.0 (2025-12-04): Initial publisher schema

**Future Enhancements** (2.0.0):
- Contact email field
- Organization type field
- Website URL field
- Social media links
- Support tiers
- Statistics (downloads, stars, etc.)

## Validation Tools

### Manual Validation

Check your publisher entry:

```bash
# Validate JSON syntax
cat docs/registries/nuget/registry.json | jq '.publishers'

# Check specific publisher
cat docs/registries/nuget/registry.json | jq '.publishers.randlee'

# Verify package count matches
cat docs/registries/nuget/registry.json | jq '.publishers.randlee.packages | length'
```

### Automated Validation

Future: Schema validation script will check:

```bash
# Validate all publishers
python3 scripts/validate-registry.py --publishers

# Validate specific publisher
python3 scripts/validate-registry.py --publisher randlee

# Full registry validation (packages + publishers)
python3 scripts/validate-registry.py --all
```

## Usage Examples

### Querying Publisher Information

**Get All Publishers**:
```bash
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json \
  | jq '.publishers'
```

**Get Specific Publisher**:
```bash
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json \
  | jq '.publishers.randlee'
```

**Get Publisher's Packages**:
```bash
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json \
  | jq '.publishers.randlee.packages[]'
```

**Check Verification Level**:
```bash
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json \
  | jq '.publishers.randlee.verification.level'
```

### Programmatic Access

**JavaScript/TypeScript**:
```javascript
const registry = await fetch(
  'https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json'
).then(r => r.json());

const publisher = registry.publishers['randlee'];
const isVerified = publisher.verification.level >= 1;
const packages = publisher.packages;
```

**Python**:
```python
import requests

url = 'https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json'
registry = requests.get(url).json()

publisher = registry['publishers']['randlee']
is_verified = publisher['verification']['level'] >= 1
packages = publisher['packages']
```

## Adding a New Publisher

To add a new publisher to the registry:

1. **Verify Prerequisites**:
   - GitHub account exists and is public
   - Publisher meets verification requirements
   - All packages are ready for publication

2. **Determine Key**:
   - Use GitHub handle as key
   - Ensure no conflicts with existing publishers

3. **Gather Information**:
   - Publisher's full name
   - GitHub handle and URL
   - List of package names
   - Verification level achieved

4. **Create Entry**:
   ```json
   {
     "publishers": {
       "new-publisher": {
         "name": "Publisher Name",
         "github_handle": "new-publisher",
         "github_url": "https://github.com/new-publisher",
         "verification": {
           "level": 1,
           "method": "github_organization",
           "verified_date": "2025-12-04T00:00:00Z"
         },
         "packages": [
           "package-1",
           "package-2"
         ],
         "total_packages": 2
       }
     }
   }
   ```

5. **Validate Entry**:
   - Check JSON syntax
   - Verify all required fields present
   - Confirm packages exist in registry
   - Validate URLs are accessible

6. **Update Registry**:
   - Add entry to registry.json
   - Commit and push changes
   - Verify in deployed registry

## Best Practices

### For Registry Maintainers

1. **Validate Before Merging**:
   - Check JSON syntax
   - Verify GitHub profile exists
   - Confirm package ownership
   - Test badge URLs

2. **Maintain Consistency**:
   - Use consistent date formats (ISO 8601)
   - Keep packages array sorted
   - Match naming conventions
   - Update total_packages when packages change

3. **Document Changes**:
   - Log verification dates accurately
   - Document verification process
   - Track re-verification schedule
   - Maintain audit trail

### For Tool Developers

1. **Defensive Parsing**:
   - Handle missing fields gracefully
   - Validate data types
   - Provide fallbacks for optional future fields
   - Don't assume publisher existence

2. **Cache Appropriately**:
   - Publisher info changes infrequently
   - Cache for reasonable duration
   - Implement cache invalidation
   - Handle stale data gracefully

3. **Error Handling**:
   - Graceful degradation if registry unavailable
   - Clear error messages for validation failures
   - Don't break on unknown verification methods
   - Support schema evolution

## Migration and Updates

### Updating Publisher Information

When publisher information changes:

1. **Name Changes**:
   - Update `name` field
   - Document change in commit message
   - Notify affected package users

2. **Handle Changes**:
   - Create new publisher entry with new handle
   - Migrate packages to new entry
   - Mark old entry as deprecated
   - Maintain redirect/note for period of time

3. **Adding Packages**:
   - Add package name to `packages` array
   - Increment `total_packages`
   - Ensure alphabetical order
   - Verify package exists in registry

4. **Verification Level Changes**:
   - Update `level` field
   - Update `method` if changed
   - Update `verified_date` to current date
   - Document upgrade in verification docs

### Schema Evolution

When schema needs enhancement:

1. **Backward Compatibility**:
   - Add new fields as optional
   - Provide defaults for missing fields
   - Document migration path
   - Maintain old field support during transition

2. **Version Bump**:
   - Increment schema version
   - Document changes in this file
   - Update validation tools
   - Notify tool developers

## Troubleshooting

### Common Issues

**Issue**: Package count doesn't match array length
```
Error: total_packages (3) doesn't match packages array length (4)
Solution: Update total_packages to match packages.length
```

**Issue**: GitHub URL doesn't match handle
```
Error: github_url "https://github.com/randlee" doesn't match handle "rand-lee"
Solution: Ensure exact match between URL and github_handle
```

**Issue**: Package not found in registry
```
Error: Package "unknown-pkg" in publisher.packages not found in registry.packages
Solution: Either add package to registry or remove from publisher.packages
```

**Issue**: Invalid ISO 8601 date
```
Error: verified_date "2025-12-04" missing time and timezone
Solution: Use format "2025-12-04T00:00:00Z"
```

## References

- [Publisher Verification](PUBLISHER-VERIFICATION.md) - Complete verification documentation
- [Security Policy](../SECURITY.md) - Security practices and policies
- [Package Registry Schema](../registries/nuget/registry-schema.md) - Package schema documentation

## Questions and Support

For questions about the publisher schema:

1. Review this documentation thoroughly
2. Check existing publisher entries for examples
3. Open a GitHub Issue with specific questions
4. Reference this document in discussions
