"""Isolated bundled resources and synthetic libraries for CLI workflows."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import socket

import pytest
import yaml

from dftcaddie import cli, config, file_management as fm, utils
from dftcaddie.commands import setup

RESOURCES = Path(__file__).resolve().parents[2] / "dftcaddie" / "resources"
with (RESOURCES / "config.yaml").open() as stream:
    BUNDLED = yaml.safe_load(stream)

CASES = [
    pytest.param(
        SimpleNamespace(kind=kind, flavor=flavor, code=code, files=files),
        id=f"{kind}-{flavor or 'default'}-{code}",
    )
    for kind, definition in BUNDLED["calculations"].items()
    for flavor, variant in definition.get("flavors", {None: definition}).items()
    for code, files in variant["files"].items()
]


@pytest.fixture(params=CASES)
def calculation_case(request):
    return request.param


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    data = deepcopy(BUNDLED)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(socket, "gethostname", lambda: "workflow-test-host")
    monkeypatch.delenv("PSLIBRARY", raising=False)

    # Minimal test headers, not potentials suitable for actual calculations.
    qe = tmp_path / "qe-library"
    for exchange in ("pbe", "rel-pbe"):
        folder = qe / exchange / "PSEUDOPOTENTIALS"
        folder.mkdir(parents=True)
        (folder / f"Si.{exchange}-nl-kjpaw_psl.1.0.0.UPF").write_text(
            "Suggested minimum cutoff for wavefunctions: 40 Ry\n"
            "Suggested minimum cutoff for charge density: 160 Ry\n"
        )
    vasp = tmp_path / "vasp-library"
    folder = vasp / "PAW_PBE" / "Si"
    folder.mkdir(parents=True)
    potcar = "Synthetic Si potential for testing only\n ENMAX = 200.0; ENMIN = 150.0\n"
    (folder / "POTCAR").write_text(potcar)
    data["qe_pslibrary"] = str(qe)
    data["vasp_pseudopotentials"] = str(vasp)

    monkeypatch.setattr(config, "CONFIG", data)
    monkeypatch.setattr(config, "SOURCE_DIR", RESOURCES)
    monkeypatch.setattr(fm, "SOURCE_DIR", RESOURCES)
    for name in (
        "calculations",
        "clusters",
        "mpi_executables",
        "suggested_qe_pseudos",
        "default_kppra",
        "nscf_kppra_ratio",
        "default_cutoff_ratio",
    ):
        monkeypatch.setattr(config, name, data[name])
        if hasattr(fm, name):
            monkeypatch.setattr(fm, name, data[name])
    monkeypatch.setattr(utils, "calculations", data["calculations"])
    monkeypatch.setattr(setup, "default_kppra", data["default_kppra"])
    # calc calls apply_setup without kppra; its default was bound at import time.
    monkeypatch.setattr(
        setup.apply_setup, "__defaults__", (False, data["default_kppra"], False)
    )

    structure = tmp_path / "Si.cif"
    structure.write_bytes(
        (Path(__file__).resolve().parents[1] / "data/Si.cif").read_bytes()
    )
    working = tmp_path / "calculation"
    working.mkdir()
    monkeypatch.chdir(working)

    def unexpected_input(prompt):
        pytest.fail(f"Unexpected workflow prompt: {prompt}")

    monkeypatch.setattr("builtins.input", unexpected_input)
    for resolver in (config.resolve_pslibrary, config.resolve_potcar_library):
        resolver.cache_clear()

    def run(*args):
        assert cli.main(list(args)) == 0

    yield SimpleNamespace(
        run=run,
        structure=str(structure),
        directory=working,
        resources=RESOURCES,
        config=data,
        potcar=potcar,
    )
    for resolver in (config.resolve_pslibrary, config.resolve_potcar_library):
        resolver.cache_clear()
