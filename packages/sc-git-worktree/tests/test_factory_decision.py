"""Tests for the worktree factory decision model in worktree_create.py.

See DESIGN.md "Worktree factory decision model". Create is a factory that
produces exactly one of three products for every request:

    A. Flat worktree  - legacy, unchanged.
    B. New stack       - same path as A, plus rerere + gh stack init.
    C. Stack layer      - no new worktree; a layer in the base's existing
                           stack worktree via git checkout -b + gh stack add.

Precedence: Intent (`flat`) > Dependency > Policy (`always_stack`) > default A,
evaluated lazily via a stack-activity probe (positive-signal rule: every
indeterminate input resolves to A).

This file replaces test_needs_stack_guard.py and test_always_stack.py, which
tested the three guards this model supersedes. test_gh_stack_tracking.py is
unchanged - cleanup/abort/scan guards are out of scope for this rework.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_create import CreateInput, create_worktree_main
from envelope import ErrorCodes
import worktree_shared


# =============================================================================
# Real-git fixtures
# =============================================================================


def _run(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_repo(tmp_path: Path, initial_branch: str = "main") -> Path:
    """Create a minimal real git repo with one commit on `initial_branch`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "-b", initial_branch], cwd=repo)
    _run(["config", "user.email", "test@example.com"], cwd=repo)
    _run(["config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("init\n")
    _run(["add", "."], cwd=repo)
    _run(["commit", "-m", "init"], cwd=repo)
    return repo


def _make_merged_branch(repo: Path, branch: str) -> None:
    """Create a branch pointing at the same commit as main (trivially merged)."""
    _run(["branch", branch, "main"], cwd=repo)


def _make_unmerged_branch(repo: Path, branch: str) -> None:
    """Create a branch with a commit that is NOT on main."""
    _run(["checkout", "-b", branch, "main"], cwd=repo)
    (repo / f"{branch.replace('/', '_')}.txt").write_text("wip\n")
    _run(["add", "."], cwd=repo)
    _run(["commit", "-m", f"wip on {branch}"], cwd=repo)
    _run(["checkout", "main"], cwd=repo)


def _mark_gh_stack(wt_path: Path) -> None:
    """Simulate gh-stack having written its per-worktree tracking marker."""
    result = _run(["rev-parse", "--git-dir"], cwd=wt_path)
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (wt_path / git_dir).resolve()
    (git_dir / "gh-stack").touch()


def _mark_rebase_in_progress(wt_path: Path) -> None:
    """Simulate an in-progress rebase in a worktree's git-dir."""
    result = _run(["rev-parse", "--git-dir"], cwd=wt_path)
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (wt_path / git_dir).resolve()
    (git_dir / "rebase-merge").mkdir(exist_ok=True)


def _write_shared_settings(repo: Path, always_stack: bool = True, stack_root: str = None) -> None:
    sc_dir = repo / ".sc"
    sc_dir.mkdir(parents=True, exist_ok=True)
    lines = ["git:", f"  always_stack: {'true' if always_stack else 'false'}"]
    if stack_root:
        lines.append(f"  stack_root: {stack_root}")
    (sc_dir / "shared-settings.yaml").write_text("\n".join(lines) + "\n")


def _make_input(repo: Path, tmp_path: Path, branch: str, base: str, **overrides) -> CreateInput:
    defaults = dict(
        branch=branch,
        base=base,
        purpose="test",
        owner="pytest",
        repo_root=str(repo),
        worktree_base=str(tmp_path / "wt-base"),
        tracking_enabled=False,
        protected_branches=["main"],
        cache_protected_branches=False,
    )
    defaults.update(overrides)
    return CreateInput(**defaults)


# =============================================================================
# gh stub on PATH
# =============================================================================


GH_STUB_TEMPLATE = """#!/bin/sh
LOG="{log_path}"
echo "$@" >> "$LOG"
case "$1" in
  --version)
    echo "gh version 2.0.0 (stub)"
    exit 0
    ;;
  extension)
    if [ "$2" = "list" ]; then
      if [ "{with_extension}" = "1" ]; then
        echo "gh-stack  github/gh-stack  1.0.0"
      fi
      exit 0
    fi
    exit 1
    ;;
  stack)
    if [ "$2" = "init" ]; then
      exit {stack_init_exit}
    fi
    if [ "$2" = "add" ]; then
      exit {stack_add_exit}
    fi
    exit 1
    ;;
  *)
    exit 1
    ;;
esac
"""


def _install_gh_stub(
    tmp_path: Path,
    monkeypatch,
    with_extension: bool = True,
    stack_init_exit: int = 0,
    stack_add_exit: int = 0,
) -> Path:
    """Prepend a fake `gh` binary (with an invocation log) onto PATH."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    log_path = tmp_path / "gh-invocations.log"
    if not log_path.exists():
        log_path.write_text("")

    script = GH_STUB_TEMPLATE.format(
        log_path=str(log_path),
        with_extension="1" if with_extension else "0",
        stack_init_exit=stack_init_exit,
        stack_add_exit=stack_add_exit,
    )
    gh_path = bin_dir / "gh"
    gh_path.write_text(script)
    gh_path.chmod(gh_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return log_path


def _no_gh_on_path(monkeypatch, tmp_path: Path) -> None:
    """Point PATH at a directory with only `git` symlinked in, so `gh`
    resolves to nothing but git commands still work."""
    git_only_dir = tmp_path / "git-only-bin"
    if not git_only_dir.exists():
        git_only_dir.mkdir()
        git_path = subprocess.run(
            ["which", "git"], capture_output=True, text=True
        ).stdout.strip()
        (git_only_dir / "git").symlink_to(git_path)
    monkeypatch.setenv("PATH", str(git_only_dir))


def _install_skill(repo: Path) -> None:
    """Create the managing-gh-stacks SKILL.md under the repo's .claude dir."""
    skill_dir = repo / ".claude" / "skills" / "managing-gh-stacks"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# managing-gh-stacks\n")


def _no_stack_field_keys(data: dict) -> bool:
    stack_keys = {
        "stacked",
        "product",
        "stack_root",
        "stack_shape",
        "stack_init",
        "stack_add",
        "requested_base",
        "flat_override",
    }
    return not (stack_keys & data.keys())


# =============================================================================
# 1. Stack-naive repo: everything is product A (positive-signal rule)
# =============================================================================


class TestStackNaiveRepoAlwaysProductA:
    def test_flat_off_main(self, tmp_path, monkeypatch):
        _no_gh_on_path(monkeypatch, tmp_path)  # prove gh is never even consulted
        repo = _init_repo(tmp_path)
        input_data = _make_input(repo, tmp_path, branch="feature/off-main", base="main")

        envelope = create_worktree_main(input_data)

        assert envelope.success is True
        assert Path(envelope.data["path"]) == tmp_path / "wt-base" / "feature/off-main"
        assert Path(envelope.data["path"]).exists()
        assert _no_stack_field_keys(envelope.data)

    def test_flat_off_unmerged_base_branch_of_branch_keeps_working(self, tmp_path, monkeypatch):
        """The key distribution guarantee: branch-of-branch off an unmerged,
        untracked base stays a plain flat create when the repo is not
        stack-active - dependency is never even evaluated."""
        _no_gh_on_path(monkeypatch, tmp_path)
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged")

        new_branch = "feature/child-of-unmerged"
        input_data = _make_input(repo, tmp_path, branch=new_branch, base="feature/unmerged")

        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert Path(envelope.data["path"]) == tmp_path / "wt-base" / new_branch
        assert Path(envelope.data["path"]).exists()
        assert _no_stack_field_keys(envelope.data)

        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch in branch_list

    def test_flat_true_off_unmerged_base(self, tmp_path, monkeypatch):
        _no_gh_on_path(monkeypatch, tmp_path)
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged-flat")

        new_branch = "feature/child-flat"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/unmerged-flat", flat=True
        )

        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert Path(envelope.data["path"]) == tmp_path / "wt-base" / new_branch
        assert _no_stack_field_keys(envelope.data)

    def test_transcript_has_no_stack_steps_when_not_stack_active(self, tmp_path, monkeypatch):
        _no_gh_on_path(monkeypatch, tmp_path)
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged2")

        input_data = _make_input(
            repo, tmp_path, branch="feature/child2", base="feature/unmerged2"
        )
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        steps = {e["step"] for e in envelope.metadata["transcript"]}
        forbidden = {"check_stack_prerequisites", "resolve_product", "protected branches", "resolve stack_root"}
        assert not (forbidden & steps), f"unexpected stacking transcript steps: {forbidden & steps}"


# =============================================================================
# 2. Stack-naive repo WITH a settings file present but no always_stack key
# =============================================================================


class TestSettingsFileWithoutAlwaysStackKey:
    def test_no_always_stack_key_is_product_a(self, tmp_path, monkeypatch):
        _no_gh_on_path(monkeypatch, tmp_path)
        repo = _init_repo(tmp_path)
        sc_dir = repo / ".sc"
        sc_dir.mkdir(parents=True, exist_ok=True)
        (sc_dir / "shared-settings.yaml").write_text("git:\n  stack_root: develop\n")

        input_data = _make_input(repo, tmp_path, branch="feature/no-key", base="main")
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert _no_stack_field_keys(envelope.data)


# =============================================================================
# 3. always_stack: false with trailing comment, no PyYAML fallback path
# =============================================================================


class TestAlwaysStackFalseWithCommentNoYaml:
    def test_regression_comment_bug(self, tmp_path, monkeypatch):
        monkeypatch.setattr(worktree_shared, "yaml", None)
        _no_gh_on_path(monkeypatch, tmp_path)
        repo = _init_repo(tmp_path)
        sc_dir = repo / ".sc"
        sc_dir.mkdir(parents=True, exist_ok=True)
        (sc_dir / "shared-settings.yaml").write_text(
            "git:\n  always_stack: false  # not ready yet\n"
        )

        input_data = _make_input(repo, tmp_path, branch="feature/comment-ok", base="main")
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert _no_stack_field_keys(envelope.data)


# =============================================================================
# 4. Stack-active via always_stack
# =============================================================================


class TestStackActiveViaAlwaysStack:
    def test_prereqs_missing_lists_installs(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _write_shared_settings(repo, always_stack=True)
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=False)

        branch = "feature/blocked"
        input_data = _make_input(repo, tmp_path, branch=branch, base="main")

        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.CREATE_STACK_PREREQS_MISSING
        assert envelope.data["gh_stack_extension"] is False
        assert "gh extension install github/gh-stack" in envelope.error.suggested_action
        assert "install GitHub CLI" not in envelope.error.suggested_action

        # No mutation happened.
        branch_list = _run(["branch", "--list", branch], cwd=repo).stdout
        assert branch not in branch_list

    def test_prereqs_present_produces_product_b(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _run(["branch", "develop", "main"], cwd=repo)
        _write_shared_settings(repo, always_stack=True)
        _install_skill(repo)
        log_path = _install_gh_stub(tmp_path, monkeypatch, with_extension=True, stack_init_exit=0)

        branch = "feature/stacked-thing"
        input_data = _make_input(repo, tmp_path, branch=branch, base="main")

        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        data = envelope.data
        assert data["stacked"] is True
        assert data["product"] == "new_stack"
        assert data["stack_init"]["ok"] is True
        assert data["stack_root"] == "develop"
        assert data["stack_shape"] == f"(develop) <- {branch}"
        # base ("main") != stack_root ("develop" wins because it exists) -
        # the requested base is surfaced.
        assert data["requested_base"] == "main"

        # SAME path a flat worktree would use - no stack/ prefix.
        expected_path = tmp_path / "wt-base" / branch
        assert Path(data["path"]) == expected_path
        assert expected_path.exists()

        log_text = log_path.read_text()
        assert f"stack init --base develop {branch}" in log_text

        rerere = _run(["config", "--get", "rerere.enabled"], cwd=expected_path).stdout.strip()
        assert rerere == "true"

    def test_requested_base_surfaced_when_base_differs_from_stack_root(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _run(["branch", "trunk", "main"], cwd=repo)
        _write_shared_settings(repo, always_stack=True, stack_root="trunk")
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=True)

        branch = "feature/diff-base"
        input_data = _make_input(repo, tmp_path, branch=branch, base="main")
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert envelope.data["requested_base"] == "main"
        assert envelope.data["stack_root"] == "trunk"

    def test_stack_root_default_develop_present(self, tmp_path):
        repo = _init_repo(tmp_path, initial_branch="main")
        _run(["branch", "develop", "main"], cwd=repo)
        assert worktree_shared.resolve_stack_root(repo) == "develop"

    def test_stack_root_default_develop_absent(self, tmp_path):
        repo = _init_repo(tmp_path, initial_branch="main")
        assert worktree_shared.resolve_stack_root(repo) == "main"

    def test_stack_init_failure_is_recoverable(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _run(["branch", "develop", "main"], cwd=repo)
        _write_shared_settings(repo, always_stack=True)
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=True, stack_init_exit=1)

        branch = "feature/init-fails"
        input_data = _make_input(repo, tmp_path, branch=branch, base="main")
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        data = envelope.data
        assert data["stacked"] is True
        assert data["stack_init"]["ok"] is False
        assert "next_step" in data["stack_init"]

        expected_path = tmp_path / "wt-base" / branch
        assert expected_path.exists()


# =============================================================================
# 5. Stack-active via tracking-marker-only (no always_stack)
# =============================================================================


class TestStackActiveViaTrackingMarkerOnly:
    def test_independent_base_is_product_a_policy_off(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=True)

        # Some unrelated worktree carries gh-stack tracking, but the base for
        # this create ("main") is protected/independent and always_stack is
        # not set - policy is off, so product A.
        other_wt = tmp_path / "other-wt"
        _run(["worktree", "add", "-b", "feature/other-stack", str(other_wt), "main"], cwd=repo)
        _mark_gh_stack(other_wt)

        branch = "feature/independent"
        input_data = _make_input(repo, tmp_path, branch=branch, base="main")
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert _no_stack_field_keys(envelope.data)
        assert Path(envelope.data["path"]) == tmp_path / "wt-base" / branch

    def test_dependent_base_with_tracked_stack_is_product_c(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        # NOTE: install the skill AFTER any `git add .`-based branch setup -
        # _make_unmerged_branch stages the whole tree, which would otherwise
        # commit .claude/ onto the feature branch and then delete it again on
        # `git checkout main` (files tracked on one branch but not the other).
        _make_unmerged_branch(repo, "feature/base-of-stack")
        _install_skill(repo)
        log_path = _install_gh_stub(tmp_path, monkeypatch, with_extension=True)

        stack_wt = tmp_path / "stack-wt"
        _run(["worktree", "add", str(stack_wt), "feature/base-of-stack"], cwd=repo)
        _mark_gh_stack(stack_wt)

        new_branch = "feature/layer-two"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/base-of-stack"
        )
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        data = envelope.data
        assert data["stacked"] is True
        assert data["product"] == "layer"
        assert data["path"] == str(stack_wt)  # NO new worktree dir

        # No new worktree directory was created under wt-base for this branch.
        assert not (tmp_path / "wt-base" / new_branch).exists()

        # Branch was created IN the stack worktree via checkout -b.
        branch_list = _run(["branch", "--list", new_branch], cwd=stack_wt).stdout
        assert new_branch in branch_list

        log_text = log_path.read_text()
        assert f"stack add {new_branch}" in log_text

    def test_dependent_base_rebase_in_progress_refuses(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/rebasing-base")
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=True)

        stack_wt = tmp_path / "stack-wt-rebasing"
        _run(["worktree", "add", str(stack_wt), "feature/rebasing-base"], cwd=repo)
        _mark_gh_stack(stack_wt)
        _mark_rebase_in_progress(stack_wt)

        new_branch = "feature/blocked-by-rebase"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/rebasing-base"
        )
        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.CREATE_NEEDS_STACK
        assert envelope.data["rebase_in_progress"] is True
        assert "rebase" in envelope.error.suggested_action.lower()

        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch not in branch_list

    def test_dependent_base_no_stack_to_join_refuses_naming_gh_stack_init(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        # NOTE: create the unmerged base branch BEFORE installing the skill -
        # _make_unmerged_branch stages the whole tree, which would otherwise
        # commit .claude/ onto that branch and delete it again on checkout.
        _make_unmerged_branch(repo, "feature/no-stack-base")
        _install_skill(repo)
        _install_gh_stub(tmp_path, monkeypatch, with_extension=True)

        # An unrelated worktree elsewhere carries tracking (so the repo is
        # stack-active), but the base itself has NO worktree/tracking at all.
        other_wt = tmp_path / "other-wt2"
        _run(["worktree", "add", "-b", "feature/other-stack2", str(other_wt), "main"], cwd=repo)
        _mark_gh_stack(other_wt)

        new_branch = "feature/needs-new-stack"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/no-stack-base"
        )
        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.CREATE_NEEDS_STACK
        assert envelope.data["gh_stack_tracked"] is False
        assert "gh stack init --base" in envelope.error.suggested_action
        assert "managing-gh-stacks" in envelope.error.suggested_action

        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch not in branch_list

    def test_flat_true_is_product_a_even_when_stack_active(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)
        # No gh, no skill - if the gate ran at all, this would refuse.
        _no_gh_on_path(monkeypatch, tmp_path)

        other_wt = tmp_path / "other-wt3"
        _run(["worktree", "add", "-b", "feature/other-stack3", str(other_wt), "main"], cwd=repo)
        _mark_gh_stack(other_wt)

        _make_unmerged_branch(repo, "feature/base-flat-override")
        new_branch = "feature/flat-wins"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/base-flat-override", flat=True
        )
        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert _no_stack_field_keys(envelope.data)
        assert Path(envelope.data["path"]) == tmp_path / "wt-base" / new_branch


