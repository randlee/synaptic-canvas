"""Render the sc-rust quality-mgr assignment templates with sc-compose and check the JSON."""

import importlib.metadata
import json
from pathlib import Path

import pytest

sc_compose = pytest.importorskip("sc_compose")
# Earlier sc-compose releases do not JSON-escape variables in `format: json` templates.
if tuple(int(p) for p in importlib.metadata.version("sc-compose").split(".")[:2]) < (1, 7):
    pytest.skip("needs sc-compose 1.7.0 or newer", allow_module_level=True)

TEMPLATES = (
    Path(__file__).resolve().parent.parent
    / "packages" / "sc-rust" / "assets" / "sc-rust" / "quality-mgr" / "templates"
)
MODES = ("doc_review", "sprint_review", "phase_end")
# A path with a quote and a backslash proves values are JSON-escaped, not pasted between quotes.
WORKTREE = 'C:\\work "tree"'


def render(name: str, variables: dict) -> str:
    request = sc_compose.ComposeRequest(
        str(TEMPLATES),
        sc_compose.ComposeMode.file(str(TEMPLATES / name)),
        vars_input=variables,
        policy=sc_compose.ComposePolicy(strict_undeclared_variables=True),
    )
    return sc_compose.compose_file(request).rendered_text


def base(mode: str, **extra) -> dict:
    return {"review_mode": mode, "worktree_path": WORKTREE, "review_targets": ["src/", "Cargo.toml"], **extra}


@pytest.mark.parametrize("mode", MODES)
def test_rust_qa_assignment_is_valid_json(mode):
    data = json.loads(render("rust-qa-assignment.json.j2", base(mode)))
    assert data["worktree_path"] == WORKTREE
    assert data["review_mode"] == mode
    assert data["review_targets"] == ["src/", "Cargo.toml"]
    assert data["run_checks"]["coverage"] is (mode == "phase_end")
    assert data["artifact_commands"] == ""


@pytest.mark.parametrize("name", ["rust-best-practices-assignment.json.j2", "rust-service-hardening-assignment.json.j2"])
@pytest.mark.parametrize("mode", MODES)
def test_open_review_is_not_scope_locked(name, mode):
    data = json.loads(render(name, base(mode, qa_round=1)))
    assert data["worktree_path"] == WORKTREE
    assert data["carry_forward_findings"] == []
    assert data["findings_scope_locked"] is False


@pytest.mark.parametrize(
    ("name", "ids"),
    [("rust-best-practices-assignment.json.j2", ["RBP-004-a"]), ("rust-service-hardening-assignment.json.j2", ["RSH-002-b"])],
)
def test_fix_round_with_carried_ids_is_scope_locked(name, ids):
    data = json.loads(render(name, base("sprint_review", qa_round=2, carry_forward_findings_json=json.dumps(ids))))
    assert data["carry_forward_findings"] == ids
    assert data["findings_scope_locked"] is True


@pytest.mark.parametrize("name", ["rust-best-practices-assignment.json.j2", "rust-service-hardening-assignment.json.j2"])
@pytest.mark.parametrize("carried", [None, "[]", "[\n]", "[\t\r\n]", "null"])
def test_fix_round_without_carried_ids_refuses_to_render(name, carried):
    # The template emits a marker ahead of the JSON; the sc-compose CLI then refuses the
    # render (ERR_RENDER_JSON_MALFORMED) and any JSON consumer rejects it.
    extra = {} if carried is None else {"carry_forward_findings_json": carried}
    text = render(name, base("sprint_review", qa_round=2, **extra))
    assert text.startswith("FIX_ROUND_SCOPE_LOCK_REQUIRED")
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)


def test_best_practices_defaults_follow_review_mode():
    sprint = json.loads(render("rust-best-practices-assignment.json.j2", base("sprint_review", qa_round=1)))
    phase_end = json.loads(render("rust-best-practices-assignment.json.j2", base("phase_end", qa_round=1)))
    assert sprint["practice_mode"] == "selected"
    assert sprint["practice_ids"] == ["RBP-001", "RBP-004", "RBP-006", "RBP-007"]
    assert phase_end["practice_mode"] == "all"
    assert phase_end["practice_ids"] == []
