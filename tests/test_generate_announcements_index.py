"""Tests for scripts/generate-announcements-index.py."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, REPO_ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_gen():
    return _load("generate_announcements_index", "generate-announcements-index.py")


def _load_validate():
    return _load("validate_site_html", "validate-site-html.py")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- parse_announcement ----------------------------------------------------

def test_parse_announcement_em_dash_split(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# Big Release — Now With More Stuff\n\nbody\n")
    entry = mod.parse_announcement(p)
    assert entry["title"] == "Big Release"
    assert entry["subtitle"] == "Now With More Stuff"


def test_parse_announcement_double_hyphen_split(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# Big Release -- Now With More Stuff\n")
    entry = mod.parse_announcement(p)
    assert entry["title"] == "Big Release"
    assert entry["subtitle"] == "Now With More Stuff"


def test_parse_announcement_single_hyphen_split(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# Big Release - Now With More Stuff\n")
    entry = mod.parse_announcement(p)
    assert entry["title"] == "Big Release"
    assert entry["subtitle"] == "Now With More Stuff"


def test_parse_announcement_heading_without_separator(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# Just A Title\n\nbody\n")
    entry = mod.parse_announcement(p)
    assert entry["title"] == "Just A Title"
    assert entry["subtitle"] == ""


def test_parse_announcement_missing_heading_falls_back_to_stem(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "no-heading-file.md", "no heading here\njust text\n")
    entry = mod.parse_announcement(p)
    assert entry["title"] == "no-heading-file"
    assert entry["subtitle"] == ""


def test_parse_announcement_released_date_parsed(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# T\n\n**Released:** March 5, 2026\n")
    entry = mod.parse_announcement(p)
    assert entry["date"] == dt.date(2026, 3, 5)


def test_parse_announcement_missing_date_is_none(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# T\n\nno date here\n")
    entry = mod.parse_announcement(p)
    assert entry["date"] is None


def test_parse_announcement_unparseable_date_is_none(tmp_path):
    mod = _load_gen()
    p = _write(tmp_path / "a.md", "# T\n\n**Released:** Marchember 99, 2026\n")
    entry = mod.parse_announcement(p)
    assert entry["date"] is None


# --- generate_index ---------------------------------------------------------

def test_generate_index_sorts_newest_first_and_undated_last(tmp_path):
    mod = _load_gen()
    _write(tmp_path / "old.md", "# Old\n\n**Released:** January 1, 2025\n")
    _write(tmp_path / "new.md", "# New\n\n**Released:** January 1, 2026\n")
    _write(tmp_path / "undated.md", "# Undated\n")
    mod.generate_index(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    pos_new = text.index("new.md")
    pos_old = text.index("old.md")
    pos_undated = text.index("undated.md")
    assert pos_new < pos_old < pos_undated


def test_generate_index_contains_links_escaped_titles_and_dates(tmp_path):
    mod = _load_gen()
    _write(tmp_path / "one.md",
           "# Title <One> — Sub & Stuff\n\n**Released:** February 2, 2026\n")
    mod.generate_index(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<a href="one.md">' in text
    assert "Title &lt;One&gt;" in text
    assert "Sub &amp; Stuff" in text
    assert "<small>(2026-02-02)</small>" in text


def test_generate_index_has_do_not_edit_marker(tmp_path):
    mod = _load_gen()
    _write(tmp_path / "one.md", "# T\n")
    mod.generate_index(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "do not edit" in text


def test_generated_index_passes_validate_site_html_structure_check(tmp_path):
    gen_mod = _load_gen()
    val_mod = _load_validate()
    _write(tmp_path / "one.md",
           "# Title <One> — Sub & Stuff\n\n**Released:** February 2, 2026\n")
    _write(tmp_path / "two.md", "# Another\n")
    index = gen_mod.generate_index(tmp_path)
    problems, links, ids = val_mod.check_file(index)
    assert problems == []


# --- main --------------------------------------------------------------

def test_main_returns_zero_on_success(tmp_path, capsys):
    mod = _load_gen()
    _write(tmp_path / "one.md", "# T\n")
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "generated" in out
    assert (tmp_path / "index.html").is_file()


def test_main_returns_one_for_bad_root(tmp_path, capsys):
    mod = _load_gen()
    missing_root = tmp_path / "does-not-exist"
    rc = mod.main(["--root", str(missing_root)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not a directory" in err
