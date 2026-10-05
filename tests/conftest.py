"""Shared bundled configuration, independent of user settings."""

from copy import deepcopy

import pytest

from dftcaddie.config import load_config
from dftcaddie.checks.workflows import calculation_cases

_BUNDLED_CONFIG, _BUNDLED_RESOURCES = load_config(default_config=True)


@pytest.fixture(scope="session")
def bundled_resources():
    return _BUNDLED_RESOURCES


@pytest.fixture
def bundled_config():
    """Give each test its own mutable copy of the bundled settings."""
    return deepcopy(_BUNDLED_CONFIG)


@pytest.fixture(
    params=list(calculation_cases(_BUNDLED_CONFIG)),
    ids=lambda case: "/".join(value or "default" for value in case),
)
def calculation_case(request):
    return request.param


@pytest.fixture
def pseudo_settings(tmp_path):
    """Small independent UPF/POTCAR collections with different scalar/SOC files."""
    root = tmp_path / "potentials"
    root.mkdir()
    for name, soc in (("Si.scalar.UPF", "F"), ("Si.soc.UPF", "T")):
        (root / name).write_text(
            f'<UPF><PP_HEADER element="Si" pseudo_type="USPP" functional="PBE" '
            f'has_so="{soc}" wfc_cutoff="40" rho_cutoff="320"/></UPF>\n'
        )
    for element in ("Si", "Cs_sv"):
        folder = root / element
        folder.mkdir()
        (folder / "POTCAR").write_text(
            f"TITEL = PAW_PBE {element} synthetic\n ENMAX = 240;\n"
        )
    return {
        "default_cutoff_ratio": 1.5,
        "pseudopotentials": {
            "defaults": {
                "quantum_espresso": {"scalar": "scalar", "soc": "soc"},
                "vasp": {"scalar": "paw", "soc": "paw"},
            },
            "libraries": {
                "scalar": {
                    "format": "upf",
                    "supported_codes": ["quantum_espresso"],
                    "path": str(root),
                    "pattern": "{element}.scalar.UPF",
                },
                "soc": {
                    "format": "upf",
                    "supported_codes": ["quantum_espresso"],
                    "path": str(root),
                    "pattern": "{element}.soc.UPF",
                },
                "paw": {
                    "format": "potcar",
                    "supported_codes": ["vasp"],
                    "path": str(root),
                    "pattern": "{element}/POTCAR",
                },
            },
        },
        "suggested_pseudos": [
            {"libraries": ["paw"], "elements": {"Cs": "Cs_sv/POTCAR"}}
        ],
    }
