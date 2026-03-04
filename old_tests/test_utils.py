from pathlib import Path
import os

import pytest

from dftcaddie.config import calculations
import dftcaddie.utils as ut


@pytest.mark.parametrize(
    "kind,code",
    [(k, c) for k, cfg in calculations.items() for c in cfg.get("files", {}).keys()],
)
def test_resolve_calc_current_dir_detects_each_kind_code(
    tmp_path: Path, kind: str, code: str
):
    """
    For each (kind, code) declared in calculations[*]["files"], create a temp
    directory containing exactly the expected template filenames and ensure
    resolve_calc_current_dir() returns that pair.
    """
    expected_files = calculations[kind]["files"][code]

    for fname in expected_files:
        (tmp_path / fname).write_text("# dummy\n", encoding="utf-8")

    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        got_kind, got_code = ut.resolve_calc_current_dir()
    finally:
        os.chdir(old)

    assert (got_kind, got_code) == (kind, code)


def test_resolve_calc_current_dir_raises_if_empty(tmp_path: Path):
    """No files -> no match -> RuntimeError."""
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        with pytest.raises(RuntimeError, match="Could not infer calculation kind/code"):
            ut.resolve_calc_current_dir()
    finally:
        os.chdir(old)


@pytest.mark.parametrize("options", [["vasp", "quantum_espresso"], ["bands", "relax"]])
def test_resolve_user_input_full_match(options: list[str]):
    """Exact match should return the input."""
    assert ut.resolve_user_input(options[0], options) == options[0]


def test_resolve_user_input_partial_match():
    """Prefix match should return the first matching option."""
    options = ["quantum_espresso", "vasp"]
    assert ut.resolve_user_input("q", options) == "quantum_espresso"


def test_resolve_user_input_boolean_options():
    """Boolean options should accept yes/no and return bool."""
    assert ut.resolve_user_input("yes", [True, False]) is True
    assert ut.resolve_user_input("no", [True, False]) is False


def test_format_options_basic_and_brackets():
    options = ["bands", "relax"]
    assert ut.format_options(options) == "bands, relax"
    assert ut.format_options(options, brackets=True) == "[B]ands, [R]elax"


def test_format_options_boolean():
    assert ut.format_options([True, False]) == "yes, no"
    assert ut.format_options([True, False], brackets=True) == "[Y]es, [N]o"


def test_check_option_exists_ok():
    ut.check_option_exists("vasp", ["vasp", "quantum_espresso"])


def test_check_option_exists_raises_system_exit():
    with pytest.raises(SystemExit):
        ut.check_option_exists("bad", ["good", "better"], name="code")


def test_get_config_happy_path_if_present():
    """
    If a kind defines config entries, get_config should return a dict with the
    requested name. We pick the first available config entry dynamically.
    """
    for kind, cfg in calculations.items():
        entries = cfg.get("config") or []
        if entries:
            name = entries[0]["name"]
            got = ut.get_config(kind, name)
            assert isinstance(got, dict)
            assert got.get("name") == name
            return
    pytest.skip("No calculations define 'config' entries to test get_config().")


def test_get_config_raises_for_unknown_kind():
    with pytest.raises(KeyError, match="Unknown calculation kind"):
        ut.get_config("___not_a_kind___", "soc")


def test_get_config_raises_for_unknown_name():
    kind = next(iter(calculations.keys()))
    with pytest.raises(KeyError, match="Configuration .* not found"):
        ut.get_config(kind, "___not_a_config___")


def test_bool_maps_are_inverse():
    """Sanity: yes/no maps are consistent."""
    assert ut.affirmation2bool["yes"] is True
    assert ut.affirmation2bool["no"] is False
    assert ut.bool2affirmation[True] == "yes"
    assert ut.bool2affirmation[False] == "no"


def test_resolve_cluster_matches_hostname(monkeypatch: pytest.MonkeyPatch):
    clusters = {
        "local": {"hostname": ""},  # special default in your implementation
        "lumi": {"hostname": "lumi"},
        "marconi": {"hostname": "login.marconi"},
    }

    def fake_gethostname() -> str:
        return "login.marconi123"

    # resolve_cluster imports socket *inside* the function, so patch socket.gethostname
    import socket

    monkeypatch.setattr(socket, "gethostname", fake_gethostname)

    assert ut.resolve_cluster(clusters) == "marconi"


def test_resolve_cluster_returns_local_when_no_match(monkeypatch: pytest.MonkeyPatch):
    clusters = {
        "local": {"hostname": ""},
        "lumi": {"hostname": "lumi"},
    }

    import socket

    monkeypatch.setattr(socket, "gethostname", lambda: "somewhere-else")

    assert ut.resolve_cluster(clusters) == "local"


def test_get_structure_basic_contract(tmp_path):
    from dftcaddie.utils import get_structure

    # Copy a minimal structure file into tmp_path
    src = Path(__file__).parent / "data" / "Si.cif"
    dst = tmp_path / "Si.cif"
    dst.write_text(src.read_text())

    s = get_structure(str(dst))

    assert hasattr(s, "formula")
    assert hasattr(s, "lattice")
    assert hasattr(s, "symbols")
    assert hasattr(s, "positions")
    assert hasattr(s, "space_group")

    assert len(s.lattice) == 3
    assert len(s.lattice[0]) == 3
    assert len(s.positions) == len(s.symbols)
