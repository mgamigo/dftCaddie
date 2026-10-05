"""Checks for the bundled configuration and its packaged resources."""

from pathlib import Path

import pytest

import dftcaddie.utils as ut


@pytest.fixture(autouse=True)
def bundled_calculations(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ut.config.clear_config_cache()
    yield
    ut.config.clear_config_cache()


def test_resources_folder_exists(bundled_resources):
    assert bundled_resources.exists()


def test_suggested_pseudos_cover_known_elements(bundled_config):
    groups = bundled_config["suggested_pseudos"]
    psl = next(group for group in groups if "pbesol-us-sr" in group["libraries"])
    assert len(psl["elements"]) == 94
    assert psl["elements"]["Si"] == "Si.*-nl-*_psl.1.0.0.UPF"
    assert "pbesol-us-fr" in psl["libraries"]


def test_resolve_calculation_directory(calculation_case, bundled_config, tmp_path):
    kind, flavor, code = calculation_case
    calculations = bundled_config["calculations"]
    definition = calculations[kind]
    if flavor is not None:
        definition = definition["flavors"][flavor]
    files = definition["files"][code]
    for filename in files:
        (tmp_path / Path(filename).name).touch()
    res_kind, res_flavor, res_code = ut.resolve_calculation_directory(tmp_path)
    assert (res_kind, res_code) == (kind, code)
    # Flavors may intentionally share the same complete file signature.
    signatures = [
        other_flavor
        for other_flavor, variant in calculations[kind]
        .get("flavors", {None: calculations[kind]})
        .items()
        if code in variant["files"]
        and {Path(f).name for f in variant["files"][code]}
        == {Path(f).name for f in files}
    ]
    assert res_flavor == (flavor if len(signatures) == 1 else None)


def test_get_config_for_all_cases(calculation_case, bundled_config):
    kind, flavor, _ = calculation_case
    definition = bundled_config["calculations"][kind]
    if flavor is not None:
        definition = definition["flavors"][flavor]
    for entry in definition["config"]:
        assert ut.get_config(kind, entry["name"], flavor) == entry
        assert ut.get_config(kind, entry["name"])["name"] == entry["name"]
