#!/usr/bin/env python3
"""Validate the static site: HTML structure + internal link resolution.

Checks every .html file under site/ (or --root):

HTML structure (per file):
- non-empty, starts with <!doctype html> (case-insensitive)
- has <title> and <meta charset>
- balanced tags: every close tag must match an open tag on the stack; tags
  the HTML5 parser auto-closes (li, p, td, tr, option, ...) may be popped
  implicitly, but a close tag with no matching open, or containers left
  open at EOF (div, section, table, script, style, ...), are errors

Links (site-wide):
- every relative href/src must resolve to an existing file under the root
  (directory links resolve via index.html); absolute-path links (/x) resolve
  from the root; `#fragment` targets must exist as an id in the target file
- external links (http/https/mailto/data), and template placeholders, are
  skipped by default; --external HEAD-checks http(s) links (network!)

Generated pages (evals.html etc.) are build artifacts: run
`python3 scripts/collect-eval-reports.py` first so they exist, as the CI
pages workflow does.

Exit 0 when clean; exit 1 listing every problem as file:line: message.
"""
from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# Elements the HTML5 tree builder closes implicitly; a dangling open one of
# these is legal, and a close tag may pop them silently.
IMPLIED_CLOSE = {
    "li", "p", "dd", "dt", "td", "th", "tr", "tbody", "thead", "tfoot",
    "option", "optgroup", "colgroup", "caption",
}


class PageParser(HTMLParser):
    """Collects structure errors, links, and ids for one document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[tuple[int, str]] = []
        self.links: list[tuple[int, str]] = []
        self.ids: set[str] = set()
        self.has_title = False
        self.has_charset = False
        self._stack: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attrs = dict(attrs)
        if "id" in attrs and attrs["id"]:
            self.ids.add(attrs["id"])
        if tag == "title":
            self.has_title = True
        if tag == "meta" and ("charset" in attrs or attrs.get("http-equiv", "").lower() == "content-type"):
            self.has_charset = True
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.links.append((line, attrs[attr]))
        if tag not in VOID_ELEMENTS:
            self._stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        # <tag/> — treat as self-closed: collect attrs, never push
        line = self.getpos()[0]
        attrs = dict(attrs)
        if "id" in attrs and attrs["id"]:
            self.ids.add(attrs["id"])
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.links.append((line, attrs[attr]))

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in VOID_ELEMENTS:
            return
        if not any(open_tag == tag for open_tag, _ in self._stack):
            self.errors.append((line, f"close tag </{tag}> with no matching open tag"))
            return
        while self._stack:
            open_tag, open_line = self._stack.pop()
            if open_tag == tag:
                return
            if open_tag not in IMPLIED_CLOSE:
                self.errors.append(
                    (line, f"</{tag}> closes <{open_tag}> opened at line {open_line} "
                           f"(unclosed <{open_tag}>?)"))

    def finish(self) -> None:
        for open_tag, open_line in self._stack:
            if open_tag not in IMPLIED_CLOSE and open_tag not in ("html", "head", "body"):
                self.errors.append((open_line, f"<{open_tag}> never closed"))


def check_file(path: Path) -> tuple[list[str], list[tuple[int, str]], set[str]]:
    """Returns (structure errors, links, ids) for one html file."""
    problems: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return [f"{path}:1: empty file"], [], set()
    if not text.lstrip().lower().startswith("<!doctype html"):
        problems.append(f"{path}:1: missing <!doctype html>")
    parser = PageParser()
    parser.feed(text)
    parser.close()
    parser.finish()
    if not parser.has_title:
        problems.append(f"{path}:1: missing <title>")
    if not parser.has_charset:
        problems.append(f"{path}:1: missing <meta charset>")
    problems.extend(f"{path}:{line}: {msg}" for line, msg in parser.errors)
    return problems, parser.links, parser.ids


def _resolve(root: Path, page: Path, target: str) -> Path | None:
    """Resolve an internal link target to a file, or None if unresolvable."""
    candidate = (root / target.lstrip("/")) if target.startswith("/") else (page.parent / target)
    try:
        candidate = candidate.resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate if candidate.is_file() else None


def validate(root: Path, external: bool = False) -> list[str]:
    pages = sorted(root.rglob("*.html"))
    problems: list[str] = []
    links: list[tuple[Path, int, str]] = []
    ids_by_file: dict[Path, set[str]] = {}

    for page in pages:
        file_problems, file_links, ids = check_file(page)
        problems.extend(file_problems)
        ids_by_file[page.resolve()] = ids
        links.extend((page, line, href) for line, href in file_links)

    for page, line, href in links:
        if "{{" in href or href.startswith(("javascript:", "data:")):
            continue
        scheme = urlparse(href).scheme
        if scheme in ("http", "https"):
            if external:
                problems.extend(_check_external(page, line, href))
            continue
        if scheme:  # mailto:, tel:, ...
            continue
        target, frag = urldefrag(href)
        if not target:  # pure #fragment -> same page
            resolved = page.resolve()
        else:
            resolved = _resolve(root, page, target)
            if resolved is None:
                problems.append(f"{page}:{line}: broken link: {href}")
                continue
            resolved = resolved.resolve()
        if frag:
            ids = ids_by_file.get(resolved)
            if ids is not None and frag not in ids:
                problems.append(f"{page}:{line}: broken anchor: {href} "
                                f"(no id=\"{frag}\" in {resolved.name})")
    return problems


def _check_external(page: Path, line: int, href: str) -> list[str]:
    import urllib.request
    req = urllib.request.Request(href, method="HEAD",
                                 headers={"User-Agent": "sc-site-link-check"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                return [f"{page}:{line}: external link returned {resp.status}: {href}"]
    except Exception as exc:
        return [f"{page}:{line}: external link failed ({exc}): {href}"]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="validate site HTML and internal links")
    ap.add_argument("--root", type=Path, default=REPO_ROOT / "site")
    ap.add_argument("--external", action="store_true",
                    help="also HEAD-check external http(s) links (network)")
    args = ap.parse_args(argv)
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 1
    problems = validate(args.root, external=args.external)
    for p in problems:
        print(p)
    count = len(sorted(args.root.rglob("*.html")))
    if problems:
        print(f"FAIL: {len(problems)} problem(s) across {count} html file(s)")
        return 1
    print(f"OK: {count} html file(s), all structure and internal links valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
