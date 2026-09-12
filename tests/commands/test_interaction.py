"""Interactive cancellation and unattended command behavior."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from dftcaddie import cli, prompts


@pytest.mark.parametrize(
    "args,hint",
    [
        (["calc"], "--kind"),
        (["set", "header", "--cluster", "cluster2"], "--header"),
    ],
)
def test_missing_input_without_terminal(args, hint, monkeypatch, capsys):
    monkeypatch.setattr(prompts.sys, "stdin", Mock(isatty=lambda: False))
    assert cli.main(args) == 1
    output = capsys.readouterr()
    assert hint in output.err
    assert "No interactive terminal" in output.err
    assert "Traceback" not in output.err
    assert not list(Path.cwd().iterdir())


def test_explicit_calc_without_terminal(monkeypatch):
    monkeypatch.setattr(prompts.sys, "stdin", Mock(isatty=lambda: False))
    assert cli.main(["calc", "--kind", "bands", "--code", "vasp"]) == 0
    assert Path("master.sh").is_file()


def test_declined_overwrite_keeps_file_and_completes(monkeypatch, capsys):
    Path("bands.sh").write_text("Keep my script.\n")
    monkeypatch.setattr(prompts, "confirm", lambda *args, **kwargs: False)

    status = cli.main(["calc", "--kind", "bands", "--code", "quantum_espresso"])

    assert status == 0
    assert Path("bands.sh").read_text() == "Keep my script.\n"
    assert Path("master.sh").is_file()
    assert "May your jobs converge" in capsys.readouterr().out


@pytest.mark.parametrize("decision", ["cancel", "noninteractive"])
def test_overwrite_stops_before_any_edits(decision, monkeypatch, capsys):
    Path("bands.sh").write_text("Keep my script.\n")
    Path("notes.txt").write_text("Keep my notes.\n")
    before = {p.name: p.read_bytes() for p in Path.cwd().iterdir()}

    def confirm(*args, **kwargs):
        if decision == "cancel":
            raise KeyboardInterrupt
        return decision

    if decision == "noninteractive":
        monkeypatch.setattr(prompts.sys, "stdin", Mock(isatty=lambda: False))
    else:
        monkeypatch.setattr(prompts, "confirm", confirm)
    status = cli.main(["calc", "--kind", "bands", "--code", "quantum_espresso"])
    assert status == (1 if decision == "noninteractive" else 130)
    assert {p.name: p.read_bytes() for p in Path.cwd().iterdir()} == before
    output = capsys.readouterr()
    assert "May your jobs converge" not in output.out
    assert "Traceback" not in output.err


def test_confirmed_overwrite(monkeypatch):
    Path("bands.sh").write_text("Old script.\n")
    monkeypatch.setattr(prompts, "confirm", lambda *args, **kwargs: True)
    assert cli.main(["calc", "--kind", "bands", "--code", "quantum_espresso"]) == 0
    assert "Old script" not in Path("bands.sh").read_text()
