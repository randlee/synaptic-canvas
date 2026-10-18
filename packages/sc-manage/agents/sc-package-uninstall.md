---
name: sc-package-uninstall
version: 0.14.2
description: Uninstall a Synaptic Canvas package from selected agent targets according to package policy.
model: sonnet
color: blue
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 scripts/validate_sc_manage_hook.py"
---

# sc-package-uninstall

## Inputs
- `package`: required package name
- `scope`: required `local` | `project` | `global` | `user`
- `targets`: optional nonempty list of `claude`, `codex`, `cursor`, `hermes`;
  defaults to `["claude"]`. Unselected targets must remain untouched.
- `sc_repo_path`: absolute path to the Synaptic Canvas repo. Default: `SC_REPO_PATH` or repo root.
- `global_claude_dir`: absolute path to the global `.claude`. Default: `~/.claude` (or `GLOBAL_CLAUDE_DIR`).
- `user_claude_dir`: absolute path to the user `.claude`. Default: `~/.claude` (or `USER_CLAUDE_DIR`).

## Execution
1. Run: `python3 scripts/sc_manage_uninstall.py` with JSON stdin.
2. The script validates package, scope, and install policy.
3. The script resolves destination and runs `tools/sc-install.py`.
4. Return JSON summary.

## Output

````markdown
```json
{
  "success": true,
  "data": { "package": "sc-delay-tasks", "scope": "global", "dest": "/home/user/.claude" },
  "error": null
}
```
````

## Errors

````markdown
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SCOPE_NOT_ALLOWED",
    "message": "Package is not allowed in the requested scope",
    "recoverable": false,
    "suggested_action": "choose a permitted scope"
  }
}
```
````

## Constraints
- Uninstall only package-owned artifacts in the selected target destinations.
  Non-Claude targets use their portable artifact subset (plus sc-manage's
  Cursor `/sc-manage` command); leave peer targets and unrelated files
  untouched. Per-target roots accept `global_<target>_dir` and
  `user_<target>_dir` overrides. Report partial completion on failure.
- Return ONLY fenced JSON.
