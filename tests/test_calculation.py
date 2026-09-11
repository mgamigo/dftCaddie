"""Calculation resolution without CLI interaction or file preparation."""

from copy import deepcopy

import pytest

from dftcaddie.calculation import CalculationSpec, resolve_calculation


def test_defaults_and_explicit_overrides(bundled_config):
    request = {"kind": "bands", "code": "quantum_espresso"}
    original = deepcopy(bundled_config)
    spec = resolve_calculation(request, bundled_config, cluster="local")
    assert isinstance(spec, CalculationSpec)
    assert spec.soc is True
    assert spec.flavor is None
    assert request == {"kind": "bands", "code": "quantum_espresso"}
    assert bundled_config == original
    explicit = resolve_calculation(
        dict(request, soc=False, auto=True, structure="Si.cif"),
        bundled_config,
        cluster="local",
    )
    assert explicit.soc is False
    assert explicit.pseudo is True


def test_missing_choice_without_prompt(bundled_config):
    with pytest.raises(ValueError, match="Missing code"):
        resolve_calculation({"kind": "bands"}, bundled_config, cluster="local")


def test_custom_settings_and_flavor_defaults(bundled_config):
    definition = bundled_config["calculations"]["relax"]["flavors"]["variable_cell"]
    definition["config"].append(
        {"name": "custom", "options": ["a", "b"], "default": "b", "prompt": "Custom"}
    )
    spec = resolve_calculation(
        {"kind": "relax", "flavor": "variable_cell", "code": "vasp"},
        bundled_config,
        cluster="local",
    )
    assert spec.settings["cell_relaxation"] is True
    assert spec.settings["custom"] == "b"
    assert spec.as_namespace().custom == "b"
    assert spec.as_namespace().flavor == "variable_cell"


@pytest.mark.parametrize("flag", ["auto", "pseudo"])
def test_missing_structure_rejected_by_resolver(bundled_config, flag):
    with pytest.raises(ValueError, match="require --structure FILE"):
        resolve_calculation({flag: True}, bundled_config, cluster="local")
