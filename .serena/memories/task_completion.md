# Task Completion Checklist

- Run `pytest` to ensure CLI helpers still pass tests.
- If working on packages, ensure manifest.yaml fields are updated and artifacts paths correct.
- For agents, run `python3 scripts/validate-agents.py` when registry/frontmatter involved (requires yq and .claude/agents/registry.yaml present).
- Document new commands/skills/agents and ensure command help text/options are clear.
- Keep layered architecture intact: commands stay thin, skills orchestrate, agents do bounded work with structured JSON outputs.
