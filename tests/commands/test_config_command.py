from types import SimpleNamespace
from pathlib import Path

import pytest

from dftcaddie.commands import config as config_command


def test_init_command_copies_default_resources_to_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config_command.Path, "home", lambda: tmp_path)

    assert config_command.run(SimpleNamespace(config_action="init", force=False)) == 0

    user_config = tmp_path / ".config" / "dftcaddie"
    assert (user_config / "config.yaml").is_file()
    assert (user_config / "templates").is_dir()
    assert (user_config / "sbatch_headers").is_dir()
    assert (user_config / "kpaths").is_dir()


@pytest.mark.parametrize("force", [False, True])
def test_init_existing_resources(parse_args, isolated_command_environment, force):
    config_command.run(parse_args("config", "init"))
    root = Path.home() / ".config" / "dftcaddie"
    paths = [
        "config.yaml",
        "templates/quantum_espresso/master.sh",
        "sbatch_headers/local.default",
        "kpaths/quantum_espresso/SG227",
    ]
    for relative in paths:
        (root / relative).write_text("custom content\n")
    config_command.run(parse_args("config", "init", *(["--force"] if force else [])))
    for relative in paths:
        expected = (
            (isolated_command_environment / relative).read_bytes()
            if force
            else b"custom content\n"
        )
        assert (root / relative).read_bytes() == expected


def test_init_copies_exact_resource_contents(parse_args, isolated_command_environment):
    config_command.run(parse_args("config", "init"))
    destination = Path.home() / ".config" / "dftcaddie"
    for entry in ["config.yaml", "templates", "sbatch_headers", "kpaths"]:
        source = isolated_command_environment / entry
        files = [source] if source.is_file() else source.rglob("*")
        for path in files:
            if path.is_file():
                assert (
                    destination / path.relative_to(isolated_command_environment)
                ).read_bytes() == path.read_bytes()
