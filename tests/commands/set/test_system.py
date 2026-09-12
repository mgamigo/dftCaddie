from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import utils, file_management as fm
from dftcaddie.commands.set import system, pseudo


@pytest.mark.parametrize(
    "autokgrid,kpath", [(False, False), (True, False), (False, True)]
)
def test_apply_system_optional_steps(monkeypatch, autokgrid, kpath):
    structure = SimpleNamespace()
    writer, grid, path = Mock(), Mock(), Mock()
    monkeypatch.setattr(fm, "set_crystal_structure", writer)
    monkeypatch.setattr(fm, "set_auto_kgrid", grid)
    monkeypatch.setattr(fm, "set_high_symmetry_path", path)
    assert (
        system.apply_system(
            "bands", "quantum_espresso", structure, autokgrid, 1234, kpath
        )
        == 0
    )
    writer.assert_called_once_with(structure, "quantum_espresso")
    if autokgrid:
        grid.assert_called_once_with(structure, "quantum_espresso", 1234)
    else:
        grid.assert_not_called()
    if kpath:
        path.assert_called_once_with(structure, "quantum_espresso")
    else:
        path.assert_not_called()


def test_system_pseudo_uses_flavor_default(parse_args, monkeypatch):
    structure = SimpleNamespace(symbols=["Si"])
    monkeypatch.setattr(
        utils, "resolve_calc_current_dir", lambda: ("relax", "variable_cell", "vasp")
    )
    monkeypatch.setattr(utils, "get_structure", Mock(return_value=structure))
    operation, pseudos = Mock(), Mock()
    monkeypatch.setattr(system, "apply_system", operation)
    monkeypatch.setattr(pseudo, "apply_pseudos", pseudos)
    system.run(
        parse_args(
            "set",
            "system",
            "Si.cif",
            "--autokgrid",
            "--kpath",
            "--kppra",
            "1234",
            "--pseudo",
        )
    )
    operation.assert_called_once_with(
        kind="relax",
        code="vasp",
        structure=structure,
        autokgrid=True,
        kpath=True,
        kppra=1234,
    )
    pseudos.assert_called_once_with(
        kind_calc="relax",
        code="vasp",
        symbols=["Si"],
        relativistic=False,
        configure=True,
    )


def test_system_rejects_empty_directory(parse_args):
    with pytest.raises(RuntimeError, match="Could not infer"):
        system.run(parse_args("set", "system", "Si.cif"))
