import os
import sys
import subprocess
from pathlib import Path
import pytest

from dftcaddie import cli
from dftcaddie.cli import _build_parser


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONWARNINGS": "ignore"},
    )


def _get_subcommands():
    import argparse

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices.keys())


def test_caddie_help_works():
    p = _run(["caddie", "--help"])
    assert p.returncode == 0, p.stderr
    # argparse typically prints to stdout, but be tolerant
    assert (p.stdout + p.stderr).strip() != ""


@pytest.mark.parametrize("subcommand", _get_subcommands())
def test_caddie_subcommand_help_works(subcommand):
    # Only the subcommands your CLI actually supports
    p = _run(["caddie", subcommand, "--help"])
    assert p.returncode == 0, (subcommand, p.stderr)
    assert (p.stdout + p.stderr).strip() != ""


def test_python_module_cli_invocation_returns_zero():
    """
    Some projects don't expose help text through `python -m ...` unless the
    module has a __main__ entry point. We still assert it is runnable.
    """
    p = _run([sys.executable, "-m", "dftcaddie.cli", "--help"])
    assert p.returncode == 0, p.stderr


def test_keyboard_interrupt_exits_cleanly(monkeypatch, capsys):
    def interrupt(_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.calc_client, "run", interrupt)

    assert cli.main(["calc"]) == 130
    captured = capsys.readouterr()

    assert "See you on the back nine ⛳" in captured.err
    assert "Traceback" not in captured.err
    assert "KeyboardInterrupt" not in captured.err
    assert "Caddie's done" not in captured.out
