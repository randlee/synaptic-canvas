#!/usr/bin/env python3
"""Interim local runner for plugin eval cases (until `claude plugin eval` is unlocked).

Executes each case under packages/<pkg>/evals/ exactly as authored — prompt.md
frontmatter + body, scaffold.sh fixture, graders/*.md — using headless
`claude -p`, then writes results in the same layout the official harness uses:

    packages/<pkg>/evals/results/<YYYYMMDD-HHMMSS>/aggregate-result.json
    packages/<pkg>/evals/results/<YYYYMMDD-HHMMSS>/report.html

so `scripts/collect-eval-reports.py` publishes them to site/reports/evals/
unchanged. Grader support: regex, tool_used, tool_order, file_exists, llm
(judged by a second headless call). Stdlib only.

Usage:
  python3 scripts/run-evals-local.py --package sc-gh-stack [--case GLOB]
      [--model ID] [--judge-model ID] [--runs N] [--keep-temp]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------- frontmatter
def parse_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    """Minimal YAML-subset parser for the eval files' frontmatter."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    body = text[end + 4:].lstrip("\n")
    meta: Dict[str, Any] = {}
    block_key: Optional[str] = None
    for raw in text[3:end].splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if block_key and (raw.startswith("  ") or raw.startswith("\t")):
            k, _, v = raw.strip().partition(":")
            meta[block_key][k.strip()] = _scalar(v.strip())
            continue
        block_key = None
        key, _, val = raw.partition(":")
        key, val = key.strip(), val.strip()
        if val == "":
            meta[key] = {}
            block_key = key
        else:
            meta[key] = _scalar(val)
    return meta, body


def _scalar(val: str) -> Any:
    if val.startswith("[") and val.endswith("]"):
        return [_scalar(x.strip()) for x in val[1:-1].split(",") if x.strip()]
    if val.startswith("{") and val.endswith("}"):
        out = {}
        for part in val[1:-1].split(","):
            k, _, v = part.partition(":")
            out[k.strip()] = _scalar(v.strip())
        return out
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        inner = val[1:-1]
        # Double-quoted YAML processes escapes; without this, an authored
        # "STACK\\.X" regex arrives with a literal double backslash and can
        # never match (bit the harness AND every local run of that grader).
        if val[0] == '"':
            inner = inner.replace('\\\\', '\\')
        return inner
    if val in ("true", "false"):
        return val == "true"
    try:
        return int(val)
    except ValueError:
        return val


# ---------------------------------------------------------------- transcript
class Transcript:
    def __init__(self, last_message: str, tool_calls: List[Dict[str, Any]], error: str = ""):
        self.last_message = last_message
        self.tool_calls = tool_calls  # [{"name": ..., "input_text": ...}]
        self.error = error


# Codex fast-model aliases (matches sc-launchpad's table); a gpt-* model routes
# the run through `codex exec` instead of `claude -p`.
MODEL_ALIASES = {"luna": "gpt-5.6-luna", "sol": "gpt-5.6-sol", "terra": "gpt-5.6-terra"}


def resolve_model(model: str) -> str:
    return MODEL_ALIASES.get(model, model)


def is_codex_model(model: str) -> bool:
    return model.startswith("gpt-")


