import json
import shutil
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, StrictUndefined
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "test-packages" / "fixtures" / "sc-ai-cli"
GENERATED_ROOT = REPO_ROOT / "test-packages" / "generated" / "sc-ai-cli"


def _platform_binary(path: Path) -> Path:
    if sys.platform == "win32" and path.suffix != ".exe":
        return path.with_suffix(".exe")
    return path


def _load_fixture() -> dict:
    with open(FIXTURE_ROOT / "fixture.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _declared_template_keys(template: Path) -> set[str]:
    data, _ = _parse_template(template)
    required = set(data.get("required_variables", []) or [])
    defaults = set((data.get("defaults") or {}).keys())
    return required | defaults


def _parse_template(template: Path) -> tuple[dict, str]:
    raw = template.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return {}, raw

    _, frontmatter, body = raw.split("---", 2)
    data = yaml.safe_load(frontmatter) or {}
    return data, body.lstrip("\n")


def _render_templates(template_root: Path, output_root: Path, vars_data: dict) -> None:
    environment = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    for template in sorted(template_root.rglob("*.j2")):
        rel = template.relative_to(template_root)
        output_path = output_root / rel.with_suffix("")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter, body = _parse_template(template)
        filtered_vars = dict(frontmatter.get("defaults") or {})
        filtered_vars.update({key: value for key, value in vars_data.items() if key in _declared_template_keys(template)})
        try:
            rendered = environment.from_string(body).render(**filtered_vars)
        except Exception as exc:
            raise AssertionError(f"Template render failed for {template}: {exc}") from exc

        output_path.write_text(rendered, encoding="utf-8")


def _run(command: list[str], cwd: Path, expected_returncode: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != expected_returncode:
        raise AssertionError(
            f"Command failed: {' '.join(command)}\n"
            f"cwd: {cwd}\n"
            f"expected return code: {expected_returncode}\n"
            f"actual return code: {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )
    return completed


def _json_from_output(completed: subprocess.CompletedProcess[str]) -> dict:
    raw = completed.stdout.strip() or completed.stderr.strip()
    return json.loads(raw)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _assert_simulator_controls(
    command_prefix: list[str],
    cwd: Path,
    state_file: Path,
    get_command_name: str,
    set_command_name: str,
) -> None:
    controls_file = Path(f"{state_file}.controls.json")

    _write_json(controls_file, {"fail_writes": True})
    backend_failure = _run(
        [*command_prefix, "--json", "--state-file", str(state_file), set_command_name, "--mode", "active"],
        cwd=cwd,
        expected_returncode=2,
    )
    backend_json = _json_from_output(backend_failure)
    assert backend_json["ok"] is False
    assert backend_json["error"]["code"] == "backend.unavailable"

    _write_json(controls_file, {"fail_reads": True})
    read_failure = _run(
        [*command_prefix, "--json", "--state-file", str(state_file), get_command_name],
        cwd=cwd,
        expected_returncode=2,
    )
    read_json = _json_from_output(read_failure)
    assert read_json["ok"] is False
    assert read_json["error"]["code"] == "backend.unavailable"

    _write_json(controls_file, {"forced_status": "degraded"})
    degraded_result = _run(
        [*command_prefix, "--json", "--state-file", str(state_file), get_command_name],
        cwd=cwd,
    )
    degraded_json = _json_from_output(degraded_result)
    assert degraded_json["ok"] is True
    assert degraded_json["data"]["status"] == "degraded"

    controls_file.unlink(missing_ok=True)


def _prepare_case(case: dict) -> tuple[Path, dict]:
    output_root = GENERATED_ROOT / case["id"]
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    with open(FIXTURE_ROOT / case["vars_file"], encoding="utf-8") as handle:
        vars_data = yaml.safe_load(handle)

    cli_template_root = REPO_ROOT / case["cli_template_root"]
    simulator_template_root = REPO_ROOT / case["simulator_template_root"]

    _render_templates(cli_template_root, output_root, vars_data)
    _render_templates(simulator_template_root, output_root, vars_data)
    return output_root, vars_data


def _verify_rust(case: dict) -> None:
    output_root, vars_data = _prepare_case(case)
    state_file = output_root / vars_data["state_file_name"]
    binary_name = vars_data["package_name"]

    _run(["cargo", "build", "--quiet"], cwd=output_root)
    binary = _platform_binary(output_root / "target" / "debug" / binary_name)
    assert binary.exists(), f"Expected Rust binary at {binary}"

    set_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "active"],
        cwd=output_root,
    )
    set_json = _json_from_output(set_result)
    assert set_json["ok"] is True
    assert set_json["data"]["applied_mode"] == "active"

    get_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["get_command_name"]],
        cwd=output_root,
    )
    get_json = _json_from_output(get_result)
    assert get_json["ok"] is True
    assert get_json["data"]["current_mode"] == "active"

    invalid_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    invalid_json = _json_from_output(invalid_result)
    assert invalid_json["ok"] is False
    assert invalid_json["error"]["code"] == "validation.invalid_mode"

    parse_result = _run(
        [str(binary), "--json"],
        cwd=output_root,
        expected_returncode=2,
    )
    parse_json = _json_from_output(parse_result)
    assert parse_json["ok"] is False
    assert parse_json["error"]["code"] == "usage.parse_error"

    extra_arg_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["get_command_name"], "unexpected-token"],
        cwd=output_root,
        expected_returncode=2,
    )
    extra_arg_json = _json_from_output(extra_arg_result)
    assert extra_arg_json["ok"] is False
    assert extra_arg_json["error"]["code"] == "usage.parse_error"

    human_error = _run(
        [str(binary), "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    assert "hint:" in human_error.stderr
    assert "mode" in human_error.stderr.lower()

    _assert_simulator_controls(
        [str(binary)],
        output_root,
        state_file,
        vars_data["get_command_name"],
        vars_data["set_command_name"],
    )


def _verify_dotnet(case: dict) -> None:
    output_root, vars_data = _prepare_case(case)
    state_file = output_root / vars_data["state_file_name"]

    _run(["dotnet", "build", "-nologo"], cwd=output_root)

    set_result = _run(
        ["dotnet", "run", "--no-build", "--", "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "active"],
        cwd=output_root,
    )
    set_json = _json_from_output(set_result)
    assert set_json["ok"] is True
    assert set_json["data"]["applied_mode"] == "active"

    get_result = _run(
        ["dotnet", "run", "--no-build", "--", "--json", "--state-file", str(state_file), vars_data["get_command_name"]],
        cwd=output_root,
    )
    get_json = _json_from_output(get_result)
    assert get_json["ok"] is True
    assert get_json["data"]["current_mode"] == "active"

    invalid_result = _run(
        ["dotnet", "run", "--no-build", "--", "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    invalid_json = _json_from_output(invalid_result)
    assert invalid_json["ok"] is False
    assert invalid_json["error"]["code"] == "validation.invalid_mode"

    parse_result = _run(
        ["dotnet", "run", "--no-build", "--", "--json"],
        cwd=output_root,
        expected_returncode=2,
    )
    parse_json = _json_from_output(parse_result)
    assert parse_json["ok"] is False
    assert parse_json["error"]["code"].startswith("usage.")

    extra_arg_result = _run(
        ["dotnet", "run", "--no-build", "--", "--json", "--state-file", str(state_file), vars_data["get_command_name"], "unexpected-token"],
        cwd=output_root,
        expected_returncode=2,
    )
    extra_arg_json = _json_from_output(extra_arg_result)
    assert extra_arg_json["ok"] is False
    assert extra_arg_json["error"]["code"].startswith("usage.")

    human_error = _run(
        ["dotnet", "run", "--no-build", "--", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    assert "hint:" in human_error.stderr
    assert "mode" in human_error.stderr.lower()

    _assert_simulator_controls(
        ["dotnet", "run", "--no-build", "--"],
        output_root,
        state_file,
        vars_data["get_command_name"],
        vars_data["set_command_name"],
    )


def _verify_go(case: dict) -> None:
    output_root, vars_data = _prepare_case(case)
    state_file = output_root / vars_data["state_file_name"]
    binary = _platform_binary(output_root / vars_data["binary_name"])

    _run(["go", "build", "-o", str(binary), "."], cwd=output_root)
    assert binary.exists(), f"Expected Go binary at {binary}"

    set_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "active"],
        cwd=output_root,
    )
    set_json = _json_from_output(set_result)
    assert set_json["ok"] is True
    assert set_json["data"]["applied_mode"] == "active"

    get_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["get_command_name"]],
        cwd=output_root,
    )
    get_json = _json_from_output(get_result)
    assert get_json["ok"] is True
    assert get_json["data"]["current_mode"] == "active"

    invalid_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    invalid_json = _json_from_output(invalid_result)
    assert invalid_json["ok"] is False
    assert invalid_json["error"]["code"] == "validation.invalid_mode"

    parse_result = _run(
        [str(binary), "--json"],
        cwd=output_root,
        expected_returncode=2,
    )
    parse_json = _json_from_output(parse_result)
    assert parse_json["ok"] is False
    assert parse_json["error"]["code"] == "usage.missing_command"

    extra_arg_result = _run(
        [str(binary), "--json", "--state-file", str(state_file), vars_data["get_command_name"], "unexpected-token"],
        cwd=output_root,
        expected_returncode=2,
    )
    extra_arg_json = _json_from_output(extra_arg_result)
    assert extra_arg_json["ok"] is False
    assert extra_arg_json["error"]["code"] == "usage.parse_error"

    human_error = _run(
        [str(binary), "--state-file", str(state_file), vars_data["set_command_name"], "--mode", "broken"],
        cwd=output_root,
        expected_returncode=2,
    )
    assert "hint:" in human_error.stderr
    assert "mode" in human_error.stderr.lower()

    _assert_simulator_controls(
        [str(binary)],
        output_root,
        state_file,
        vars_data["get_command_name"],
        vars_data["set_command_name"],
    )


def test_sc_ai_cli_templates_render_build_and_run() -> None:
    fixture = _load_fixture()
    verifiers = {
        "rust": _verify_rust,
        "dotnet": _verify_dotnet,
        "go": _verify_go,
    }

    failures: list[str] = []

    for case in fixture["cases"]:
        case_id = case["id"]
        try:
            verifiers[case["language"]](case)
        except Exception as exc:  # pragma: no cover - failure path
            failures.append(f"{case_id}: {exc}")

    assert not failures, "\n\n".join(failures)
