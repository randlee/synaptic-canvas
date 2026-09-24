# sc-install

`sc-install` (implementation: `install.py`, invoked via `tools/sc-install.py` or
`python3 -m sc_cli.sc_install`) installs and uninstalls Synaptic Canvas
packages from `packages/*/` into a `.claude` and/or `.codex` directory. This
document is the normative reference for what a package (`packages/<name>/`)
must provide, and what `sc-install` guarantees in return.

## CLI

```
sc-install list [--registry NAME] [--all-registries] [--search QUERY]
sc-install info <package> [--registry NAME]
sc-install search <query> [--registry NAME]
sc-install install <package> --dest <path/to/.claude> [--force] [--no-expand] [--set K=V ...]
sc-install install <package> --global [--claude|--codex] [--force] [--no-expand] [--set K=V ...]
sc-install install <package> --local  [--claude|--codex] [--force] [--no-expand] [--set K=V ...]
sc-install install <package> --user   [--claude|--codex] [--force] [--no-expand] [--set K=V ...]
sc-install install <package> --project [--claude|--codex] [--force] [--no-expand] [--set K=V ...]
sc-install uninstall <package> --dest <path/to/.claude> [--set K=V ...]
sc-install registry add <name> <url> [--path <path>]
sc-install registry list
sc-install registry remove <name>
```

- `--global`/`--user` resolve to `~/`; `--local`/`--project` resolve to `./`.
  Exactly one of `--global`/`--local`/`--user`/`--project`/`--dest` is
  required for `install`.
- `--claude`/`--codex` select which target(s) get installed under the chosen
  scope: symmetric flags, either alone means only that target, neither means
  both `.claude` and `.codex` are installed. An explicit `--dest` is always
  `.claude`-only (there is no sibling `.codex` to mirror into).
- `--force` overwrites existing files instead of skipping them.
- `--no-expand` disables the legacy `{{TOKEN}}` expansion (see below).
- `--set KEY=VALUE` is repeatable and forwards arbitrary key/value pairs to a
  package's `install.py` hooks (see below); `sc-install` itself never
  interprets these values, only a package's own hook does.

## `manifest.yaml`

Every package must have `packages/<name>/manifest.yaml`:

```yaml
name: sc-example                # defaults to the directory name if omitted
version: 0.1.0
description: >
  One or more sentences describing the package.
author: your-name
license: MIT
tags: [tag-one, tag-two]

# Files to install, relative to the package root. Every key is optional;
# omit a category entirely if the package ships none of it.
artifacts:
  commands:
    - commands/sc-example.md
  skills:
    - skills/sc-example/SKILL.md
  agents:
    - agents/sc-example-do-thing.md
  scripts:
    - scripts/example_helper.py     # chmod +x'd automatically on install
  assets:
    - assets/example-template.txt
  plugin:
    - plugin.json                   # or any other manifest-adjacent artifact

# Optional installation policy
install:
  scope: local-only   # or omit; local-only packages refuse --global/--user

# Optional install-time flags a package documents for its own consumers
# (informational only - sc-install does not read or enforce this section;
# a package's install.py reads its own required values out of options["args"]
# instead, see below)
options:
  some-flag:
    type: boolean
    default: false
    description: What this flag changes about behavior at runtime.

# Legacy token-expansion variable declaration (superseded by install.py +
# .j2 rendering for anything new - see "Repo-specific rendering" below).
# Only relevant if a shipped artifact still contains a literal {{REPO_NAME}}
# token and --no-expand is not passed.
variables:
  REPO_NAME:
    auto: git-repo-basename
```

Codex installs (`--codex`) only ever receive `skills`, `scripts`, and
`assets` - Codex has no equivalent of commands, agents, or
`agents/registry.yaml`.

### Registry (`agents/registry.yaml`)

For non-Codex targets, every installed file under `agents/` or `skills/` is
recorded in `<dest>/agents/registry.yaml` after the copy step. An
`agents/*.md` file's frontmatter `version` (if present) must match the
package's `manifest.yaml` version, or the install fails; this catches an
artifact that was hand-edited without bumping its own version.

## Repo-specific rendering: `.local.j2` and `install.py`

A package that needs to bake repo-specific values (like the consuming repo's
name) into an installed artifact has two options:

1. **`.local.j2` sibling files** (existing mechanism, any artifact category):
   ship `<path>.local.j2` next to `<path>` and it is rendered via
   `sc-compose` and used *instead of* the plain `<path>` for any install that
   isn't `--global`/`--user` and isn't `--codex`. `sc-compose` is
   auto-installed on first use. This is a generic, no-code mechanism - good
   for simple single-variable substitution.
2. **`install.py` hooks** (below): full control over what happens before and
   after the copy step, for anything `.local.j2` doesn't cover (multiple
   templates, conditional logic, non-trivial failure messages, cleanup).

Both mechanisms may be used by the same package; they don't interact with
each other.

## `install.py` hooks

A package root may optionally contain `packages/<name>/install.py` defining
any of three module-level functions. None are required; a package with no
`install.py`, or one missing some of the functions, behaves as if the absent
ones were no-ops.

