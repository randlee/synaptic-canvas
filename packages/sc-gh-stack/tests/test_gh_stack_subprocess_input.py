"""The shared subprocess seam accepts bounded-argv stdin without shell writes."""
from pathlib import Path
import sys
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gh_stack_shared import run


def test_text_stdin_reaches_child_without_becoming_command_arguments():
    refspecs = ''.join(f'+refs/heads/layer/{n}:refs/remotes/origin/layer/{n}\n' for n in range(120))
    command = [sys.executable, '-c', 'import sys; sys.stdout.write(sys.stdin.read())']
    result = run(command, input=refspecs)
    assert result.returncode == 0
    assert result.stdout == refspecs
    assert len(command) == 3


def test_default_subprocess_call_preserves_existing_no_input_behavior():
    with patch('gh_stack_shared.subprocess.run', return_value=subprocess.CompletedProcess(['git'], 0, '', '')) as child:
        run(['git', '--version'])
    assert 'input' not in child.call_args.kwargs
