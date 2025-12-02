# Style and Conventions

- Architecture philosophy (from CONTRIBUTING): layered design (commands → skills → agents), explicit contracts with structured data, safety-first with explicit approvals/validation, minimal context pollution, installation simplicity.
- Artifacts: commands define user-facing slash commands with help/options; skills orchestrate workflows and reference agents; agents do bounded work and return structured JSON outputs; scripts handle heavy lifting and must be executable.
- Manifests: manifest.yaml required with metadata and artifacts lists; optional tags, variables (for token substitution), options, and requires fields. Package tiers: Tier0 direct copy, Tier1 token substitution (e.g., {{REPO_NAME}}), Tier2 adds runtime deps.
- Code style: Python utilities are straightforward/imperative; no stated formatter; tests use pytest. Keep contracts explicit, avoid hidden state, and provide clear errors.
- Safety: avoid destructive operations without explicit approval; validate inputs; keep command definitions minimal and delegate to skills/agents.