```python
def prepare(source_path: str, destination_path: str, options: dict) -> dict:
    """Runs once per install target, immediately before the artifact copy
    step for that target. Must not write to destination_path - nothing has
    been copied there yet for this install run."""

def complete(source_path: str, destination_path: str, options: dict) -> dict:
    """Runs once per install target, immediately after the artifact copy
    step and registry update finish. This is where repo-specific rendering,
    and any conditional delete-if-present cleanup of prior-version output
    (see INVENTORY below), belongs."""

def cleanup(source_path: str, destination_path: str, options: dict) -> dict:
    """Runs once per target during `sc-install uninstall`, after the
    standard manifest-artifact removal. Deletes anything prepare()/
    complete() created that isn't itself a plain manifest artifact (so the
    standard removal step wouldn't already have deleted it)."""
```

- `source_path` is the package's root directory (`packages/<name>`).
- `destination_path` is the resolved directory for *this* install target
  (e.g. `~/.claude`, `./.codex`, or an explicit `--dest`) - the same
  directory every prior install/uninstall of this package used, so a hook
  can inspect what's already on disk there.
- `options` is always:
  ```python
  {
      "global": bool, "local": bool, "user": bool, "project": bool,
      "codex": bool,       # True iff this call is for the .codex target
      "force": bool, "expand": bool,
      "args": {"KEY": "VALUE", ...},   # from repeatable --set KEY=VALUE
  }
  ```
  `args` is empty unless the caller passed `--set`. A package that needs
  information `sc-install` has no generic way to know (e.g. a target
  environment name) reads it from `options["args"]` and fails with a message
  telling the caller which `--set` to add if it's missing - see the result
  contract below.
- Both `.claude` and `.codex` targets get their own full `prepare()` → copy →
  `complete()` cycle when both are installed (`options["codex"]` tells the
  hook which one it's in).

### Result contract

Every hook function must return one of exactly two shapes:

```python
{"result": "success"}
{"result": "fail", "message": "<fail reason, instructions to fix>"}
```

`message` must combine *why it failed* and *what to do about it* in one
string - there is no separate reason/suggestion field. Anything else -
raising an exception, returning a non-dict, returning a dict without a
`"result"` key, or reporting `"fail"` without a `message` - is itself an
`sc-install` error (the hook is buggy, not the caller's input), and
`sc-install` reports a descriptive error and aborts that target with a
non-zero exit code. A failing hook stops the install/uninstall for that
target only; other targets already processed are not rolled back.

### Requirements for `install.py` authors

These are enforced by convention and (for the INVENTORY rule) by CI, not by
`sc-install` itself - a non-compliant hook can still be written, but every
hook shipped in this repo is expected to meet these:

1. **Idempotent.** Running `prepare()`/`complete()`/`cleanup()` twice against
   the same `destination_path` (re-running install, e.g. with `--force`;
   running uninstall twice) must produce the same on-disk result as running
   it once - never accumulate duplicate or corrupted state.
2. **Self-cleaning across versions, via a cumulative `INVENTORY`.** A
   package with an `install.py` should keep a module-level `INVENTORY` list
   naming every destination-relative path it has ever produced across all
   released versions. Entries are only ever *added*, never removed, even
   once a path stops being current. A CI validator checks each `INVENTORY`
   entry against the package's current source tree: an entry whose source
   file no longer exists (this version dropped it) fails CI unless
   `complete()` contains a matching conditional delete for that path.
   `prepare()` must never contain such a delete (see rule 1: nothing should
   touch `destination_path` before the copy step). Put a comment directly
   above `INVENTORY` telling the next editor exactly this, so removing an
   entry without adding the corresponding cleanup line is caught early
   rather than at CI:

   ```python
   # Every path this package has ever installed, across all versions.
   # Only append - never remove an entry. If a version stops shipping a
   # path listed here, add a matching `if (Path(destination_path) / path
   # ).exists(): ...unlink()` line to complete() before removing that
   # artifact from manifest.yaml, or CI will fail.
   INVENTORY = [
       "commands/sc-example.md",
   ]
   ```

### Example: `packages/sc-git-worktree/*.local.j2`

`sc-git-worktree` is the package this generic mechanism was built for: its
manifest docs describe a `worktree_base` default of `../<repo-name>-worktrees`,
and that repo name should be baked in for a local install rather than left as
a runtime-derivation instruction. It ships three `.local.j2` siblings -
`commands/sc-git-worktree.md.local.j2`, `skills/sc-git-worktree/SKILL.md.local.j2`,
and `agents/sc-git-worktree-update.md.local.j2` - each identical to its plain
`.md` counterpart except that the `basename $(git rev-parse --show-toplevel)`
runtime-derivation sentence is replaced with the literal `{{ REPO_NAME }}`
value. For `--local`/`--project` installs where `repo_name` is non-empty,
`install_one()` renders the `.local.j2` and writes that instead of the plain
file; for `--global`/`--user` installs, `--codex` targets, or any install
where no repo is detected, the plain `.md` (with the runtime-derivation
instructions) is copied unchanged. `sc-git-worktree` has no `install.py` -
this substitution needs nothing beyond the generic mechanism.

## Uninstall

`sc-install uninstall <package> --dest <path>` removes every path in the
package's current `manifest.yaml` artifacts from `<path>`, then runs the
package's `cleanup()` hook (if any) with the same `options` shape as
install (scope flags are all `False` since `uninstall` doesn't reconstruct
them; `args` still comes from `--set`).
