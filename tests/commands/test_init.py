from types import SimpleNamespace
from pathlib import Path

import pytest

from dftcaddie.commands import init


def test_init_command_copies_default_resources_to_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(init.Path, "home", lambda: tmp_path)

    assert init.run(SimpleNamespace(force=False)) == 0

    user_config = tmp_path / ".config" / "dftcaddie"
    assert (user_config / "config.yaml").is_file()
    assert (user_config / "templates").is_dir()
    assert (user_config / "sbatch_headers").is_dir()


@pytest.mark.parametrize("force", [False, True])
def test_init_existing_resources(parse_args, isolated_command_environment, force):
    init.run(parse_args("init"))
    root = Path.home() / ".config" / "dftcaddie"
    paths = [
        "config.yaml",
        "templates/quantum_espresso/master.sh",
        "sbatch_headers/local.default",
    ]
    for relative in paths:
        (root / relative).write_text("custom content\n")
    init.run(parse_args("init", *(["--force"] if force else [])))
    for relative in paths:
        expected = (
            (isolated_command_environment / relative).read_bytes()
            if force
            else b"custom content\n"
        )
        assert (root / relative).read_bytes() == expected


def test_init_copies_exact_resource_contents(parse_args, isolated_command_environment):
    init.run(parse_args("init"))
    destination = Path.home() / ".config" / "dftcaddie"
    for entry in ["config.yaml", "templates", "sbatch_headers"]:
        source = isolated_command_environment / entry
        files = [source] if source.is_file() else source.rglob("*")
        for path in files:
            if path.is_file():
                assert (
                    destination / path.relative_to(isolated_command_environment)
                ).read_bytes() == path.read_bytes()