def run_agent_codex(prompt: str, meta: Dict[str, Any], cwd: Path, model: str,
                    codex_bin: str) -> Transcript:
    """Run one eval case via `codex exec` (ecosystem convention: --yolo; the
    workspace is a throwaway scratch dir). JSONL events supply tool calls
    (command_execution items) and the final agent_message; --output-last-message
    is the authoritative final text."""
    env = dict(os.environ)
    for k, v in (meta.get("env") or {}).items():
        env[k] = str(v)
    # Codex runs commands via `zsh -lc` (login shell), which re-sources the
    # user profile and rebuilds PATH — defeating the case's stub-PATH env.
    # ZDOTDIR points the login shell at OUR dotfiles instead: .zshenv prepends
    # the workspace stub dir absolutely, so stubs win regardless of profile.
    zdot = cwd / ".codex-zdot"
    zdot.mkdir(exist_ok=True)
    (zdot / ".zshenv").write_text(f'export PATH="{cwd / "bin"}:$PATH"\n', encoding="utf-8")
    (zdot / ".zprofile").write_text("", encoding="utf-8")
    (zdot / ".zshrc").write_text("", encoding="utf-8")
    env["ZDOTDIR"] = str(zdot)
    # Codex has no Skill tool; its native instruction channel is AGENTS.md in
    # the workspace. Point it at the installed skills so cross-model runs test
    # the same skill content through each model's idiomatic loading path.
    skills = sorted((cwd / ".claude" / "skills").glob("*/SKILL.md"))
    if skills and not (cwd / "AGENTS.md").exists():
        lines = ["# Project skills\n",
                 "Before acting, read the relevant skill and follow it:\n"]
        lines += [f"- {p.relative_to(cwd)}\n" for p in skills]
        (cwd / "AGENTS.md").write_text("".join(lines), encoding="utf-8")
    last_file = cwd / ".codex-last-message"
    cmd = [codex_bin, "exec", "--yolo", "--model", model, "--json",
           "--output-last-message", str(last_file), "--skip-git-repo-check",
           "-c", 'shell_environment_policy.inherit="all"', prompt]
    try:
        # Codex sessions run slower and more exploratorily than claude -p;
        # give them double the case's budget rather than failing on variance.
        # stdin MUST be DEVNULL: with a piped/inherited stdin, codex exec
        # waits to read it as an appended <stdin> block and hangs forever
        # ("Reading additional input from stdin...").
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL,
                              timeout=2 * int(meta.get("timeout_seconds", 300)))
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or b"")
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "ignore")
        return Transcript("", [], error=f"timeout (partial events: {partial[-300:]!r})")
    last, calls = "", []
    for line in proc.stdout.splitlines():
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = evt.get("item") or {}
        if evt.get("type") == "item.completed":
            if item.get("type") == "command_execution":
                calls.append({"name": "Bash",
                              "input_text": json.dumps({"command": item.get("command", "")})})
            elif item.get("type") == "agent_message":
                last = item.get("text", last)
    if last_file.exists():
        text = last_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            last = text
        last_file.unlink(missing_ok=True)
    err = "" if proc.returncode == 0 else f"codex exited {proc.returncode}: {proc.stderr[-500:]}"
    return Transcript(last, calls, error=err)


