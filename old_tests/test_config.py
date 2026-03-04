from dftcaddie.config import calculations, clusters, mpi_executables


def test_calculations_schema_minimal():
    assert (
        isinstance(calculations, dict) and calculations
    ), "calculations must be a non-empty dict"

    for kind, cfg in calculations.items():
        assert isinstance(kind, str) and kind, "kind keys must be non-empty strings"
        assert isinstance(cfg, dict), f"calculations[{kind!r}] must be a dict"

        # required top-level keys
        assert "name" in cfg, f"calculations[{kind!r}] missing 'name'"
        assert "files" in cfg, f"calculations[{kind!r}] missing 'files'"

        assert (
            isinstance(cfg["name"], str) and cfg["name"]
        ), f"calculations[{kind!r}]['name'] must be a string"
        assert isinstance(
            cfg["files"], dict
        ), f"calculations[{kind!r}]['files'] must be a dict"

        for code, files_list in cfg["files"].items():
            assert (
                isinstance(code, str) and code
            ), f"code keys must be non-empty strings (kind={kind!r})"
            assert isinstance(
                files_list, list
            ), f"calculations[{kind!r}]['files'][{code!r}] must be a list"
            assert files_list, f"files list empty for kind={kind!r}, code={code!r}"
            assert all(
                isinstance(f, str) and f for f in files_list
            ), f"All template filenames must be non-empty strings (kind={kind!r}, code={code!r})"


def test_clusters_schema_minimal():
    assert isinstance(clusters, dict), "clusters must be a dict"

    # allow None key if you use it, but enforce structure for real clusters
    for key, cfg in clusters.items():
        if key is None:
            continue
        assert isinstance(cfg, dict), f"clusters[{key!r}] must be a dict"
        assert "mpi_command" in cfg, f"clusters[{key!r}] missing 'mpi_command'"
        assert "headers" in cfg, f"clusters[{key!r}] missing 'headers'"
        assert (
            isinstance(cfg["mpi_command"], str) and cfg["mpi_command"]
        ), f"clusters[{key!r}]['mpi_command'] must be a string"
        assert (
            isinstance(cfg["headers"], list) and cfg["headers"]
        ), f"clusters[{key!r}]['headers'] must be a list"


def test_mpi_executables_basic():
    assert isinstance(
        mpi_executables, (list, tuple, set)
    ), "mpi_executables should be a sequence"
    assert all(
        isinstance(x, str) and x for x in mpi_executables
    ), "mpi_executables must be non-empty strings"
