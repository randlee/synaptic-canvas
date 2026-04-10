import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "test-packages" / "fixtures" / "sc-ai-cli"
GENERATED_ROOT = REPO_ROOT / "test-packages" / "generated" / "sc-ai-cli"


def _load_fixture() -> dict:
    with open(FIXTURE_ROOT / "fixture.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _render_templates(template_root: Path, output_root: Path, vars_file: Path) -> None:
    for template in sorted(template_root.rglob("*.j2")):
        rel = template.relative_to(template_root)
        output_path = output_root / rel.with_suffix("")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "sc-compose",
            "render",
            rel.as_posix(),
            "--root",
            str(template_root),
            "--var-file",
            str(vars_file),
            "--output",
            str(output_path),
            "--write",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise AssertionError(
                f"sc-compose render failed for {template}:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )


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


def _prepare_case(case: dict) -> tuple[Path, dict]:
    output_root = GENERATED_ROOT / case["id"]
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    vars_file = FIXTURE_ROOT / case["vars_file"]
    with open(vars_file, encoding="utf-8") as handle:
        vars_data = yaml.safe_load(handle)

    cli_template_root = REPO_ROOT / case["cli_template_root"]
    simulator_template_root = REPO_ROOT / case["simulator_template_root"]

    _render_templates(cli_template_root, output_root, vars_file)
    _render_templates(simulator_template_root, output_root, vars_file)
    return output_root, vars_data


def _verify_rust(case: dict) -> None:
    output_root, vars_data = _prepare_case(case)
    state_file = output_root / vars_data["state_file_name"]
    binary_name = vars_data["package_name"]

    _run(["cargo", "build", "--quiet"], cwd=output_root)
    binary = output_root / "target" / "debug" / binary_name
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


def _verify_go(case: dict) -> None:
    output_root, vars_data = _prepare_case(case)
    state_file = output_root / vars_data["state_file_name"]
    binary = output_root / vars_data["binary_name"]

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


def test_sc_ai_cli_templates_render_build_and_run() -> None:
    fixture = _load_fixture()
    verifiers = {
        "rust": _verify_rust,
        "dotnet": _verify_dotnet,
        "go": _verify_go,
    }

    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(verifiers[case["language"]], case): case["id"]
            for case in fixture["cases"]
        }

        for future in as_completed(future_map):
            case_id = future_map[future]
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - failure path
                failures.append(f"{case_id}: {exc}")

    assert not failures, "\n\n".join(failures)
