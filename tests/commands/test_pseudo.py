from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import config, file_management as fm, utils
from dftcaddie.commands import pseudo


def test_pseudo_run_forwards_options(parse_args, monkeypatch):
    monkeypatch.setattr(
        utils, "resolve_calc_current_dir", lambda: ("bands", None, "quantum_espresso")
    )
    reader = Mock(return_value=SimpleNamespace(symbols=["Si"]))
    operation = Mock()
    monkeypatch.setattr(utils, "get_structure", reader)
    monkeypatch.setattr(pseudo, "apply_pseudos", operation)
    pseudo.run(parse_args("pseudo", "Si.cif", "-e", "pbesol", "-k", "us", "-r", "-c"))
    reader.assert_called_once_with("Si.cif")
    operation.assert_called_once_with(
        kind_calc="bands",
        code="quantum_espresso",
        symbols=["Si"],
        exchange="pbesol",
        kind_pseudo="us",
        relativistic=True,
        configure=True,
    )


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_pseudos_without_configure_preserve_cutoffs(monkeypatch, code):
    if code == "quantum_espresso":
        monkeypatch.setattr(
            fm,
            "get_qe_pseudo_paths",
            lambda **kwargs: ["/library/pbe/PSEUDOPOTENTIALS/Si.UPF"],
        )
        target = Path("SYSTEM.INFO")
        original = "CUTOFF=77\nECUTRHO=777\n"
    else:
        potential = Path("Si.POTCAR")
        potential.write_text("Synthetic POTCAR without cutoff recommendations\n")
        monkeypatch.setattr(fm, "get_potcar_paths", lambda **kwargs: [str(potential)])
        target = Path("INCAR")
        original = "ENCUT = 777\n"
    target.write_text(original)
    assert pseudo.apply_pseudos("bands", code, ["Si"], False, configure=False) == 0
    assert target.read_text() == original


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_missing_library_does_not_write_files(monkeypatch, code):
    monkeypatch.setattr(config, "load_config", lambda: ({}, Path.cwd()))
    with pytest.raises(RuntimeError, match="not defined"):
        pseudo.apply_pseudos("bands", code, ["Si"], False)
    assert list(Path.cwd().iterdir()) == []


def test_unsupported_code_warns():
    with pytest.warns(UserWarning, match="not implemented"):
        assert pseudo.apply_pseudos("bands", "unknown", ["Si"], False) == 0
