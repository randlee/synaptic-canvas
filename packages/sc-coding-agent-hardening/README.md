# sc-coding-agent-hardening

Marketplace package for hardening coding, QA, and orchestration agent prompts.

## Installed Skill

- `coding-agent-hardening`

## What It Does

- removes permissive prompt language that lets fixable issues survive
- tightens escalation so agents only stop for real decisions or boundaries
- requires validation-backed completion after code changes

## Included References

- `./skills/coding-agent-hardening/references/hardening-policy.md`
- `./skills/coding-agent-hardening/references/prompt-rewrite-patterns.md`
- `./skills/coding-agent-hardening/references/agent-category-guidance.md`
- `./skills/coding-agent-hardening/references/repo-target-map.md`

`repo-target-map.md` is optional and only applies when hardening agents inside the Synaptic Canvas repository itself.
