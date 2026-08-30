"""
Environment isolation for Claude Code test harness.

This module provides mechanisms to run Claude tests in isolated environments,
preventing interference from user plugins, settings, and other test sessions.

Key concepts:
- HOME override: Primary isolation mechanism - creates a temp HOME directory
  to hide all user-scoped plugins and settings
- Marketplace data: Can be optionally copied for plugin installation
- Transcript path handling: Accounts for HOME-based path transformations

Based on findings from:
- spike-1-clean-environment-configuration.md

Example usage:
    from harness.environment import isolated_claude_session

    with isolated_claude_session() as session:
        result = session.run_command(
            ["claude", "-p", "list files"],
            model="haiku",
            tools=["Bash"]
        )
        # Access trace at session.trace_path
        # Access transcript at session.transcript_path
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_TEST_HOME_PREFIX = "claude-test-"
CLAUDE_DIR = ".claude"
PLUGINS_DIR = "plugins"
MARKETPLACE_FILES = ["known_marketplaces.json"]
MARKETPLACE_DIRS = ["marketplaces"]

CODEX_DIR = ".codex"
CODEX_ZDOT_DIRNAME = ".codex-zdot"
CODEX_BIN_DIRNAME = "bin"

# Codex fast-model aliases (matches sc-launchpad's table / scripts/run-evals-local.py).
# A model resolving to a "gpt-*" id routes execution.model through `codex exec`
# instead of `claude -p`; everything else keeps using the Claude path.
MODEL_ALIASES = {"luna": "gpt-5.6-luna", "sol": "gpt-5.6-sol", "terra": "gpt-5.6-terra"}


def resolve_model(model: str) -> str:
    """Resolve a short Codex model alias (luna/sol/terra) to its full model id.

    Unknown aliases (including all Claude model names) pass through unchanged.
    """
    return MODEL_ALIASES.get(model, model)


def is_codex_model(model: str) -> bool:
    """Return True if `model` should be routed through `codex exec` rather than `claude`."""
    return resolve_model(model).startswith("gpt-")


# =============================================================================
# Helper Functions
# =============================================================================


def create_isolated_home(
    prefix: str = DEFAULT_TEST_HOME_PREFIX,
    base_dir: str | None = None,
) -> Path:
    """Create a temporary HOME directory for test isolation.

    Creates a unique temporary directory with a UUID suffix to serve as
    an isolated HOME for Claude test execution. This hides all user-scoped
    plugins and settings.

    Args:
        prefix: Prefix for the temp directory name (default: "claude-test-")
        base_dir: Base directory for temp creation (default: system temp)

    Returns:
        Path to the created isolated HOME directory

    Example:
        >>> home = create_isolated_home()
        >>> print(home)
        /tmp/claude-test-a1b2c3d4-e5f6-7890-abcd-ef1234567890
    """
    unique_id = str(uuid.uuid4())
    dir_name = f"{prefix}{unique_id}"

    if base_dir:
        isolated_home = Path(base_dir) / dir_name
        isolated_home.mkdir(parents=True, exist_ok=True)
    else:
        isolated_home = Path(tempfile.mkdtemp(prefix=prefix))

    # Create .claude directory structure
    claude_dir = isolated_home / CLAUDE_DIR
    claude_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Created isolated HOME: {isolated_home}")
    return isolated_home


def copy_marketplace_data(
    isolated_home: Path,
    source_home: Path | None = None,
) -> bool:
    """Copy marketplace registry data to isolated HOME for plugin installation.

    Plugin installation requires access to marketplace registries stored in
    ~/.claude/plugins/. This function copies the necessary files to the
    isolated HOME to enable plugin installation in tests.

    Args:
        isolated_home: The isolated HOME directory
        source_home: Source HOME to copy from (default: actual HOME)

    Returns:
        True if marketplace data was copied successfully, False otherwise

    Note:
        Required files/directories:
        - ~/.claude/plugins/known_marketplaces.json
        - ~/.claude/plugins/marketplaces/
    """
    source_home = source_home or Path.home()
    source_plugins = source_home / CLAUDE_DIR / PLUGINS_DIR
    dest_plugins = isolated_home / CLAUDE_DIR / PLUGINS_DIR

    if not source_plugins.exists():
        logger.warning(f"Source plugins directory not found: {source_plugins}")
        return False

    dest_plugins.mkdir(parents=True, exist_ok=True)

    copied_any = False

    # Copy marketplace files
    for filename in MARKETPLACE_FILES:
        source_file = source_plugins / filename
        if source_file.exists():
            dest_file = dest_plugins / filename
            shutil.copy2(source_file, dest_file)
            logger.debug(f"Copied marketplace file: {filename}")
            copied_any = True

    # Copy marketplace directories
    for dirname in MARKETPLACE_DIRS:
        source_dir = source_plugins / dirname
        if source_dir.exists() and source_dir.is_dir():
            dest_dir = dest_plugins / dirname
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
            logger.debug(f"Copied marketplace directory: {dirname}")
            copied_any = True

    return copied_any


def copy_codex_auth(isolated_home: Path, source_home: Path | None = None) -> bool:
    """Copy Codex auth/config files into isolated HOME."""
    source_home = source_home or Path.home()
    source_dir = source_home / ".codex"
    if not source_dir.exists():
        return False

    dest_dir = isolated_home / ".codex"
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied_any = False
    for name in ("auth.json",):
        src = source_dir / name
        if not src.exists():
            continue
        try:
            shutil.copy2(src, dest_dir / name)
            copied_any = True
        except Exception as exc:
            logger.warning(f"Failed to copy Codex file {src}: {exc}")

    return copied_any


def setup_codex_home(isolated_home: Path, source_home: Path | None = None) -> Path:
    """Provision CODEX_HOME inside the isolated HOME.

    CODEX_HOME is Codex's analogue of HOME: it holds config and auth.json,
    just as ~/.claude holds Claude's. Isolating it the same way HOME is
    isolated keeps Codex runs from touching (or depending on) the real
    ~/.codex, while still letting them authenticate via a copy of its
    auth.json (see copy_codex_auth).

    Args:
        isolated_home: The isolated HOME directory
        source_home: Source HOME to copy Codex auth from (default: actual HOME)

    Returns:
        Path to the CODEX_HOME directory (isolated_home/.codex), created
        whether or not auth was available to copy.
    """
    codex_home = isolated_home / CODEX_DIR
    codex_home.mkdir(parents=True, exist_ok=True)
    copy_codex_auth(isolated_home, source_home)
    return codex_home


def provision_codex_zdot(zdot_dir: Path, bin_dir: Path) -> Path:
    """Create a ZDOTDIR that forces Codex's login-shell PATH to include bin_dir.

    Codex executes shell commands via `zsh -lc` (a login shell), which
    re-sources the user's profile and rebuilds PATH -- silently defeating a
    stub-PATH set only via the subprocess environment. Pointing ZDOTDIR at a
    workspace-owned directory whose .zshenv unconditionally prepends bin_dir
    (with empty .zprofile/.zshrc, so nothing else re-clobbers PATH afterward)
    restores control over command resolution for isolated Codex runs.

    Args:
        zdot_dir: Directory to use as ZDOTDIR (created if missing)
        bin_dir: Directory to prepend to PATH inside Codex's login shell

    Returns:
        The zdot_dir path, for convenience.
    """
    zdot_dir.mkdir(parents=True, exist_ok=True)
    (zdot_dir / ".zshenv").write_text(
        f'export PATH="{bin_dir}:$PATH"\n', encoding="utf-8"
    )
    (zdot_dir / ".zprofile").write_text("", encoding="utf-8")
    (zdot_dir / ".zshrc").write_text("", encoding="utf-8")
    return zdot_dir


def write_codex_agents_md(project_path: Path) -> Path | None:
    """Write an AGENTS.md pointing Codex at installed skills, if needed.

    Codex has no Skill tool; its native instruction channel is AGENTS.md in
    the working directory, which it reads automatically on `codex exec`.
    This is the parity equivalent of Claude's Skill tool: the same skill
    content (.claude/skills/*/SKILL.md), loaded through each model's own
    idiomatic mechanism.

    Args:
        project_path: The test project directory (cwd for codex exec)

    Returns:
        Path to the written AGENTS.md, or None if it was skipped because the
        fixture already ships its own AGENTS.md, or because there are no
        installed skills to point at.
    """
    agents_path = project_path / "AGENTS.md"
    if agents_path.exists():
        logger.debug(f"AGENTS.md already present, leaving as-is: {agents_path}")
        return None

    skills = sorted((project_path / CLAUDE_DIR / "skills").glob("*/SKILL.md"))
    if not skills:
        logger.debug(f"No installed skills found under {project_path / CLAUDE_DIR / 'skills'}")
        return None

    lines = [
        "# Project skills\n",
        "Before acting, read the relevant skill and follow it:\n",
    ]
    lines += [f"- {p.relative_to(project_path)}\n" for p in skills]
    agents_path.write_text("".join(lines), encoding="utf-8")
    logger.debug(f"Wrote Codex AGENTS.md pointing at {len(skills)} skill(s): {agents_path}")
    return agents_path


def setup_test_environment(
    isolated_home: Path,
    project_path: Path,
    copy_marketplace: bool = False,
    source_home: Path | None = None,
) -> dict[str, str]:
    """Configure the test environment with HOME override.

    Sets up the environment variables needed to run Claude in an isolated
    context. The primary isolation mechanism is the HOME override.

    Args:
        isolated_home: The isolated HOME directory
        project_path: Path to the test project (where .claude/ settings are)
        copy_marketplace: Whether to copy marketplace data for plugin install
        source_home: Source HOME to copy marketplace data from

    Returns:
        Dictionary of environment variables to use for subprocess calls

    Example:
        >>> env = setup_test_environment(isolated_home, project_path)
        >>> subprocess.run(["claude", "-p", "test"], env=env)
    """
    # Start with current environment
    env = os.environ.copy()

    # Override HOME for isolation
    env["HOME"] = str(isolated_home)

    # Ensure project path is absolute
    env["SC_TEST_PROJECT"] = str(project_path.absolute())

    # Copy marketplace data if requested
    if copy_marketplace:
        copy_marketplace_data(isolated_home, source_home)

    # Provision CODEX_HOME inside the isolated HOME (copies auth if available).
    # Setting CODEX_HOME is inert for the Claude path -- Claude never reads it.
    codex_home = setup_codex_home(isolated_home, source_home)
    env["CODEX_HOME"] = str(codex_home)

    logger.debug(f"Configured test environment with HOME={isolated_home}")
    return env


def cleanup_test_environment(isolated_home: Path, force: bool = False) -> bool:
    """Remove the isolated HOME directory after test completion.

    Safely cleans up the temporary isolated HOME directory. Performs
    safety checks to prevent accidental deletion of real HOME.

    Args:
        isolated_home: The isolated HOME directory to remove
        force: Skip safety checks (use with caution)

    Returns:
        True if cleanup succeeded, False otherwise

    Raises:
        ValueError: If trying to delete what appears to be a real HOME
    """
    if not isolated_home.exists():
        logger.debug(f"Isolated HOME already removed: {isolated_home}")
        return True

    # Safety check: don't delete real HOME
    real_home = Path.home()
    if isolated_home.resolve() == real_home.resolve():
        raise ValueError(f"Refusing to delete real HOME directory: {isolated_home}")

    # Safety check: must be in temp directory or have test prefix
    is_temp = str(isolated_home).startswith(tempfile.gettempdir())
    has_prefix = DEFAULT_TEST_HOME_PREFIX in isolated_home.name

    if not force and not (is_temp or has_prefix):
        raise ValueError(
            f"Refusing to delete non-test directory: {isolated_home}. "
            "Use force=True to override."
        )

    try:
        shutil.rmtree(isolated_home)
        logger.debug(f"Cleaned up isolated HOME: {isolated_home}")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup isolated HOME: {e}")
        return False


def get_transcript_path(
    isolated_home: Path,
    project_path: Path,
    session_id: str,
) -> Path:
    """Compute the transcript path for an isolated session.

    With HOME override, transcripts are written to a transformed path:
    $HOME/.claude/projects/<encoded-project-path>/<session-id>.jsonl

    The project path is encoded by replacing '/' with '-'.

    Args:
        isolated_home: The isolated HOME directory
        project_path: Path to the test project
        session_id: The session UUID

    Returns:
        Full path to the expected transcript file

    Example:
        >>> path = get_transcript_path(
        ...     Path("/tmp/claude-test-xxx"),
        ...     Path("/Users/test/project"),
        ...     "abc-123"
        ... )
        >>> print(path)
        /tmp/claude-test-xxx/.claude/projects/-Users-test-project/abc-123.jsonl
    """
    # Encode project path (replace / with -)
    encoded_path = str(project_path.absolute()).replace("/", "-")

    # Handle leading slash encoding
    if encoded_path.startswith("-"):
        encoded_path = encoded_path  # Keep the leading dash
    else:
        encoded_path = f"-{encoded_path}"

    transcript_path = (
        isolated_home
        / CLAUDE_DIR
        / "projects"
        / encoded_path
        / f"{session_id}.jsonl"
    )

    return transcript_path


# =============================================================================
# Session Data Class
# =============================================================================


@dataclass
class IsolatedSession:
    """Represents an isolated Claude test session.

    Contains all paths and configuration for a test session running
    in an isolated environment.

    Attributes:
        isolated_home: The temporary HOME directory
        project_path: Path to the test project
        env: Environment variables for subprocess calls
        trace_path: Path to the trace.jsonl file (from hooks)
        session_id: The session UUID (populated after run)
        transcript_path: Path to session transcript (populated after run)
    """

    isolated_home: Path
    project_path: Path
    env: dict[str, str]
    trace_path: Path
    session_id: str | None = None
    transcript_path: Path | None = None
    codex_events_path: Path | None = None
    _process_result: subprocess.CompletedProcess | None = field(
        default=None, repr=False
    )

    def run_plugin_install(
        self,
        plugin_name: str,
        scope: str = "project",
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Install a plugin using the Claude CLI.

        Runs `claude plugin install <plugin_name> --scope <scope>` in the
        isolated environment. Marketplace data must be available in the
        isolated HOME for this to work.

        Args:
            plugin_name: Plugin identifier (e.g., "sc-startup@synaptic-canvas")
            scope: Installation scope ("project" or "user"), default "project"
            timeout: Timeout in seconds (default: 60)

        Returns:
            CompletedProcess with stdout, stderr, and returncode

        Example:
            >>> result = session.run_plugin_install("sc-startup@synaptic-canvas")
            >>> if result.returncode == 0:
            ...     print("Plugin installed successfully")
        """
        cmd = [
            "claude",
            "plugin",
            "install",
            plugin_name,
            "--scope",
            scope,
        ]

        logger.info(f"Installing plugin: {plugin_name} (scope={scope})")
        logger.debug(f"Plugin install command: {cmd}")

        result = subprocess.run(
            cmd,
            env=self.env,
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            logger.info(f"Successfully installed plugin: {plugin_name}")
        else:
            logger.warning(
                f"Plugin install failed for {plugin_name}: "
                f"returncode={result.returncode}, stderr={result.stderr}"
            )

        return result

    def run_command(
        self,
        prompt: str,
        model: str = "haiku",
        tools: list[str] | None = None,
        timeout: int = 120,
        additional_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run Claude CLI with a prompt in the isolated environment.

        Executes Claude with the specified prompt and options, using the
        isolated environment configured for this session.

        Args:
            prompt: The prompt to send to Claude
            model: Model to use (default: "haiku")
            tools: List of tools to allow (default: all)
            timeout: Timeout in seconds (default: 120)
            additional_args: Additional CLI arguments

        Returns:
            CompletedProcess with stdout, stderr, and returncode

        Example:
            >>> result = session.run_command("list files", tools=["Bash"])
            >>> print(result.stdout)
        """
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--setting-sources",
            "project",
            "--dangerously-skip-permissions",
        ]

        if tools:
            cmd.extend(["--tools", ",".join(tools)])

        if additional_args:
            cmd.extend(additional_args)

        logger.info(f"Running command: {' '.join(cmd[:6])}...")
        logger.debug(f"Full command: {cmd}")

        # Change to project directory for execution
        result = subprocess.run(
            cmd,
            env=self.env,
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        self._process_result = result
        logger.debug(f"Command completed with return code: {result.returncode}")

        return result

    def run_codex_command(
        self,
        prompt: str,
        model: str = "gpt-5.6-luna",
        timeout: int = 120,
        codex_bin: str = "codex",
        events_path: Path | None = None,
    ) -> subprocess.CompletedProcess:
        """Run `codex exec` with a prompt in the isolated environment.

        Parity counterpart to run_command(): same isolation (HOME/CODEX_HOME),
        same cwd/timeout contract, but drives the Codex CLI instead of Claude.
        Codex has no hook system, so the JSONL it emits on stdout with --json
        IS the trace -- it is written to `events_path` for the collector to
        read, exactly as trace.jsonl is for Claude.

        Also provisions ZDOTDIR (see provision_codex_zdot) so Codex's
        `zsh -lc` login shell doesn't silently rebuild PATH out from under a
        stub-PATH set via the subprocess environment, and writes AGENTS.md
        pointing at any installed skills (see write_codex_agents_md) -- the
        parity equivalent of Claude's Skill tool, since Codex has none.

        Args:
            prompt: The prompt to send to Codex
            model: Model id or alias (see MODEL_ALIASES); resolved before use
            timeout: Timeout in seconds (default: 120)
            codex_bin: Name/path of the codex executable (default: "codex")
            events_path: Where to write the raw --json event stream
                (default: <trace_path-parent>/codex-events.jsonl)

        Returns:
            CompletedProcess with stdout (the JSONL event stream), stderr,
            and returncode.
        """
        resolved_model = resolve_model(model)

        zdot_dir = self.isolated_home / CODEX_ZDOT_DIRNAME
        bin_dir = self.isolated_home / CODEX_BIN_DIRNAME
        bin_dir.mkdir(parents=True, exist_ok=True)
        provision_codex_zdot(zdot_dir, bin_dir)

        env = dict(self.env)
        env["ZDOTDIR"] = str(zdot_dir)

        write_codex_agents_md(self.project_path)

        if events_path is None:
            events_path = self.trace_path.parent / "codex-events.jsonl"
        events_path = Path(events_path)
        last_message_path = self.isolated_home / "codex-last-message.txt"

        cmd = [
            codex_bin,
            "exec",
            "--yolo",
            "--model",
            resolved_model,
            "--json",
            "--output-last-message",
            str(last_message_path),
            "--skip-git-repo-check",
            "-c",
            'shell_environment_policy.inherit="all"',
            prompt,
        ]

        logger.info(f"Running codex command: model={resolved_model}")
        logger.debug(f"Full codex command: {cmd}")

        result = subprocess.run(
            cmd,
            env=env,
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Persist the JSONL trace -- this IS the codex trace artifact, since
        # there are no Claude-style hooks for codex to emit events through.
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(result.stdout, encoding="utf-8")
        self.codex_events_path = events_path

        self._process_result = result
        logger.debug(f"Codex command completed with return code: {result.returncode}")

        return result

    def find_transcript(self) -> Path | None:
        """Find the transcript file from the most recent session.

        Searches the isolated HOME's .claude/projects directory for
        transcript files and returns the most recent one.

        Returns:
            Path to transcript file, or None if not found
        """
        projects_dir = self.isolated_home / CLAUDE_DIR / "projects"

        if not projects_dir.exists():
            logger.warning(f"Projects directory not found: {projects_dir}")
            return None

        # Find all .jsonl files (excluding subagent transcripts)
        transcripts = []
        for transcript_file in projects_dir.rglob("*.jsonl"):
            # Skip subagent transcripts (in subagents/ subdirectory)
            if "subagents" not in str(transcript_file):
                transcripts.append(transcript_file)

        if not transcripts:
            logger.warning("No transcript files found")
            return None

        # Return most recent
        most_recent = max(transcripts, key=lambda p: p.stat().st_mtime)
        self.transcript_path = most_recent
        self.session_id = most_recent.stem

        logger.debug(f"Found transcript: {most_recent}")
        return most_recent

    @property
    def claude_stdout(self) -> str:
        """Get Claude CLI stdout from the last command."""
        return self._process_result.stdout if self._process_result else ""

    @property
    def claude_stderr(self) -> str:
        """Get Claude CLI stderr from the last command."""
        return self._process_result.stderr if self._process_result else ""


# =============================================================================
# Context Manager
# =============================================================================


@contextmanager
def isolated_claude_session(
    project_path: str | Path,
    trace_path: str | Path | None = None,
    copy_marketplace: bool = False,
    cleanup: bool = True,
) -> Generator[IsolatedSession, None, None]:
    """Context manager for running Claude in an isolated environment.

    Creates a temporary HOME directory, configures the environment,
    yields a session object for test execution, and cleans up afterwards.

    Args:
        project_path: Path to the test project (with .claude/ directory)
        trace_path: Path to trace.jsonl for hook events (default: reports/trace.jsonl)
        copy_marketplace: Whether to copy marketplace data for plugin install
        cleanup: Whether to clean up isolated HOME on exit (default: True)

    Yields:
        IsolatedSession object for running commands and accessing paths

    Example:
        >>> with isolated_claude_session("/path/to/test-harness") as session:
        ...     result = session.run_command("list files", tools=["Bash"])
        ...     # session.trace_path contains hook events
        ...     # session.find_transcript() locates the transcript

    Note:
        The HOME override completely hides user plugins. The project's
        .claude/settings.json (with hooks) is still used via --setting-sources.
    """
    project_path = Path(project_path).absolute()

    # Default trace path
    if trace_path is None:
        trace_path = project_path / "reports" / "trace.jsonl"
    else:
        trace_path = Path(trace_path).absolute()

    # Ensure trace directory exists
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    # Clear any existing trace file
    if trace_path.exists():
        trace_path.unlink()

    # Create isolated environment
    isolated_home = create_isolated_home()

    try:
        # Setup environment
        env = setup_test_environment(
            isolated_home=isolated_home,
            project_path=project_path,
            copy_marketplace=copy_marketplace,
        )

        # Create session object
        session = IsolatedSession(
            isolated_home=isolated_home,
            project_path=project_path,
            env=env,
            trace_path=trace_path,
        )

        logger.info(f"Created isolated session: HOME={isolated_home}")
        yield session

    finally:
        if cleanup:
            cleanup_test_environment(isolated_home)
            logger.info("Cleaned up isolated session")
        else:
            logger.info(f"Skipped cleanup, isolated HOME at: {isolated_home}")


# =============================================================================
# Utility Functions
# =============================================================================


def get_git_state(project_path: Path) -> dict[str, str | list[str]]:
    """Get current git state of the project.

    Captures the current branch, commit hash, and list of modified files
    for reproducibility information.

    Args:
        project_path: Path to the git repository

    Returns:
        Dictionary with branch, commit, and modified_files
    """
    result = {
        "branch": "",
        "commit": "",
        "modified_files": [],
    }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if branch_result.returncode == 0:
            result["branch"] = branch_result.stdout.strip()

        # Get current commit (short hash)
        commit_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if commit_result.returncode == 0:
            result["commit"] = commit_result.stdout.strip()

        # Get modified files
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if status_result.returncode == 0:
            modified = []
            for line in status_result.stdout.strip().split("\n"):
                if line:
                    # Format is "XY filename" - extract filename
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        modified.append(parts[1])
            result["modified_files"] = modified

    except Exception as e:
        logger.warning(f"Failed to get git state: {e}")

    return result
