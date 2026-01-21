# Frontmatter JSON Schemas

This directory contains JSON Schema files for validating Claude Code artifact frontmatter.

## Files

| Schema | Purpose |
|--------|---------|
| `command-frontmatter.schema.json` | Validates command .md frontmatter |
| `skill-frontmatter.schema.json` | Validates skill SKILL.md frontmatter |
| `agent-frontmatter.schema.json` | Validates agent .md frontmatter |

## Usage

These schemas can be used with any JSON Schema validator:

```python
import jsonschema
import yaml

with open('docs/schemas/command-frontmatter.schema.json') as f:
    schema = json.load(f)

# Validate frontmatter
jsonschema.validate(frontmatter_dict, schema)
```

## IDE Integration

Many IDEs support JSON Schema validation for YAML files. Configure your IDE to use these schemas for `.md` files with YAML frontmatter.
