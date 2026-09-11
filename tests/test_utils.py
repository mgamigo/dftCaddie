from pathlib import Path

import pytest

import dftcaddie.utils as ut


def test_resolve_cluster(monkeypatch: pytest.MonkeyPatch):

    clusters = {
        "local": {"hostname": ""},
        "lumi": {"hostname": "lumi"},
        "marconi": {"hostname": "login.marconi"},
    }

    # resolve_cluster imports socket *inside* the function, so patch socket.gethostname
    import socket

    monkeypatch.setattr(socket, "gethostname", lambda: "login.marconi123")
    assert ut.resolve_cluster(clusters) == "marconi"
    monkeypatch.setattr(socket, "gethostname", lambda: "somewhere-else")
    assert ut.resolve_cluster(clusters) == "local"


def test_check_option_exists():
    assert ut.check_option_exists("vasp", ["vasp", "quantum_espresso"]) == 0
    assert ut.check_option_exists(True, [True, False]) == 0
    with pytest.raises(SystemExit):
        ut.check_option_exists("bad", ["good", "better"], name="code")


def test_get_structure(tmp_path):
    # Copy a minimal structure file into tmp_path
    src = Path(__file__).parent / "data" / "Si.cif"
    dst = tmp_path / "Si.cif"
    dst.write_text(src.read_text())

    s = ut.get_structure(str(dst))

    assert hasattr(s, "formula")
    assert hasattr(s, "lattice")
    assert hasattr(s, "symbols")
    assert hasattr(s, "positions")
    assert hasattr(s, "space_group")
    assert hasattr(s, "atoms")

    assert len(s.lattice) == 3
    assert len(s.lattice[0]) == 3
    assert len(s.positions) == len(s.symbols)


@pytest.fixture
def calculations(monkeypatch):
    definitions = {
        "bands": {
            "config": [{"name": "soc", "default": False}],
            "files": {"qe": ["bands.in"]},
        },
        "relax": {
            "flavors": {
                "fixed": {
                    "config": [{"name": "soc", "default": False}],
                    "files": {"qe": ["relax.in"]},
                },
                "variable": {
                    "config": [{"name": "soc", "default": True}],
                    "files": {"qe": ["relax.in"]},
                },
            },
        },
    }
    monkeypatch.setattr(
        ut.config, "load_config", lambda: ({"calculations": definitions}, None)
    )
    return definitions


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("bands.in", ("bands", None, "qe")), ("relax.in", ("relax", None, "qe"))],
)
def test_resolve_calc_current_dir(
    calculations, tmp_path, monkeypatch, filename, expected
):
    (tmp_path / filename).touch()
    monkeypatch.chdir(tmp_path)
    assert ut.resolve_calc_current_dir() == expected


def test_resolve_calc_current_dir_raises_if_empty(calculations, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Could not infer calculation kind/code"):
        ut.resolve_calc_current_dir()


def test_resolve_calc_current_dir_raises_if_ambiguous(
    calculations, tmp_path, monkeypatch
):
    calculations["other"] = {"files": {"qe": ["bands.in"]}}
    (tmp_path / "bands.in").touch()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Ambiguous calculation setup"):
        ut.resolve_calc_current_dir()


def test_get_config(calculations):
    assert ut.get_config("bands", "soc") == {"name": "soc", "default": False}
    assert ut.get_config("relax", "soc", "variable") == {"name": "soc", "default": True}
    assert ut.get_config("relax", "soc") == {"name": "soc", "default": False}


@pytest.mark.parametrize(
    ("kind", "name", "flavor", "message"),
    [
        ("missing", "soc", None, "No calculation kind:"),
        ("bands", "missing", None, "Configuration .* not found"),
        ("relax", "soc", "missing", "No config for calculation kind/flavor:"),
    ],
)
def test_get_config_raises(calculations, kind, name, flavor, message):
    with pytest.raises(KeyError, match=message):
        ut.get_config(kind, name, flavor)
