from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import utils
from dftcaddie.commands import calc, setup, pseudo


@pytest.mark.parametrize(
    "flavor,expected", [("fixed_cell", "relax"), ("variable_cell", "vc-relax")]
)
def test_calc_relax_flavor(parse_args, flavor, expected):
    calc.run(parse_args("calc", "-k", "relax", "-f", flavor, "-c", "quantum_espresso"))
    assert f"calculation='{expected}'" in Path("relax.sh").read_text()


def test_calc_interactive_details(parse_args, monkeypatch):
    answers = iter(["bands", "quantum_espresso", "no"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    calc.run(parse_args("calc", "--details"))
    assert "noncolin=.false." in Path("scf.sh").read_text()
    assert "lspinorb=.false." in Path("scf.sh").read_text()


def test_calc_overwrite(parse_args):
    args = parse_args("calc", "-k", "bands", "-c", "quantum_espresso", "--overwrite")
    calc.run(args)
    Path("bands.sh").write_text("old contents\n")
    calc.run(args)
    assert "old contents" not in Path("bands.sh").read_text()
    assert Path("master.sh").read_text().count("bash bands.sh\n") == 1


@pytest.mark.parametrize(
    "flags",
    [
        ("-k", "unknown"),
        ("-k", "bands", "-c", "unknown"),
        ("-k", "relax", "-f", "unknown"),
    ],
)
def test_calc_rejects_invalid_selection(parse_args, flags):
    with pytest.raises(SystemExit) as error:
        calc.run(parse_args("calc", *flags))
    assert error.value.code == 1
    assert not Path("master.sh").exists()


def test_calc_structure_without_pseudo(parse_args, monkeypatch):
    structure = SimpleNamespace(symbols=["Si"])
    setup_step, pseudo_step = Mock(), Mock()
    monkeypatch.setattr(utils, "get_structure", lambda path: structure)
    monkeypatch.setattr(setup, "apply_setup", setup_step)
    monkeypatch.setattr(pseudo, "apply_pseudos", pseudo_step)
    calc.run(
        parse_args("calc", "-k", "bands", "-c", "quantum_espresso", "-s", "Si.cif")
    )
    setup_step.assert_called_once_with(
        kind="bands",
        code="quantum_espresso",
        structure=structure,
        autokgrid=False,
        kpath=False,
    )
    pseudo_step.assert_not_called()
