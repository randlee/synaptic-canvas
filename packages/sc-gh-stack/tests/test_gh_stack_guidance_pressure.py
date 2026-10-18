"""Exercise generated and documented handoffs without executing outward writes."""
import ast
import json
from pathlib import Path
import re
import shlex
from typing import Any, Dict

import pytest


PACKAGES = Path(__file__).resolve().parents[2]
WORKTREE = PACKAGES / "sc-git-worktree"


def active_commands(commands):
    return [command for command in commands if not command.lstrip().startswith("#")]


@pytest.mark.parametrize("position,installed", [(p, i) for p in ("top", "insert") for i in (False, True)])
def test_generated_handoff_avoids_acquisition_ritual_but_preserves_stack_strategy(tmp_path, position, installed):
    if installed:
        scripts = tmp_path / ".claude/scripts"
        scripts.mkdir(parents=True)
        (scripts / "gh_stack_chain_check.py").touch()
    # Execute the actual pure handoff generator, without importing the companion
    # command's Pydantic entrypoint into sc-gh-stack's stdlib-only CI environment.
    source = WORKTREE / "scripts/worktree_create.py"
    function = next(node for node in ast.parse(source.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "build_stack_handoff")
    namespace = {"Path": Path, "shlex": shlex, "Any": Any, "Dict": Dict}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
    info = {"trunk": "develop", "parent": "layer-120", "parent_sha": "a" * 40,
            "above": "layer-121" if position == "insert" else None, "position": position}
    handoff = namespace["build_stack_handoff"]("fix-top", "fix findings", tmp_path / "worktree", info, tmp_path)
    commands = active_commands(handoff["stack_writer"]["commands"])
    # Routine creation emits necessary writes, not additional read/checkouts or
    # all-worktree recovery. Conditional missing-evidence guidance stays comments.
    assert not any("gh stack checkout" in command or "/sc-gh-stack-view" in command for command in commands)
    assert not any("gh pr view" in command or "gh stack view" in command for command in commands)
    assert not any("gh stack unstack --local" in command for command in commands)
    assert not any("gh " in command for command in handoff["writer"]["commands"])
    assert any(command.startswith("gh pr create --base layer-120 --head fix-top") for command in commands)
    assert any(command.startswith("gh stack link --base develop") for command in commands)
    instructions = handoff["stack_writer"]["commands"]
    assert any("record the returned numeric stack number from link" in command for command in instructions)
    fallback = [command for command in instructions if "/sc-gh-stack-view" in command]
    assert len(fallback) == 1
    assert "only if complete composition/base evidence is missing" in fallback[0]
    assert "/sc-gh-stack-view --stack <returned-stack#> --refresh" in fallback[0]
    assert "--stack fix-top" not in fallback[0], "new branch may have no local catalog for resolution"
    checks = [command for command in commands if "gh_stack_chain_check.py" in command]
    assert len(checks) == int(installed)
    if position == "insert":
        assert any("merge --no-ff origin/fix-top" in command for command in commands)
        assert any(command.startswith("gh stack unstack <stack#>") for command in commands)
        assert "gh pr edit <pr# of layer-121> --base fix-top" in commands
        assert not any("rebase" in command or "force" in command for command in commands)
    else:
        assert any(command.startswith("gh stack link <stack#> <pr# of fix-top>") for command in commands)
        assert not any(command.startswith("gh stack unstack") for command in commands)


def test_documented_agent_handoff_has_no_extra_read_commands():
    agent = (WORKTREE / "agents/sc-git-worktree-create-stacked.md").read_text()
    example = agent.split("**Success example (top):**", 1)[1]
    example = json.loads(re.search(r"```json\n(.*?)\n```", example, re.S).group(1))
    commands = active_commands(example["data"]["stack_handoff"]["stack_writer"]["commands"])
    assert not any("checkout" in command or "/sc-gh-stack-view" in command for command in commands)
    assert any(command.startswith("gh pr create --base sprint-6 --head sprint-7") for command in commands)
    assert any(command.startswith("gh stack link <stack#>") for command in commands)
    assert any(command.startswith("gh stack link --base develop") for command in commands)
    instructions = example["data"]["stack_handoff"]["stack_writer"]["commands"]
    assert any("record the returned numeric stack number" in command for command in instructions)
    assert any("--stack <returned-stack#> --refresh" in command for command in instructions)


def test_worktree_skill_template_remains_in_sync():
    skill = WORKTREE / "skills/sc-git-worktree"
    def stack_guidance(path):
        return path.read_text().split("## Stack Layers (gh-stack)", 1)[1].split("## Standards and Paths", 1)[0]
    # Template intentionally differs in repository-name interpolation elsewhere.
    assert stack_guidance(skill / "SKILL.md") == stack_guidance(skill / "SKILL.md.local.j2")
