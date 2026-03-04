import pathlib
import os

from dftcaddie import config


def test_pseudo_libraries():
    assert isinstance(config.resolve_pslibrary(), pathlib.PosixPath)
    assert isinstance(config.resolve_potcar_library(), pathlib.PosixPath)


def test_resources_folder_exists():
    assert config.SOURCE_DIR.exists()


def test_numerical_defaults():
    assert config.default_kppra > 0, "default_kppra should be bigger than 0"
    assert (
        config.default_cutoff_ratio > 0
    ), "default_cutoff_ratio should be bigger than 0"


def test_suggested_pseudos():
    assert len(config.suggested_qe_pseudos) == 94, f"Not 94 suggested pseudos."


def test_mpi_executables_basic():
    mpi_executables = config.mpi_executables
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


def test_clusters_schema():
    clusters = config.clusters
    assert isinstance(clusters, dict), "clusters must be a dict"

    check_list = [
        ["hostname", str],
        ["mpi_command", str],
        ["headers", list],
    ]
    for cluster, cluster_dict in clusters.items():
        for key in check_list:
            _check_key(cluster_dict, key[0], key[1])
        headers = cluster_dict["headers"]
        for header in headers:
            _check_key(header, "name", str)
            _check_key(header, "file", str)
            path = os.path.join(config.SOURCE_DIR, "sbatch_headers", header["file"])
            assert os.path.exists(path), "Missing header file: {path!r}"


def _check_calculation_flavor(flavor_dict):
    _check_key(flavor_dict, "config", list)
    _check_key(flavor_dict, "files", dict)
    cfg = flavor_dict["config"]
    for item in cfg:
        _check_key(item, "name", str)
        _check_key(item, "prompt", str)
        _check_key(item, "options", list)
        if item["name"] == "code":
            codes = item["options"]
    files = flavor_dict["files"]
    for code, code_files in files.items():
        assert code in codes
        for f in code_files:
            path = os.path.join(config.SOURCE_DIR, "templates", f)
            assert os.path.exists(path)


def test_calculations_schema():
    calculations = config.calculations
    for kind, kind_dict in calculations.items():
        _check_key(kind_dict, "name", str)
        if "flavors" not in kind_dict.keys():
            _check_calculation_flavor(kind_dict)
        else:
            flavors = kind_dict["flavors"]
            for flavor, flavor_dict in flavors.items():
                _check_key(flavor_dict, "name", str)
                _check_calculation_flavor(flavor_dict)
