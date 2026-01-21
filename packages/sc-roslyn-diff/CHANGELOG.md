# Changelog

## 0.7.0

- Initial package design for sc-roslyn-diff.
- Added /sc-diff command, sc-diff skill, and agent specs.
- Added sc-git-diff agent spec for GitHub/Azure PR diffs.
- Aligned runner/agents with roslyn-diff 0.7 CLI options (`--mode`, `--ignore-whitespace`, `--context`).
- Avoided dotnet tool update/install output corrupting JSON responses.
- Added support for `--text` and `--git` outputs in sc-diff/sc-git-diff.
