from pathlib import Path

import pytest

import dftcaddie.utils as ut


def test_bool_maps():
    """Sanity: yes/no maps are consistent."""
    assert ut.affirmation2bool["yes"] is True
    assert ut.affirmation2bool["no"] is False
    assert ut.bool2affirmation[True] == "yes"
    assert ut.bool2affirmation[False] == "no"


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


def test_format_options():
    options = ["bands", "relax"]
    assert ut.format_options(options) == "bands, relax"
    assert ut.format_options(options, brackets=True) == "[B]ands, [R]elax"
    assert ut.format_options(options, numbers=True) == "[1] Bands, [2] Relax"
    options = [True, False]
    assert ut.format_options(options) == "yes, no"
    assert ut.format_options(options, brackets=True) == "[Y]es, [N]o"
    assert ut.format_options(options, numbers=True) == "[1] Yes, [2] No"


@pytest.mark.parametrize("options", [["vasp", "quantum_espresso"], ["bands", "relax"]])
def test_resolve_user_input_full_match(options: list[str]):
    # Exact match should return the input.
    assert ut.resolve_user_input(options[0], options) == options[0]
    # Test numbers as way to resolve input
    for i, opt in enumerate(options):
        assert ut.resolve_user_input(i + 1, options) == opt
    # Prefix match should return the first matching option.
    for opt in options:
        partial_input = opt[0]
        assert ut.resolve_user_input(partial_input, options) == opt
    # Boolean options should accept yes/no and return bool.
    assert ut.resolve_user_input("yes", [True, False]) is True
    assert ut.resolve_user_input("no", [True, False]) is False


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
    monkeypatch.setattr(ut, "calculations", definitions)
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