def run_agent(prompt: str, meta: Dict[str, Any], cwd: Path, model: str,
              claude_bin: str) -> Transcript:
    if is_codex_model(model):
        codex_bin = shutil.which("codex")
        if not codex_bin:
            return Transcript("", [], error="`codex` CLI not on PATH")
        return run_agent_codex(prompt, meta, cwd, model, codex_bin)
    env = dict(os.environ)
    for k, v in (meta.get("env") or {}).items():
        env[k] = str(v)
    # The case env's relative PATH entries (./bin, ../bin) break for
    # processes the agent's scripts spawn from other cwds (e.g. a new
    # worktree). Prepend the workspace stub dir ABSOLUTELY so stubs win
    # everywhere — the claude-path analogue of the codex ZDOTDIR fix.
    ws_bin = cwd / "bin"
    if ws_bin.is_dir():
        env["PATH"] = f"{ws_bin}:{env.get('PATH', '')}"
    cmd = [claude_bin, "-p", prompt, "--model", model,
           "--output-format", "stream-json", "--verbose",
           "--max-turns", str(meta.get("max_turns", 20))]
    tools = meta.get("allowed_tools")
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL,
                              timeout=int(meta.get("timeout_seconds", 300)))
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or b"")
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "ignore")
        return Transcript("", [], error=f"timeout (partial: {partial[-400:]!r})")
    last, calls = "", []
    for line in proc.stdout.splitlines():
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "assistant":
            for block in (evt.get("message") or {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls.append({"name": block.get("name", ""),
                                  "input_text": json.dumps(block.get("input", {}))})
                elif block.get("type") == "text":
                    last = block.get("text", last)
        elif evt.get("type") == "result":
            last = evt.get("result") or last
    err = "" if proc.returncode == 0 else f"claude exited {proc.returncode}: {proc.stderr[-500:]}"
    return Transcript(last, calls, error=err)


# ------------------------------------------------------------------- graders
def _grader_target_text(target: Any, tr: Transcript, workspace: Path) -> str:
    if isinstance(target, dict) and target.get("source") == "file":
        p = workspace / str(target.get("path", ""))
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""
    if target == "trace":
        return "\n".join(c["input_text"] for c in tr.tool_calls)
    return tr.last_message


def grade(g: Dict[str, Any], tr: Transcript, workspace: Path, judge_model: str,
          claude_bin: str) -> Dict[str, Any]:
    gtype = g.get("type", "regex")
    try:
        if gtype == "regex":
            text = _grader_target_text(g.get("target", "last_message"), tr, workspace)
            flags = re.IGNORECASE if "i" in str(g.get("flags", "")) else 0
            hit = re.search(str(g["pattern"]), text, flags) is not None
            want = g.get("match", "contains")
            passed = hit if want == "contains" else not hit
            return {"passed": passed, "evidence": f"pattern {'found' if hit else 'absent'}"}
        if gtype == "tool_used":
            pat = re.compile(str(g.get("input_match", "")), re.IGNORECASE)
            n = sum(1 for c in tr.tool_calls
                    if (not g.get("tool") or c["name"] == g["tool"]) and pat.search(c["input_text"]))
            lo, hi = int(g.get("min", 1)), g.get("max")
            passed = n >= lo and (hi is None or n <= int(hi))
            return {"passed": passed, "evidence": f"{n} matching call(s)"}
        if gtype == "tool_order":
            def first(pat: str) -> Optional[int]:
                rx = re.compile(pat, re.IGNORECASE)
                for i, c in enumerate(tr.tool_calls):
                    if rx.search(c["input_text"]):
                        return i
                return None
            b, a = first(str(g["before"])), first(str(g["after"]))
            passed = b is not None and a is not None and b < a
            return {"passed": passed, "evidence": f"before@{b} after@{a}"}
        if gtype == "file_exists":
            passed = any(workspace.rglob(str(g["path"])))
            return {"passed": passed, "evidence": str(g["path"])}
        if gtype == "llm":
            verdict = _judge(str(g["criteria"]), tr.last_message, judge_model, claude_bin)
            return verdict
    except Exception as exc:  # a broken grader fails closed, with the reason
        return {"passed": False, "evidence": f"grader error: {exc}"}
    return {"passed": False, "evidence": f"unsupported grader type: {gtype}"}


def _judge(criteria: str, last_message: str, judge_model: str, claude_bin: str) -> Dict[str, Any]:
    prompt = (
        "You are grading an AI agent's final answer against pass criteria.\n\n"
        f"CRITERIA:\n{criteria}\n\nAGENT'S FINAL ANSWER:\n{last_message[:8000]}\n\n"
        "Reply with exactly one line: PASS: <one-sentence reason> or FAIL: <one-sentence reason>."
    )
    try:
        proc = subprocess.run([claude_bin, "-p", prompt, "--model", judge_model,
                               "--output-format", "json"],
                              capture_output=True, text=True, timeout=120)
        result = json.loads(proc.stdout).get("result", "")
    except Exception as exc:
        return {"passed": False, "evidence": f"judge error: {exc}"}
    passed = result.strip().upper().startswith("PASS")
    return {"passed": passed, "evidence": result.strip()[:300]}


# ---------------------------------------------------------------------- runs
def run_case(case_dir: Path, pkg_dir: Path, model_override: Optional[str],
             judge_model: str, runs_override: Optional[int], keep_temp: bool,
             claude_bin: str) -> Dict[str, Any]:
    meta, prompt = parse_front_matter((case_dir / "prompt.md").read_text(encoding="utf-8"))
    model = resolve_model(model_override or str(meta.get("model", DEFAULT_MODEL)))
    n_runs = runs_override or int(meta.get("runs", 1))
    graders = sorted((case_dir / "graders").glob("*.md"))
    arms = []
    for _ in range(n_runs):
        workspace = Path(tempfile.mkdtemp(prefix=f"eval-{case_dir.name}-"))
        try:
            scaffold = case_dir / "scaffold.sh"
            if scaffold.exists():
                subprocess.run(["bash", str(scaffold)], cwd=workspace, check=True,
                               capture_output=True, text=True, timeout=120)
            # project-scope install of the package so the skill/agents are live
            _install_package(pkg_dir, workspace / ".claude")
            tr = run_agent(prompt, meta, workspace, model, claude_bin)
            results = []
            for gf in graders:
                gmeta, _ = parse_front_matter(gf.read_text(encoding="utf-8"))
                r = grade(gmeta, tr, workspace, judge_model, claude_bin)
                results.append({"name": gf.stem, "type": gmeta.get("type", "regex"), **r})
            arms.append({"graders": results, "error": tr.error,
                         "last_message": tr.last_message[-4000:],
                         "tool_call_count": len(tr.tool_calls)})
        finally:
            if not keep_temp:
                shutil.rmtree(workspace, ignore_errors=True)
    return {"name": case_dir.name, "tags": meta.get("tags", []), "model": model,
            "arms": {"with": arms}}


def _install_package(pkg_dir: Path, dest: Path) -> None:
    manifest = pkg_dir / "manifest.yaml"
    rels: List[str] = []
    current = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.endswith(":") and not line.startswith(" "):
            current = "artifacts" if s == "artifacts:" else None
        elif current and s.startswith("- ") and "/" in s:
            rels.append(s[2:].strip())
    for rel in rels:
        src = pkg_dir / rel
        if src.is_file():
            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


# -------------------------------------------------------------------- report
def write_report(out_dir: Path, suite_name: str, cases: List[Dict[str, Any]]) -> None:
    def case_pass(c: Dict[str, Any]) -> bool:
        return all(g["passed"] for arm in c["arms"]["with"] for g in arm["graders"])

    passed = sum(1 for c in cases if case_pass(c))
    agg = {"schemaVersion": "local-1", "runner": "scripts/run-evals-local.py",
           "suite": {"name": suite_name, "caseCount": len(cases), "passCount": passed,
                     "passRate": round(passed / len(cases), 3) if cases else 0.0},
           "cases": cases}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "aggregate-result.json").write_text(json.dumps(agg, indent=2), encoding="utf-8")

    rows = []
    for c in cases:
        ok = case_pass(c)
        gr_rows = "".join(
            f"<tr><td>{html.escape(g['name'])}</td><td>{html.escape(g['type'])}</td>"
            f"<td class='{'pass' if g['passed'] else 'fail'}'>{'PASS' if g['passed'] else 'FAIL'}</td>"
            f"<td>{html.escape(str(g.get('evidence', '')))}</td></tr>"
            for arm in c["arms"]["with"] for g in arm["graders"])
        last = html.escape(c["arms"]["with"][-1]["last_message"]) if c["arms"]["with"] else ""
        rows.append(
            f"<section><h2 class='{'pass' if ok else 'fail'}'>{html.escape(c['name'])} — "
            f"{'PASS' if ok else 'FAIL'}</h2><table><tr><th>grader</th><th>type</th>"
            f"<th>verdict</th><th>evidence</th></tr>{gr_rows}</table>"
            f"<details><summary>final message</summary><pre>{last}</pre></details></section>")
    (out_dir / "report.html").write_text(
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{html.escape(suite_name)} evals</title>"
        "<style>body{font-family:system-ui;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;"
        "padding:.3rem .5rem;text-align:left}pre{white-space:pre-wrap;background:#f6f6f6;"
        "padding:1rem}.pass{color:#0a7a2f}.fail{color:#b3261e}</style>"
        f"<h1>{html.escape(suite_name)} — local eval run</h1>"
        f"<p>{passed}/{len(cases)} cases passed · runner: interim local harness "
        "(pending <code>claude plugin eval</code> access)</p>" + "".join(rows),
        encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="interim local plugin-eval runner")
    ap.add_argument("--package", required=True)
    ap.add_argument("--case", default="*", help="case name glob")
    ap.add_argument("--model", default=None)
    ap.add_argument("--judge-model", default=DEFAULT_MODEL)
    ap.add_argument("--runs", type=int, default=None)
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args(argv)

    pkg_dir = PACKAGES_DIR / args.package
    evals_dir = pkg_dir / "evals"
    if not evals_dir.is_dir():
        print(f"error: no evals/ in {pkg_dir}", file=sys.stderr)
        return 1
    claude_bin = shutil.which("claude")
    if not claude_bin:
        print("error: `claude` CLI not on PATH", file=sys.stderr)
        return 1
    case_dirs = [d for d in sorted(evals_dir.iterdir())
                 if d.is_dir() and d.name != "results" and (d / "prompt.md").exists()
                 and fnmatch.fnmatch(d.name, args.case)]
    if not case_dirs:
        print(f"error: no cases match {args.case!r}", file=sys.stderr)
        return 1

    cases = []
    for cd in case_dirs:
        print(f"running: {cd.name} ...", flush=True)
        cases.append(run_case(cd, pkg_dir, args.model, args.judge_model,
                              args.runs, args.keep_temp, claude_bin))
        ok = all(g["passed"] for arm in cases[-1]["arms"]["with"] for g in arm["graders"])
        print(f"  {'PASS' if ok else 'FAIL'}", flush=True)

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = evals_dir / "results" / stamp
    # Tag the suite with the subject model so haiku/luna runs are
    # distinguishable in site/reports/evals history.
    tag_model = resolve_model(args.model) if args.model else DEFAULT_MODEL
    short = tag_model.split("-")[1] if tag_model.startswith("claude-") else tag_model.rsplit("-", 1)[-1]
    write_report(out_dir, f"{args.package}-{short}", cases)
    print(f"wrote {out_dir.relative_to(REPO_ROOT)}/aggregate-result.json and report.html")
    print("publish with: python3 scripts/collect-eval-reports.py --package " + args.package)
    return 0


if __name__ == "__main__":
    sys.exit(main())
