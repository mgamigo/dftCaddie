import os
import sys
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONWARNINGS": "ignore"},
    )


def test_caddie_help_works():
    p = _run(["caddie", "--help"])
    assert p.returncode == 0, p.stderr
    # argparse typically prints to stdout, but be tolerant
    assert (p.stdout + p.stderr).strip() != ""


def test_caddie_subcommand_help_works():
    # Only the subcommands your CLI actually supports
    for sub in ("calc", "setup", "pseudo"):
        p = _run(["caddie", sub, "--help"])
        assert p.returncode == 0, (sub, p.stderr)
        assert (p.stdout + p.stderr).strip() != ""


def test_python_module_cli_invocation_returns_zero():
    """
    Some projects don't expose help text through `python -m ...` unless the
    module has a __main__ entry point. We still assert it is runnable.
    """
    p = _run([sys.executable, "-m", "dftcaddie.cli", "--help"])
    assert p.returncode == 0, p.stderr
