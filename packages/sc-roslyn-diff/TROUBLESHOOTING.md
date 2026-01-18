# sc-roslyn-diff Troubleshooting

## dotnet tool install/update fails

- Ensure `dotnet` 10+ is installed and on PATH.
- If `dotnet tool update -g roslyn-diff` fails, the agent will fall back to `dotnet tool install -g roslyn-diff`.

## Azure DevOps PR resolution fails

- Ensure `az` CLI is installed and authenticated:
  - `az login`
  - `az devops configure --defaults organization=<org> project=<project>`
- If org/project cannot be inferred from the repo, they are cached in `.sc/roslyn-diff/settings.json`.

## Large batch stopped without running

- The agent enforces a default max pair cap to avoid context overload.
- Re-run with `--allow-large` or reduce the scope.

## HTML report not opening

- `--html` writes reports; opening depends on OS/browser availability.
- If the system blocks auto-open, use the file path returned by the agent.

## Non-.NET file behavior

- The default mode is `auto`, which falls back to line diffs for non-.NET files.
- Use `--line` to force line diff for all files.

