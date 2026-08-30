"""Tests for scripts/validate-site-html.py (static site HTML/link validation)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_site_html", REPO_ROOT / "scripts" / "validate-site-html.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CLEAN_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Home</title>
</head>
<body>
  <div>hello</div>
</body>
</html>
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_minimal_page_has_no_problems(tmp_path):
    mod = _load()
    _write(tmp_path / "index.html", CLEAN_PAGE)
    assert mod.validate(tmp_path) == []


def test_missing_doctype_reported(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<!doctype html>\n", "")
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("missing <!doctype html>" in p for p in problems)


def test_missing_title_reported(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("  <title>Home</title>\n", "")
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("missing <title>" in p for p in problems)


def test_missing_charset_reported(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace('  <meta charset="utf-8">\n', "")
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("missing <meta charset>" in p for p in problems)


def test_unclosed_div_reported(tmp_path):
    mod = _load()
    text = """<!doctype html>
<html><head><title>t</title><meta charset="utf-8"></head>
<body>
  <div>oops
"""
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("never closed" in p for p in problems)


def test_stray_close_tag_reported(tmp_path):
    mod = _load()
    text = """<!doctype html>
<html><head><title>t</title><meta charset="utf-8"></head>
<body>
  hello</div>
</body>
</html>
"""
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("no matching open tag" in p for p in problems)


def test_implied_close_list_items_no_false_positive(tmp_path):
    mod = _load()
    text = """<!doctype html>
<html><head><title>t</title><meta charset="utf-8"></head>
<body>
  <ul><li>a<li>b</ul>
</body>
</html>
"""
    _write(tmp_path / "index.html", text)
    assert mod.validate(tmp_path) == []


def test_implied_close_table_cells_no_false_positive(tmp_path):
    mod = _load()
    text = """<!doctype html>
<html><head><title>t</title><meta charset="utf-8"></head>
<body>
  <table><tr><td>x</table>
</body>
</html>
"""
    _write(tmp_path / "index.html", text)
    assert mod.validate(tmp_path) == []


def test_broken_relative_link_reported(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="missing.html">m</a>')
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("broken link: missing.html" in p for p in problems)


def test_valid_relative_link_clean(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="other.html">o</a>')
    _write(tmp_path / "index.html", text)
    _write(tmp_path / "other.html", CLEAN_PAGE)
    assert mod.validate(tmp_path) == []


def test_directory_link_resolves_via_index(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="subdir/">s</a>')
    _write(tmp_path / "index.html", text)
    _write(tmp_path / "subdir" / "index.html", CLEAN_PAGE)
    assert mod.validate(tmp_path) == []


def test_directory_link_broken_without_index(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="subdir/">s</a>')
    _write(tmp_path / "index.html", text)
    (tmp_path / "subdir").mkdir()
    problems = mod.validate(tmp_path)
    assert any("broken link: subdir/" in p for p in problems)


def test_absolute_path_link_resolves_from_root(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="/other.html">o</a>')
    _write(tmp_path / "sub" / "page.html", text)
    _write(tmp_path / "other.html", CLEAN_PAGE)
    assert mod.validate(tmp_path) == []


def test_link_escaping_root_reported(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace(
        "<div>hello</div>", '<a href="../../etc/passwd">p</a>')
    _write(tmp_path / "sub" / "page.html", text)
    problems = mod.validate(tmp_path)
    assert any("broken link: ../../etc/passwd" in p for p in problems)


def test_fragment_same_page_passes_when_id_present(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace(
        "<div>hello</div>", '<a href="#x">x</a><div id="x">target</div>')
    _write(tmp_path / "index.html", text)
    assert mod.validate(tmp_path) == []


def test_fragment_same_page_reported_when_id_absent(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="#missing">x</a>')
    _write(tmp_path / "index.html", text)
    problems = mod.validate(tmp_path)
    assert any("broken anchor: #missing" in p for p in problems)


def test_cross_file_fragment_checked_against_target(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace(
        "<div>hello</div>", '<a href="other.html#sec">o</a>')
    _write(tmp_path / "index.html", text)
    other = CLEAN_PAGE.replace(
        "<div>hello</div>", '<div id="sec">section</div>')
    _write(tmp_path / "other.html", other)
    assert mod.validate(tmp_path) == []

    other_missing = CLEAN_PAGE  # no id="sec"
    _write(tmp_path / "other.html", other_missing)
    problems = mod.validate(tmp_path)
    assert any("broken anchor: other.html#sec" in p for p in problems)


def test_external_and_special_schemes_skipped_without_network(tmp_path):
    mod = _load()
    text = CLEAN_PAGE.replace(
        "<div>hello</div>",
        '<a href="https://example.com">e</a>'
        '<a href="http://example.com">e2</a>'
        '<a href="mailto:a@b.com">m</a>'
        '<a href="data:text/plain,hi">d</a>'
        '<a href="{{ site.url }}/x">t</a>',
    )
    _write(tmp_path / "index.html", text)
    assert mod.validate(tmp_path) == []


def test_empty_file_reported(tmp_path):
    mod = _load()
    _write(tmp_path / "index.html", "")
    problems = mod.validate(tmp_path)
    assert any("empty file" in p for p in problems)


def test_main_returns_zero_on_clean_site(tmp_path, capsys):
    mod = _load()
    _write(tmp_path / "index.html", CLEAN_PAGE)
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_main_returns_one_with_problems_printed(tmp_path, capsys):
    mod = _load()
    text = CLEAN_PAGE.replace("<div>hello</div>", '<a href="missing.html">m</a>')
    _write(tmp_path / "index.html", text)
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "broken link: missing.html" in out
    assert "FAIL" in out


def test_main_returns_one_for_nonexistent_root(tmp_path, capsys):
    mod = _load()
    missing_root = tmp_path / "does-not-exist"
    rc = mod.main(["--root", str(missing_root)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not a directory" in err
