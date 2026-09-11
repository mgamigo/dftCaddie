"""Checks for the bundled configuration and its packaged resources."""

from pathlib import Path

import pytest

import dftcaddie.utils as ut
from dftcaddie.checks.config import validate_config


@pytest.fixture(autouse=True)
def bundled_calculations(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ut.config.clear_config_cache()
    yield
    ut.config.clear_config_cache()


def test_resources_folder_exists(bundled_resources):
    assert bundled_resources.exists()


def test_bundled_config_resources_are_valid(bundled_config, bundled_resources):
    data = dict(bundled_config)
    data.pop("qe_pslibrary", None)
    data.pop("vasp_pseudopotentials", None)

    issues = validate_config(data, bundled_resources, environ={})

    assert not [issue for issue in issues if issue.level == "error"]
    assert {issue.location for issue in issues} == {
        "qe_pslibrary",
        "vasp_pseudopotentials",
    }


def test_suggested_pseudos_cover_known_elements(bundled_config):
    assert len(bundled_config["suggested_qe_pseudos"]) == 94


def test_resolve_calc_current_dir(
    calculation_case, bundled_config, tmp_path, monkeypatch
):
    kind, flavor, code = calculation_case
    calculations = bundled_config["calculations"]
    definition = calculations[kind]
    if flavor is not None:
        definition = definition["flavors"][flavor]
    files = definition["files"][code]
    for filename in files:
        (tmp_path / Path(filename).name).touch()
    monkeypatch.chdir(tmp_path)
    res_kind, res_flavor, res_code = ut.resolve_calc_current_dir()
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
