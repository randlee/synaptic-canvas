"""Tests for the need-based stacking guard in worktree_create.py.

Rule under test (skills/sc-git-worktree/references/gh-stack-support.md, rule 5):
a worktree must be stacked iff the base branch requires it.

- Base protected OR merged into trunk -> flat create proceeds exactly as today
  (zero behavior change for the common path).
- Base neither protected nor merged into trunk -> the new work depends on
  unmerged work, so the create script REFUSES a flat create with
  `CREATE.NEEDS_STACK`, routing toward a stack worktree (or the existing
  tracked stack's worktree, if the base already carries gh-stack tracking).
- Explicit `flat: true` bypasses the refusal entirely.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_create import CreateInput, create_worktree_main
from envelope import ErrorCodes


# =============================================================================
# Real-git fixtures
# =============================================================================


def _run(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal real git repo with one commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "-b", "main"], cwd=repo)
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
# 1. Common path: base is protected/trunk -> proceeds
# =============================================================================


class TestFlatCreateOffProtectedBase:
    def test_create_off_protected_branch_proceeds(self, tmp_path):
        repo = _init_repo(tmp_path)
        input_data = _make_input(repo, tmp_path, branch="feature/off-main", base="main")

        envelope = create_worktree_main(input_data)

        assert envelope.success is True
        assert envelope.data["branch"] == "feature/off-main"
        assert envelope.data["base"] == "main"
        worktree_path = Path(envelope.data["path"])
        assert worktree_path.exists()

        branch_list = _run(["branch", "--list", "feature/off-main"], cwd=repo).stdout
        assert "feature/off-main" in branch_list


# =============================================================================
# 2. Base is merged into trunk (but not itself protected) -> proceeds
# =============================================================================


class TestFlatCreateOffMergedBase:
    def test_create_off_merged_feature_branch_proceeds(self, tmp_path):
        repo = _init_repo(tmp_path)
        _make_merged_branch(repo, "feature/merged")

        input_data = _make_input(repo, tmp_path, branch="feature/child-of-merged", base="feature/merged")

        envelope = create_worktree_main(input_data)

        assert envelope.success is True
        worktree_path = Path(envelope.data["path"])
        assert worktree_path.exists()

        branch_list = _run(["branch", "--list", "feature/child-of-merged"], cwd=repo).stdout
        assert "feature/child-of-merged" in branch_list


# =============================================================================
# 3. Base is unmerged and untracked -> refused with CREATE.NEEDS_STACK
# =============================================================================


class TestRefusesFlatCreateOffUnmergedBase:
    def test_create_off_unmerged_branch_is_refused(self, tmp_path):
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged")

        new_branch = "feature/child-of-unmerged"
        input_data = _make_input(repo, tmp_path, branch=new_branch, base="feature/unmerged")

        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.CREATE_NEEDS_STACK

        # No worktree or branch may have been created.
        worktree_path = tmp_path / "wt-base" / new_branch
        assert not worktree_path.exists()
        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch not in branch_list

        data = envelope.data
        assert data["base"] == "feature/unmerged"
        assert data["base_merged"] is False
        assert data["base_protected"] is False
        assert data["gh_stack_tracked"] is None  # base has no worktree at all
        assert "suggested_worktree_path" in data


# =============================================================================
# 4. Base is unmerged AND checked out in a gh-stack-tracked worktree
# =============================================================================


class TestRefusalRoutesToTrackedStackWorktree:
    def test_refusal_names_tracked_stack_worktree(self, tmp_path):
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged-tracked")

        stack_wt_path = tmp_path / "stack-wt"
        _run(["worktree", "add", str(stack_wt_path), "feature/unmerged-tracked"], cwd=repo)
        _mark_gh_stack(stack_wt_path)

        new_branch = "feature/child-of-tracked"
        input_data = _make_input(repo, tmp_path, branch=new_branch, base="feature/unmerged-tracked")

        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        assert envelope.error.code == ErrorCodes.CREATE_NEEDS_STACK

        data = envelope.data
        assert data["gh_stack_tracked"] is True
        assert data["suggested_worktree_path"] == str(stack_wt_path)
        assert str(stack_wt_path) in envelope.error.suggested_action
        assert "do not create a separate worktree" in envelope.error.suggested_action

        # Still no new worktree/branch created.
        worktree_path = tmp_path / "wt-base" / new_branch
        assert not worktree_path.exists()
        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch not in branch_list


# =============================================================================
# 5. flat: true bypasses the refusal
# =============================================================================


class TestFlatOverrideBypassesRefusal:
    def test_flat_true_proceeds_despite_unmerged_base(self, tmp_path):
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged-flat")

        new_branch = "feature/child-flat"
        input_data = _make_input(
            repo, tmp_path, branch=new_branch, base="feature/unmerged-flat", flat=True
        )

        envelope = create_worktree_main(input_data)

        assert envelope.success is True
        worktree_path = Path(envelope.data["path"])
        assert worktree_path.exists()

        branch_list = _run(["branch", "--list", new_branch], cwd=repo).stdout
        assert new_branch in branch_list


# =============================================================================
# 6. Envelope shape for the refusal
# =============================================================================


class TestRefusalEnvelopeShape:
    def test_error_envelope_has_expected_shape(self, tmp_path):
        repo = _init_repo(tmp_path)
        _make_unmerged_branch(repo, "feature/unmerged-shape")

        input_data = _make_input(
            repo, tmp_path, branch="feature/child-shape", base="feature/unmerged-shape"
        )

        envelope = create_worktree_main(input_data)

        assert envelope.success is False
        error = envelope.error
        assert error is not None
        assert error.code == ErrorCodes.CREATE_NEEDS_STACK
        assert isinstance(error.message, str) and error.message
        assert error.recoverable is True
        assert isinstance(error.suggested_action, str) and error.suggested_action

        data = envelope.data
        for key in (
            "base",
            "base_merged",
            "base_protected",
            "gh_stack_tracked",
            "suggested_worktree_path",
        ):
            assert key in data


class TestNoProtectedBranchConfigFailsOpen:
    """NEW-4 regression: repos with no .sc/shared-settings.yaml and no gitflow
    config must keep the historical flat-create behavior — the guard fails
    OPEN (skipped), it must never turn a plain create into an error."""

    def test_create_off_main_without_any_config_proceeds(self, tmp_path):
        repo = _init_repo(tmp_path)
        # No protected_branches input, no .sc/ config, no gitflow config:
        # the canonical invocation shape used by existing prompts.
        input_data = _make_input(
            repo, tmp_path, branch="feature/x", base="main",
            protected_branches=None,
        )

        envelope = create_worktree_main(input_data)

        assert envelope.success is True, envelope.error
        assert Path(envelope.data["path"]).exists()
