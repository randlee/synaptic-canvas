"""env_file: dotenv parsing, lookup across linked worktrees, and merge precedence."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "packages" / "sc-launchpad" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from launchpad_env import find_env_file, merge_env, parse_env_file  # noqa: E402
from launchpad_models import LaunchFailure  # noqa: E402


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


# --- parsing -------------------------------------------------------------------


def test_dotenv_syntax(tmp_path):
    env = write(tmp_path / ".env", "﻿" + "\r\n".join([
        "# comment",
        "",
        "PLAIN=value",
        "  SPACED  =  padded value  ",
        "export EXPORTED=1",
        "EMPTY=",
        "INLINE=abc # trailing comment",
        "HASH=abc#not-a-comment",
        "SINGLE='lit $HOME \\n # kept'",
        'DOUBLE="a\\nb \\"q\\" \\\\ $HOME" # comment',
        "REPEAT=first",
        "REPEAT=last",
        "URL=https://example.invalid/?a=b=c",
    ]))
    assert parse_env_file(env) == {
        "PLAIN": "value",
        "SPACED": "padded value",
        "EXPORTED": "1",
        "EMPTY": "",
        "INLINE": "abc",
        "HASH": "abc#not-a-comment",
        "SINGLE": "lit $HOME \\n # kept",
        "DOUBLE": 'a\nb "q" \\ $HOME',
        "REPEAT": "last",
        "URL": "https://example.invalid/?a=b=c",
    }


@pytest.mark.parametrize(
    ("line", "problem"),
    [
        ("NO_EQUALS_sk-secret", "expected KEY=value"),
        ("1BAD=sk-secret", "not a valid identifier"),
        ("BAD KEY=sk-secret", "not a valid identifier"),
        ("K='sk-secret", "unterminated single-quoted"),
        ('K="sk-secret', "unterminated double-quoted"),
        ("K='sk-secret' extra", "after the closing quote"),
    ],
)
def test_malformed_line_reports_number_never_content(tmp_path, line, problem):
    env = write(tmp_path / ".env", f"OK=1\n{line}\n")
    with pytest.raises(LaunchFailure) as exc:
        parse_env_file(env)
    failure = exc.value
    assert failure.code == "VALIDATION.INVALID_ENV_FILE"
    assert "line 2" in failure.message and problem in failure.message
    assert "sk-secret" not in str(failure.to_error())


def test_non_utf8_file_is_invalid(tmp_path):
    env = tmp_path / ".env"
    env.write_bytes(b"K=\xff\xfe\n")
    with pytest.raises(LaunchFailure) as exc:
        parse_env_file(env)
    assert exc.value.code == "VALIDATION.INVALID_ENV_FILE"


# --- lookup ----------------------------------------------------------------------


@pytest.fixture
def repos(tmp_path):
    """A main checkout with an untracked .env and a linked worktree, laid out the way
    `git worktree add` leaves them (no git binary needed)."""
    main = tmp_path / "repo"
    (main / ".git" / "worktrees" / "feat").mkdir(parents=True)
    write(main / ".git" / "worktrees" / "feat" / "commondir", "../..\n")
    linked = tmp_path / "repo-worktrees" / "feat"
    write(linked / ".git", f"gitdir: {main / '.git' / 'worktrees' / 'feat'}\n")
    (linked / "pkg" / "sub").mkdir(parents=True)
    write(main / ".env", "WHERE=main\n")
    return main, linked


def test_linked_worktree_falls_back_to_the_main_checkout(repos):
    main, linked = repos
    assert find_env_file(".env", linked / "pkg" / "sub") == (main / ".env").resolve()


def test_closest_file_wins(repos):
    main, linked = repos
    write(linked / ".env", "WHERE=linked\n")
    assert find_env_file(".env", linked / "pkg" / "sub") == (linked / ".env").resolve()
    write(linked / "pkg" / "sub" / ".env", "WHERE=cwd\n")
    assert find_env_file(".env", linked / "pkg" / "sub") == (linked / "pkg" / "sub" / ".env").resolve()


def test_relative_gitdir_and_subdirectory_of_main(repos, tmp_path):
    main, linked = repos
    write(linked / ".git", "gitdir: ../../repo/.git/worktrees/feat\n")
    assert find_env_file(".env", linked) == (main / ".env").resolve()
    (main / "src").mkdir()
    assert find_env_file(".env", main / "src") == (main / ".env").resolve()


def test_absolute_path_is_used_as_given(tmp_path):
    env = write(tmp_path / "elsewhere" / "creds.env", "K=1\n")
    assert find_env_file(str(env), tmp_path) == env.resolve()


def test_not_found_lists_every_place_searched(repos):
    _, linked = repos
    with pytest.raises(LaunchFailure) as exc:
        find_env_file("missing.env", linked / "pkg")
    assert exc.value.code == "VALIDATION.ENV_FILE_NOT_FOUND"
    searched = exc.value.details["searched"]
    assert [Path(p).parent.name for p in searched] == ["pkg", "feat", "repo"]


def test_outside_any_repository_only_base_is_searched(tmp_path):
    with pytest.raises(LaunchFailure) as exc:
        find_env_file(".env", tmp_path)
    assert exc.value.details["searched"] == [str(tmp_path / ".env")]


# --- merge -----------------------------------------------------------------------


def test_file_overrides_inherited():
    merged = merge_env({"ANTHROPIC_API_KEY": "stale", "KEEP": "1"}, {"ANTHROPIC_API_KEY": "fresh"}, False)
    assert merged == {"ANTHROPIC_API_KEY": "fresh", "KEEP": "1"}


def test_windows_names_are_case_insensitive():
    inherited = {"PATH": "/usr/bin", "Other": "x"}
    assert merge_env(inherited, {"Path": "/opt/bin"}, True) == {"Path": "/opt/bin", "Other": "x"}
    assert merge_env(inherited, {"Path": "/opt/bin"}, False) == {"PATH": "/usr/bin", "Other": "x", "Path": "/opt/bin"}
