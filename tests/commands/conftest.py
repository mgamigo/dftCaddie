from pathlib import Path
import socket

import pytest
import yaml

from dftcaddie import config, file_management as fm, utils
from dftcaddie.cli import _build_parser
from dftcaddie.commands import setup


@pytest.fixture(autouse=True)
def isolated_command_environment(tmp_path, monkeypatch):
    resources = Path(__file__).resolve().parents[2] / "dftcaddie" / "resources"
    with (resources / "config.yaml").open() as stream:
        data = yaml.safe_load(stream)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(socket, "gethostname", lambda: "test-host")
    monkeypatch.setattr(config, "CONFIG", data)
    monkeypatch.setattr(config, "SOURCE_DIR", resources)
    monkeypatch.setattr(fm, "SOURCE_DIR", resources)
    for name in ("calculations", "clusters", "mpi_executables"):
        monkeypatch.setattr(config, name, data[name])
        monkeypatch.setattr(fm, name, data[name])
    monkeypatch.setattr(utils, "calculations", data["calculations"])
    monkeypatch.setattr(setup, "default_kppra", data["default_kppra"])
    monkeypatch.setattr(config, "default_cutoff_ratio", data["default_cutoff_ratio"])
    monkeypatch.delenv("PSLIBRARY", raising=False)
    for resolver in (config.resolve_pslibrary, config.resolve_potcar_library):
        resolver.cache_clear()

    def unexpected_input(prompt):
        pytest.fail(f"Unexpected interactive prompt: {prompt}")

    monkeypatch.setattr("builtins.input", unexpected_input)
    yield resources
    for resolver in (config.resolve_pslibrary, config.resolve_potcar_library):
        resolver.cache_clear()


@pytest.fixture
def parse_args():
    return lambda *args: _build_parser().parse_args(list(args))
