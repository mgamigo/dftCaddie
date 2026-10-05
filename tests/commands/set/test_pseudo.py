from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import config, file_management as fm, utils
from dftcaddie.commands.set import pseudo


@pytest.fixture(autouse=True)
def configured_pseudos(monkeypatch, pseudo_settings):
    monkeypatch.setattr(config, "load_config", lambda: (pseudo_settings, Path.cwd()))
    return pseudo_settings


def test_pseudo_run_forwards_options(parse_args, monkeypatch):
    monkeypatch.setattr(
        utils,
        "resolve_calculation_directory",
        lambda directory: ("bands", None, "quantum_espresso"),
    )
    reader = Mock(return_value=SimpleNamespace(symbols=["Si"]))
    operation = Mock(return_value=0)
    monkeypatch.setattr(utils, "get_structure", reader)
    monkeypatch.setattr(pseudo, "apply_pseudos", operation)
    assert (
        pseudo.run(
            parse_args(
                "set", "pseudo", "Si.cif", "-l", "soc", "--soc", "-c", "--ratio", "2.0"
            )
        )
        == 0
    )
    reader.assert_called_once_with("Si.cif")
    operation.assert_called_once_with(
        kind_calc="bands",
        code="quantum_espresso",
        symbols=["Si"],
        library="soc",
        soc=True,
        configure=True,
        ratio=2.0,
    )


@pytest.mark.parametrize(
    "soc,library,filename",
    [
        (False, None, "Si.scalar.UPF"),
        (True, None, "Si.soc.UPF"),
        (False, "soc", "Si.soc.UPF"),
    ],
)
def test_defaults_and_explicit_library_are_independent_of_soc(soc, library, filename):
    Path("SYSTEM.INFO").write_text("ATOMIC_SPECIES=\nold\nEOL\nPSEUDO_DIR=\n")
    pseudo.apply_pseudos("bands", "quantum_espresso", ["Si"], soc, library=library)
    assert filename in Path("SYSTEM.INFO").read_text()


def test_pseudo_ratio_overrides_configuration():
    target = Path("SYSTEM.INFO")
    target.write_text("CUTOFF=\nECUTRHO=\n")
    pseudo.apply_pseudos(
        "bands", "quantum_espresso", ["Si"], False, configure=True, ratio=2.0
    )
    assert target.read_text() == "CUTOFF=80\nECUTRHO=640\n"


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_pseudos_without_configure_preserve_cutoffs(code):
    target = Path("SYSTEM.INFO" if code == "quantum_espresso" else "INCAR")
    original = (
        "CUTOFF=77\nECUTRHO=777\n" if code == "quantum_espresso" else "ENCUT = 777\n"
    )
    target.write_text(original)
    assert pseudo.apply_pseudos("bands", code, ["Si"], False) == 0
    assert target.read_text() == original


@pytest.mark.parametrize(
    "library,soc,message",
    [
        ("paw", False, "does not support"),
        ("scalar", True, "has_so=True"),
    ],
)
def test_incompatible_selection_does_not_write_files(library, soc, message):
    target = Path("SYSTEM.INFO")
    target.write_text("CUTOFF=77\nECUTRHO=777\n")
    before = {p: p.read_bytes() for p in Path.cwd().rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match=message):
        pseudo.apply_pseudos(
            "bands", "quantum_espresso", ["Si"], soc, library=library, configure=True
        )
    assert {p: p.read_bytes() for p in Path.cwd().rglob("*") if p.is_file()} == before


def test_missing_library_does_not_write_files(pseudo_settings):
    pseudo_settings["pseudopotentials"]["libraries"]["scalar"]["path"] = "missing"
    with pytest.raises(FileNotFoundError, match="directory does not exist"):
        pseudo.apply_pseudos("bands", "quantum_espresso", ["Si"], False)
    assert not Path("SYSTEM.INFO").exists()


def test_list_needs_no_structure_or_calculation(parse_args, capsys):
    assert pseudo.run(parse_args("set", "pseudo", "--list")) == 0
    output = capsys.readouterr().out
    assert "UPF: scalar" in output and "POTCAR: paw" in output
    assert "quantum_espresso/scalar" in output


def test_unsupported_code_warns():
    with pytest.warns(UserWarning, match="not implemented"):
        assert pseudo.apply_pseudos("bands", "unknown", ["Si"], False) == 0


@pytest.mark.parametrize("soc", [False, True])
def test_scalar_and_soc_defaults_can_share_full_relativistic_library(
    pseudo_settings, soc
):
    pseudo_settings["pseudopotentials"]["defaults"]["quantum_espresso"][
        "scalar"
    ] = "soc"
    Path("SYSTEM.INFO").write_text("ATOMIC_SPECIES=\nold\nEOL\nPSEUDO_DIR=\n")
    pseudo.apply_pseudos("bands", "quantum_espresso", ["Si"], soc)
    assert "Si.soc.UPF" in Path("SYSTEM.INFO").read_text()
