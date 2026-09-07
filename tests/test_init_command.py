from types import SimpleNamespace

from dftcaddie.commands import init


def test_init_command_copies_default_resources_to_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(init.Path, "home", lambda: tmp_path)

    assert init.run(SimpleNamespace(force=False)) == 0

    user_config = tmp_path / ".config" / "dftcaddie"
    assert (user_config / "config.yaml").is_file()
    assert (user_config / "templates").is_dir()
    assert (user_config / "sbatch_headers").is_dir()
