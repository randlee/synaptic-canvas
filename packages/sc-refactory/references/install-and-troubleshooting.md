# Refactor Install And Troubleshooting

Use this guide when a refactor skill pre-flight fails.

## Claude Repair Contract

The goal is for the Claude session to repair this environment through the
skill's documented workflow whenever the repair path is local and scripted.

That means:

- run pre-flight,
- if it fails, read this guide,
- attempt the scripted local repair steps below,
- rerun pre-flight,
- only stop and ask for help if the scripted repair path does not restore the
  environment.

## Expected Layout

- rules: `.refactor/rules/`
- docs: `.refactor/docs/`
- runtime DB: `.refactor/db/`
- startup/rebuild scripts: `.refactor/scripts/`
- temp files and logs: `.refactor/temp/`

## Supported Runtime

Install `oxigraph` from crates.io, not from Homebrew.

This workflow was tested with:

```text
oxigraph 0.5.7
```

## Pre-flight Command

Run:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-lookup
```

or:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/preflight.py" --skill refactor-write
```

Success output:

```text
oxigraph v 0.5.7 checks pass
```

If pre-flight fails, do not invoke the background agent yet.

Failure output:

```text
tools are not installed or working to use this skill. please read ./.refactor/docs/install-and-troubleshooting.md
```

## Scripted Repair

After a pre-flight failure, Claude should attempt the scripted repair path
before stopping:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-lookup
```

or:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-write
```

This repair path rebuilds `.refactor/db/` through `session_start.py` and then
reruns the matching pre-flight check.

## Installation

Install the latest `oxigraph-cli` from crates.io:

```bash
cargo install oxigraph-cli
```

If an older `oxigraph` is already shadowing the cargo install, remove or unlink
it so `oxigraph` resolves to `~/.cargo/bin/oxigraph`.

Verify:

```bash
oxigraph --version
```

## Rebuild Runtime DB

If `.refactor/db/` is missing or unreadable, rebuild it through the startup
script:

```bash
python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/session_start.py" --mode startup >/tmp/refactor-startup.out
```

This rebuilds `.refactor/db/` from committed turtles in `.refactor/rules/`.

This is the first repair step Claude should attempt when pre-flight fails and
`oxigraph` itself is installed.

## Direct Health Checks

Check that the DB can be queried:

```bash
repo_root="$(git rev-parse --show-toplevel)"

oxigraph query \
  --location "$repo_root/.refactor/db" \
  --query 'PREFIX ref: <https://synaptic.canvas/refactor/> SELECT ?s WHERE { ?s ?p ?o } LIMIT 1' \
  --results-format json
```

## Troubleshooting

If `oxigraph --version` fails:

- install `oxigraph`
- ensure it is on `PATH`

If `.refactor/db/` is missing:

- run `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/session_start.py" --mode startup`

If `.refactor/db/` exists but query fails:

- run `python3 "$(git rev-parse --show-toplevel)/.refactor/scripts/repair.py" --skill refactor-lookup`
- rerun the pre-flight command

If pre-flight still fails after rebuilding the DB:

- surface a concise environment error
- include the exact failing command and output
- do not invoke the background refactor agent yet

If startup succeeds but the background lookup agent still reports
`EXECUTION.GRAPH_UNAVAILABLE`:

- verify the agent is running in this repo
- verify it is querying `.refactor/db`
- treat that as an agent cwd/path problem, not a rule-authoring problem

## Source Of Truth

The committed source of truth is:

- `.refactor/rules/*.ttl`
- `.refactor/docs/*.md`

Do not commit:

- `.refactor/db/`
- `.refactor/temp/`
