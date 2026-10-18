# Codex marketplace inclusion review

Reviewed 2026-10-18 by three independent `gpt-6-luna` agents, eight plugins each.
Policy: include reasonable plugins, even with known compatibility caveats, so
users can try them. Missing end-to-end verification is not an exclusion reason.
All 24 existing entries are approved **for inclusion**, not certified for every
workflow. No reviewer found a serious safety issue warranting exclusion.

The main session separately installed all 24 using Codex CLI 0.162.1 in a
temporary profile, including the four forwarded sources. No real user profile
was modified. Local skill discovery is covered by an actual app-server test;
install/list/load checks do not execute agents, launch child CLIs or call model,
GitHub API, OCR/VLM or other external service operations.

| Plugin | Inclusion | Review caveat |
|---|---|---|
| process-porn | Approved | Forwarded source; hosted Jev operation needs `TYPESAFE_API_KEY`. Remote code not audited by the Luna reviewer. |
| sc-ai-cli | Approved | Standalone CLI design/review/simulator skills and templates; no concrete host blocker found. |
| sc-ci-automation | Approved with caveat | Agent Runner conventions and references to absent `.claude/references/ci-automation-*` files need follow-up. |
| sc-codex | Approved | Codex runner by design; some invocation/log paths still assume `.claude`. |
| sc-coding-agent-hardening | Approved | Main-session instruction-editing workflow; no concrete host blocker found. |
| sc-commit-push-pr | Approved with caveat | Agent Runner/hook conventions; commits, pushes and PR creation remain outward mutations. |
| sc-delay-tasks | Approved with caveat | Task/delegation conventions and old `delay-run.py`/`.sh` references differ from shipped `sc-delay-run.py`. |
| sc-docling-pdf | Approved with caveat | Requires Docling; optional OCR/VLM dependencies may be substantial. |
| sc-gh-stack | Approved | Requires git/Python/gh/auth/gh-stack for operations; landing and destructive lifecycle approval still apply. |
| sc-git-worktree | Approved with caveat | Skill describes Claude Task delegation; Codex can use bundled instructions/scripts but host orchestration is not certified. |
| sc-github-issue | Approved with caveat | Task-agent orchestration, gh auth and worktree dependencies; `--yolo` skips workflow prompts. |
| sc-just | Approved | Standalone setup skill and templates; needs just/Python and edits project files on use. |
| sc-kanban | Approved with caveat | Agent Runner conventions; requires package dependencies and mutates board state. |
| sc-launch-term | Approved with caveat | Command-only package uses compatibility conversion. Launchers use `--yolo`/`--dangerously-skip-permissions`; review before launching. |
| sc-launchpad | Approved with caveat | Claude-style background-agent orchestration; child CLI launching/env isolation behavior not exercised here. |
| sc-lint-adoption | Approved with caveat | Forwarded source; installation checked separately, remote contents not audited by the Luna reviewer. |
| sc-lint-version-adoption | Approved with caveat | Forwarded source; installation checked separately, remote contents not audited by the Luna reviewer. |
| sc-manage | Approved | Native Codex commands supported; artifact copies use a separate dispatcher/source checkout. |
| sc-observability | Approved with caveat | Forwarded source; installation checked separately, remote contents not audited by the Luna reviewer. |
| sc-refactory | Approved with caveat | Agent Runner conventions; cargo/Oxigraph/Python dependencies and local-only workflow. |
| sc-repomix-nuget | Approved with caveat | Agent Runner conventions; Node/Python dependencies. |
| sc-roslyn-diff | Approved with caveat | Agent Runner conventions; .NET/roslyn-diff/Python dependencies. |
| sc-rust | Approved with caveat | Agent Runner conventions; cargo, coverage and composition tools required. |
| sc-startup | Approved with caveat | Default workflow mutates state; use `--readonly` for reporting and honor pull/PR/worktree authorization. |

## Follow-ups, not catalog gates

- Repair CI automation's missing reference links and delay-task helper name drift.
- Improve host-neutral delegation and installed-relative helper guidance where it
  still assumes Task, Agent Runner or `.claude` locations.
- Forwarded plugins retain upstream source/ref ownership. Installation success
  does not certify that Codex discovers each upstream skill or that a configured
  external service works; report actual failures without hiding their entries.
- Do not run launcher, mutation or credentialed-service workflows just to browse
  or validate the marketplace.
