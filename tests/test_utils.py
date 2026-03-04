from pathlib import Path
import os

import pytest

from dftcaddie.config import calculations
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


CASES = []
for kind, kind_dict in calculations.items():
    if "flavors" in kind_dict.keys():
        for flavor, flavor_dict in kind_dict["flavors"].items():
            for code, files in flavor_dict["files"].items():
                CASES.append([kind, flavor, code, files])
    else:
        flavor = None
        for code, files in kind_dict["files"].items():
            CASES.append([kind, flavor, code, files])


@pytest.mark.parametrize("kind,flavor,code,files", CASES)
def test_resolve_calc_current_dir(
    kind, flavor, code, files, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(os, "listdir", lambda x: [os.path.basename(f) for f in files])
    monkeypatch.setattr(os.path, "isfile", lambda x: True)
    res_kind, res_flavor, res_code = ut.resolve_calc_current_dir()
    assert res_kind == kind
    assert res_code == code


def test_resolve_calc_current_dir_raises_if_empty(tmp_path: Path):
    """No files -> no match -> RuntimeError."""
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        with pytest.raises(RuntimeError, match="Could not infer calculation kind/code"):
            ut.resolve_calc_current_dir()
    finally:
        os.chdir(old)


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


@pytest.mark.parametrize("kind,flavor,code,files", CASES)
def test_get_config_for_all_cases(
    kind,
    flavor,
    code,
    files,
):
    """
    If a kind defines config entries, get_config should return a dict with the
    requested name.
    """
    if flavor is None:
        config = calculations[kind]["config"]
    else:
        config = calculations[kind]["flavors"][flavor]["config"]
    for cfg in config:
        answer = ut.get_config(kind=kind, config_name=cfg["name"], flavor=flavor)
        assert answer == cfg
        # Retrieve even when flavor is not resolved
        answer = ut.get_config(kind=kind, config_name=cfg["name"])
        assert isinstance(answer, dict)
        assert answer.get("name") == cfg.get("name")


def test_get_config_raises_for_unknown_kind():
    with pytest.raises(KeyError, match="No calculation kind:"):
        ut.get_config("___not_a_kind___", "soc")


def test_get_config_raises_for_unknown_name():
    kind = next(iter(calculations.keys()))
    with pytest.raises(KeyError, match="Configuration .* not found"):
        ut.get_config(kind, "___not_a_config___")
