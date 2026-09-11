import os
import sys
import subprocess
from pathlib import Path
from argparse import Namespace
import pytest

from dftcaddie import cli
from dftcaddie.cli import _build_parser
from unittest.mock import Mock


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
    p = _run([sys.executable, "-m", "dftcaddie.cli", "--help"])
    assert p.returncode == 0, p.stderr
    assert "DFT Caddie" in p.stdout


def test_keyboard_interrupt_exits_cleanly(monkeypatch, capsys):
    def interrupt(_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.calc, "run", interrupt)

    assert cli.main(["calc"]) == 130
    captured = capsys.readouterr()

    assert "👋 Caddie has left the course." in captured.err
    assert "Traceback" not in captured.err
    assert "KeyboardInterrupt" not in captured.err
    assert "May your jobs converge" not in captured.out


def test_calc_prints_heading(monkeypatch, capsys):
    monkeypatch.setattr(cli.calc, "run", Mock(return_value=0))

    assert cli.main(["calc", "--kind", "bands", "--code", "quantum_espresso"]) == 0
    assert "Don’t shoot the caddie" in capsys.readouterr().out


def test_non_calc_command_omits_heading(monkeypatch, capsys):
    monkeypatch.setattr(cli.config, "run", Mock(return_value=0))

    assert cli.main(["config", "check"]) == 0
    assert "Don’t shoot the caddie" not in capsys.readouterr().out


@pytest.mark.parametrize("subcommand", _get_subcommands())
def test_dispatch(monkeypatch, subcommand):
    handlers = {}
    for name in _get_subcommands():
        handlers[name] = Mock(return_value=0)
        monkeypatch.setattr(getattr(cli, name), "run", handlers[name])

    # Isolate dispatch from command-specific required arguments.
    args = Namespace(command=subcommand, verbose=0, quiet=False)
    parser = Mock()
    parser.parse_args.return_value = args
    monkeypatch.setattr(cli, "_build_parser", lambda: parser)

    assert cli.main([subcommand]) == 0

    for name, handler in handlers.items():
        if name == subcommand:
            handler.assert_called_once_with(args)
        else:
            handler.assert_not_called()


def test_no_command_prints_help(capsys):
    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert "Don’t shoot the caddie" in output
    assert "usage: caddie" in output
