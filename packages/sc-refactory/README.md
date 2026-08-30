# sc-refactory

`sc-refactory` designs and installs a rule-driven refactoring toolkit. It
combines approved-fix lookup, bounded development waves, and independent QA
gates so large migrations remain traceable to explicit policy.

## Install

```bash
python3 tools/sc-install.py install sc-refactory --dest .claude
```

Run the installed `sc-refactory-install` command to create the local
`.refactor/` policy workspace and seed its templates.

## Components

- `refactory-design` and `refactory-install` establish the policy system.
- `refactor-lookup` and `refactor-write` retrieve and curate approved fixes.
- `refactor-orchestrate` coordinates development waves with
  `refactor-quality-manager` as the independent QA teammate.

## Security

Use this package only in trusted repositories and treat `.refactor/` rules as
the source of truth for authorized changes. Review proposed rules and generated
edits before commit, use least-privilege credentials for any repository access,
and never include secrets in prompts, rule documents, logs, or agent messages.
