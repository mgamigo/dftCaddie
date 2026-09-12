import os
import sys
import subprocess
from pathlib import Path
from argparse import Namespace
import pytest

from dftcaddie import __version__
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


def test_caddie_version():
    p = _run(["caddie", "--version"])
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == f"caddie {__version__}"


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


def test_directory_scopes_command_dispatch(tmp_path, monkeypatch):
    original = Path.cwd()
    target = tmp_path / "calculation"
    target.mkdir()

    def run(_args):
        assert Path.cwd() == target
        Path("prepared.txt").write_text("prepared\n")

    monkeypatch.setattr(cli.calc, "run", run)

    assert cli.main(["-C", str(target), "calc"]) == 0
    assert Path.cwd() == original
    assert (target / "prepared.txt").read_text() == "prepared\n"


def test_directory_must_exist(tmp_path):
    p = _run(["caddie", "-C", str(tmp_path / "missing"), "calc"])

    assert p.returncode == 2
    assert "directory does not exist" in p.stderr


def test_directory_prepares_calculation_outside_invocation_directory(tmp_path):
    target = tmp_path / "calculation"
    target.mkdir()

    p = _run(
        [
            "caddie",
            "--directory",
            str(target),
            "calc",
            "--kind",
            "bands",
            "--code",
            "vasp",
        ],
        cwd=tmp_path,
    )

    assert p.returncode == 0, p.stderr
    assert (target / "master.sh").is_file()
    assert not (tmp_path / "master.sh").exists()


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
    modules = {
        "calc": cli.calc,
        "set": cli.set_command,
        "config": cli.config,
    }
    handlers = {}
    for name in _get_subcommands():
        handlers[name] = Mock(return_value=0)
        monkeypatch.setattr(modules[name], "run", handlers[name])

    # Isolate dispatch from command-specific required arguments.
    args = Namespace(command=subcommand, verbose=0, quiet=False, directory=None)
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
