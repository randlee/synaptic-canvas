---
name: sc-manage
description: List, install, or uninstall Synaptic Canvas packages for Claude, Codex, Cursor, or Hermes.
---

# /sc-manage

This is the installer entry point. Many packages are not a `SKILL.md` copy:
their skills need the scripts (and optional `install.py` hooks) that
`sc-manage` installs through `tools/sc-install.py`.

Resolve `../scripts/sc_manage_dispatch.py` relative to this command file and
run it with the user's flags unchanged. Do not delegate to Claude Task agents
such as `sc-package-install`; those files are not part of a Cursor install.

```bash
python3 <resolved-dispatch> --list
python3 <resolved-dispatch> --install <package> --local|--project|--global|--user [--claude] [--codex] [--cursor] [--hermes]
python3 <resolved-dispatch> --uninstall <package> --local|--project|--global|--user [--claude] [--codex] [--cursor] [--hermes]
python3 <resolved-dispatch> --docs <package>
```

No target flags means Claude only. Unknown or conflicting flags are errors.
Present the dispatcher's JSON as a table. Read
`../skills/managing-sc-packages/SKILL.md` for policy details.
