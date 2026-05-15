import ast
import importlib.util
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = (
    REPO_ROOT
    / "packages"
    / "sc-just"
    / "skills"
    / "setting-up-just"
    / "assets"
    / "templates"
)


def _copy_template(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(TEMPLATE_ROOT / name, target)
    return target


def _run_script(script: Path, cwd: Path, *args: str, expected_returncode: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == expected_returncode, (
        f"script failed: {script}\n"
        f"args: {args}\n"
        f"cwd: {cwd}\n"
        f"expected: {expected_returncode}\n"
        f"actual: {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    return completed


def _load_module(module_name: str, module_path: Path):
    sys.path.insert(0, str(module_path.parent))
    try:
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_sc_just_template_python_files_have_version_marker_and_parse() -> None:
    python_files = sorted(TEMPLATE_ROOT.rglob("*.py"))
    assert python_files
    for path in python_files:
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        assert lines[1] == "# sc-just-template-version: 0.1.0"
        ast.parse(raw, filename=str(path))


def test_minimal_task_runner_reports_unconfigured(tmp_path, capsys) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    module = _load_module("minimal_task_runner", template_root / ".just" / "task_runner.py")
    result = module.run_steps("lint", [])
    assert result == 2
    captured = capsys.readouterr()
    assert "lint is not configured" in captured.out


def test_minimal_task_runner_propagates_failure(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    module = _load_module("minimal_task_runner", template_root / ".just" / "task_runner.py")
    result = module.run_steps(
        "lint",
        [
            [sys.executable, "-c", "import sys; sys.exit(0)"],
            [sys.executable, "-c", "import sys; sys.exit(4)"],
        ],
    )
    assert result == 4


def test_minimal_print_help_reads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    config = template_root / ".just" / "config.toml"
    config.write_text(
        textwrap.dedent(
            """
            template_version = "0.1.0"
            [repo]
            name = "demo-repo"
            [help]
            usage = "just <recipe>"
            [[help.sections]]
            title = "General"
            [[help.sections.recipes]]
            name = "help"
            description = "Show custom help."
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    completed = _run_script(template_root / ".just" / "print_help.py", template_root)
    assert "demo-repo task runner" in completed.stdout
    assert "Show custom help." in completed.stdout


def test_minimal_run_fmt_unknown_mode(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    completed = _run_script(
        template_root / ".just" / "run_fmt.py",
        template_root,
        "invalid",
        expected_returncode=2,
    )
    assert "unknown fmt mode" in completed.stderr


def test_minimal_run_lint_uses_configured_steps(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    marker = template_root / "lint.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.steps]
            check = []
            write = []
            apply = []
            [lint]
            steps = [[{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('ok', encoding='utf-8')"]]
            [test]
            steps = []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(template_root / ".just" / "run_lint.py", template_root)
    assert marker.read_text(encoding="utf-8") == "ok"


def test_minimal_run_tests_missing_config_fails(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "minimal")
    (template_root / ".just" / "config.toml").unlink()
    completed = _run_script(
        template_root / ".just" / "run_tests.py",
        template_root,
        expected_returncode=2,
    )
    assert "missing config file" in completed.stderr


def test_python_task_runner_loads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    module = _load_module("python_task_runner", template_root / ".just" / "task_runner.py")
    config = module.load_config()
    assert config["fmt"]["default_mode"] == "check"
    assert config["lint"]["steps"]


def test_python_print_help_reads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    completed = _run_script(template_root / ".just" / "print_help.py", template_root)
    assert "Run Python lint checks." in completed.stdout
    assert "Run Python tests." in completed.stdout


def test_python_run_fmt_runs_configured_mode(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    marker = template_root / "fmt.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.steps]
            check = [[{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('fmt', encoding='utf-8')"]]
            write = []
            apply = []
            [lint]
            steps = []
            [test]
            steps = []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(template_root / ".just" / "run_fmt.py", template_root)
    assert marker.read_text(encoding="utf-8") == "fmt"


def test_python_run_fmt_unknown_mode(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    completed = _run_script(
        template_root / ".just" / "run_fmt.py",
        template_root,
        "bad",
        expected_returncode=2,
    )
    assert "unknown fmt mode" in completed.stderr


def test_python_run_lint_uses_configured_steps(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    marker = template_root / "lint.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.steps]
            check = []
            write = []
            apply = []
            [lint]
            steps = [[{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('lint', encoding='utf-8')"]]
            [test]
            steps = []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(template_root / ".just" / "run_lint.py", template_root)
    assert marker.read_text(encoding="utf-8") == "lint"


def test_python_run_tests_uses_configured_steps(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    marker = template_root / "test.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.steps]
            check = []
            write = []
            apply = []
            [lint]
            steps = []
            [test]
            steps = [[{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('test', encoding='utf-8')"]]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(template_root / ".just" / "run_tests.py", template_root)
    assert marker.read_text(encoding="utf-8") == "test"


def test_python_task_runner_missing_config_raises(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "python")
    module = _load_module("python_task_runner_missing", template_root / ".just" / "task_runner.py")
    (template_root / ".just" / "config.toml").unlink()
    try:
        module.load_config()
    except FileNotFoundError as exc:
        assert "missing config file" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_go_print_help_reads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "go")
    completed = _run_script(template_root / ".just" / "print_help.py", template_root)
    assert "Go task runner" in completed.stdout
    assert "Run go build ./... from repo root." in completed.stdout
    assert "Run go test ./... from repo root." in completed.stdout


def test_go_print_help_missing_config_fails(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "go")
    (template_root / ".just" / "config.toml").unlink()
    completed = _run_script(
        template_root / ".just" / "print_help.py",
        template_root,
        expected_returncode=2,
    )
    assert "missing config file" in completed.stdout


def test_rust_print_help_reads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "rust")
    completed = _run_script(template_root / ".just" / "print_help.py", template_root)
    assert "Build the Rust workspace." in completed.stdout
    assert "Run only clippy with warnings denied." in completed.stdout


def test_rust_run_fmt_unknown_mode(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "rust")
    completed = _run_script(
        template_root / ".just" / "run_fmt.py",
        template_root,
        "bad",
        expected_returncode=2,
    )
    assert "unknown fmt mode" in completed.stderr


def test_rust_run_fmt_uses_configured_commands(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "rust")
    marker = template_root / "fmt.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.commands]
            check = [{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('fmt', encoding='utf-8')"]
            write = [{sys.executable!r}, "-c", "import sys; sys.exit(0)"]
            apply = [{sys.executable!r}, "-c", "import sys; sys.exit(0)"]
            [lint]
            default_target = "all"
            [lint.targets]
            all = []
            fmt = []
            clippy = []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(template_root / ".just" / "run_fmt.py", template_root)
    assert marker.read_text(encoding="utf-8") == "fmt"


def test_rust_run_lint_unknown_target(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "rust")
    completed = _run_script(
        template_root / ".just" / "run_lint.py",
        template_root,
        "bad",
        expected_returncode=2,
    )
    assert "unknown lint target" in completed.stderr


def test_rust_run_lint_stops_on_first_failure(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "rust")
    marker = template_root / "lint.txt"
    (template_root / ".just" / "config.toml").write_text(
        textwrap.dedent(
            f"""
            template_version = "0.1.0"
            [repo]
            name = ""
            [help]
            usage = "just <recipe>"
            [fmt]
            default_mode = "check"
            [fmt.commands]
            check = [{sys.executable!r}, "-c", "import sys; sys.exit(0)"]
            write = [{sys.executable!r}, "-c", "import sys; sys.exit(0)"]
            apply = [{sys.executable!r}, "-c", "import sys; sys.exit(0)"]
            [lint]
            default_target = "all"
            [lint.targets]
            all = [
              [{sys.executable!r}, "-c", "import sys; sys.exit(3)"],
              [{sys.executable!r}, "-c", "from pathlib import Path; Path({str(marker)!r}).write_text('late', encoding='utf-8')"],
            ]
            fmt = []
            clippy = []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    _run_script(
        template_root / ".just" / "run_lint.py",
        template_root,
        expected_returncode=3,
    )
    assert not marker.exists()


def test_dotnet_print_help_reads_config(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "dotnet")
    completed = _run_script(template_root / ".just" / "print_help.py", template_root)
    assert ".NET task runner" in completed.stdout
    assert "Run dotnet build from repo root." in completed.stdout
    assert "Run dotnet test from repo root." in completed.stdout


def test_dotnet_print_help_missing_config_fails(tmp_path) -> None:
    template_root = _copy_template(tmp_path, "dotnet")
    (template_root / ".just" / "config.toml").unlink()
    completed = _run_script(
        template_root / ".just" / "print_help.py",
        template_root,
        expected_returncode=2,
    )
    assert "missing config file" in completed.stdout
