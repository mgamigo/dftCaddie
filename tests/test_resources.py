"""Checks for the bundled configuration and its packaged resources."""

from pathlib import Path

import pytest

import dftcaddie.utils as ut


@pytest.fixture(autouse=True)
def bundled_calculations(monkeypatch, bundled_config, bundled_resources):
    monkeypatch.setattr(
        ut.config, "load_config", lambda: (bundled_config, bundled_resources)
    )


def test_resources_folder_exists(bundled_resources):
    assert bundled_resources.exists()


def test_numerical_defaults(bundled_config):
    for key in ("default_kppra", "nscf_kppra_ratio", "default_cutoff_ratio"):
        assert type(bundled_config[key]) in (int, float), key
        assert bundled_config[key] > 0, key


def test_suggested_pseudos(bundled_config):
    assert (
        len(bundled_config["suggested_qe_pseudos"]) == 94
    ), f"Not 94 suggested pseudos."


def test_mpi_executables_basic(bundled_config):
    mpi_executables = bundled_config["mpi_executables"]
    assert isinstance(
        mpi_executables, (list, tuple, set)
    ), "mpi_executables should be a sequence"
    assert all(
        isinstance(x, str) and x for x in mpi_executables
    ), "mpi_executables must be non-empty strings"


def _check_key(dictionary, key, key_type=None):
    assert key in dictionary.keys(), f"Missing key {key!r} in {dictionary!r}"
    if key_type is not None:
        assert isinstance(
            dictionary[key], key_type
        ), f"{key!r} is not {key_type!r} type"


def test_clusters_schema(bundled_config, bundled_resources):
    clusters = bundled_config["clusters"]
    assert isinstance(clusters, dict), "clusters must be a dict"
    assert "local" in clusters

    check_list = [
        ["hostname", str],
        ["mpi_command", str],
        ["headers", list],
    ]
    for cluster, cluster_dict in clusters.items():
        for key in check_list:
            _check_key(cluster_dict, key[0], key[1])
        headers = cluster_dict["headers"]
        assert headers, cluster
        assert len({header["name"] for header in headers}) == len(headers), cluster
        for header in headers:
            _check_key(header, "name", str)
            _check_key(header, "file", str)
            path = bundled_resources / "sbatch_headers" / header["file"]
            assert path.is_file(), f"Missing header file: {path}"


def _check_calculation_flavor(flavor_dict, bundled_resources):
    _check_key(flavor_dict, "config", list)
    _check_key(flavor_dict, "files", dict)
    cfg = flavor_dict["config"]
    assert cfg
    codes = None
    for item in cfg:
        _check_key(item, "name", str)
        _check_key(item, "prompt", str)
        _check_key(item, "options", list)
        assert item["options"], item["name"]
        if "default" in item:
            assert item["default"] in item["options"], item["name"]
        if item["name"] == "code":
            codes = item["options"]
    files = flavor_dict["files"]
    assert len({item["name"] for item in cfg}) == len(cfg)
    assert codes, "Missing code options"
    assert set(files) == set(codes), "Code options and template mappings differ"
    for code, code_files in files.items():
        assert isinstance(code_files, list) and code_files, code
        assert len({Path(f).name for f in code_files}) == len(code_files), code
        for f in code_files:
            path = bundled_resources / "templates" / f
            assert path.is_file(), f"Missing template: {path}"


def test_calculations_schema(bundled_config, bundled_resources):
    calculations = bundled_config["calculations"]
    assert isinstance(calculations, dict) and calculations
    for kind, kind_dict in calculations.items():
        _check_key(kind_dict, "name", str)
        if "flavors" not in kind_dict.keys():
            _check_calculation_flavor(kind_dict, bundled_resources)
        else:
            flavors = kind_dict["flavors"]
            assert isinstance(flavors, dict) and flavors, kind
            for flavor, flavor_dict in flavors.items():
                _check_key(flavor_dict, "name", str)
                _check_calculation_flavor(flavor_dict, bundled_resources)


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


@pytest.mark.parametrize("code", ["quantum_espresso", "wannier90"])
def test_bundled_kpath_files(code, bundled_resources):
    for space_group in range(1, 231):
        path = bundled_resources / "kpaths" / code / f"SG{space_group}"
        assert path.is_file(), f"Missing k-path: {path}"
        assert path.stat().st_size > 0, f"Empty k-path: {path}"