# =============================================================================
# 6. Fallback parser unit tests
# =============================================================================


class TestFallbackParserUnit:
    def _write_and_load(self, tmp_path, monkeypatch, text: str):
        monkeypatch.setattr(worktree_shared, "yaml", None)
        path = tmp_path / "shared-settings.yaml"
        path.write_text(text)
        return worktree_shared._load_yaml(path)

    def test_comment_after_bool(self, tmp_path, monkeypatch):
        data = self._write_and_load(
            tmp_path, monkeypatch, "git:\n  always_stack: true  # comment here\n"
        )
        assert data["git"]["always_stack"] is True

    def test_comment_after_false_bool(self, tmp_path, monkeypatch):
        data = self._write_and_load(
            tmp_path, monkeypatch, "git:\n  always_stack: false  # comment here\n"
        )
        assert data["git"]["always_stack"] is False

    def test_quoted_scalar(self, tmp_path, monkeypatch):
        data = self._write_and_load(
            tmp_path, monkeypatch, 'git:\n  stack_root: "develop"\n'
        )
        assert data["git"]["stack_root"] == "develop"

    def test_unknown_scalar_for_boolean_key_coerces_false(self, tmp_path, monkeypatch):
        data = self._write_and_load(
            tmp_path, monkeypatch, "git:\n  always_stack: maybe\n"
        )
        assert data["git"]["always_stack"] is False

    def test_non_boolean_key_scalar_passthrough(self, tmp_path, monkeypatch):
        data = self._write_and_load(
            tmp_path, monkeypatch, "git:\n  stack_root: develop\n"
        )
        assert data["git"]["stack_root"] == "develop"

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(worktree_shared, "yaml", None)
        data = worktree_shared._load_yaml(tmp_path / "does-not-exist.yaml")
        assert data == {}
