from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import config, file_management as fm, utils
from dftcaddie.commands.set import pseudo


def test_pseudo_run_forwards_options(parse_args, monkeypatch):
    monkeypatch.setattr(
        utils,
        "resolve_calculation_directory",
        lambda directory: ("bands", None, "quantum_espresso"),
    )
    reader = Mock(return_value=SimpleNamespace(symbols=["Si"]))
    operation = Mock()
    monkeypatch.setattr(utils, "get_structure", reader)
    monkeypatch.setattr(pseudo, "apply_pseudos", operation)
    pseudo.run(
        parse_args(
            "set",
            "pseudo",
            "Si.cif",
            "-e",
            "pbesol",
            "-k",
            "us",
            "-r",
            "-c",
            "--ratio",
            "2.0",
        )
    )
    reader.assert_called_once_with("Si.cif")
    operation.assert_called_once_with(
        kind_calc="bands",
        code="quantum_espresso",
        symbols=["Si"],
        exchange="pbesol",
        kind_pseudo="us",
        relativistic=True,
        configure=True,
        ratio=2.0,
    )


def test_vasp_pseudos_honor_exchange_and_kind(monkeypatch):
    potential = Path("Si.POTCAR")
    potential.write_text("Synthetic POTCAR\n", encoding="utf-8")
    finder = Mock(return_value=[str(potential)])
    monkeypatch.setattr(fm, "get_potcar_paths", finder)

    pseudo.apply_pseudos(
        "bands", "vasp", ["Si"], False, exchange="pz", kind_pseudo="us"
    )

    finder.assert_called_once_with(symbols=["Si"], exchange="pz", kind="us")


def test_pseudo_ratio_overrides_configuration(monkeypatch):
    pseudos = ["/library/pbe/PSEUDOPOTENTIALS/Si.UPF"]
    cutoff = Mock()
    monkeypatch.setattr(fm, "get_qe_pseudo_paths", lambda **kwargs: pseudos)
    monkeypatch.setattr(fm, "write_pseudos_to_system_info", Mock())
    monkeypatch.setattr(fm, "set_spin_orbit_coupling", Mock())
    monkeypatch.setattr(fm, "configure_qe_cutoffs_from_pseudos", cutoff)

    pseudo.apply_pseudos(
        "bands", "quantum_espresso", ["Si"], False, configure=True, ratio=2.0
    )

    cutoff.assert_called_once_with("SYSTEM.INFO", pseudos, ratio=2.0)


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
