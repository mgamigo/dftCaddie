import os
import pytest

from dftcaddie import config


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("PSLIBRARY", raising=False)
    for resolver in (
        config.load_config,
        config.resolve_pseudo_library,
    ):
        resolver.cache_clear()
    yield
    for resolver in (
        config.load_config,
        config.resolve_pseudo_library,
    ):
        resolver.cache_clear()


def test_load_config_uses_bundled_defaults(tmp_path, monkeypatch):
    from pathlib import Path
    import yaml

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    data, source = config.load_config()
    bundled = Path(config.__file__).parent / "resources"
    assert source == bundled
    with (bundled / "config.yaml").open() as stream:
        assert data == yaml.safe_load(stream)


def test_load_config_prefers_user_config(tmp_path, monkeypatch):
    from pathlib import Path

    user_dir = tmp_path / ".config" / "dftcaddie"
    user_dir.mkdir(parents=True)
    (user_dir / "config.yaml").write_text("default_kppra: 42\n")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert config.load_config() == ({"default_kppra": 42}, user_dir)


def test_load_config_can_force_bundled_defaults(tmp_path, monkeypatch):
    from pathlib import Path
    import yaml

    user_dir = tmp_path / ".config" / "dftcaddie"
    user_dir.mkdir(parents=True)
    (user_dir / "config.yaml").write_text("default_kppra: 42\n")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    data, source = config.load_config(default_config=True)

    bundled = Path(config.__file__).parent / "resources"
    assert source == bundled
    with (bundled / "config.yaml").open() as stream:
        assert data == yaml.safe_load(stream)


def test_private_config_paths_use_user_config_when_present(tmp_path):
    source = tmp_path / ".config" / "dftcaddie"
    source.mkdir(parents=True)
    path = source / "config.yaml"
    path.write_text("default_kppra: 42\n")
    assert config._config_paths() == (path, source)
    assert config.load_config() == ({"default_kppra": 42}, source)


@pytest.mark.parametrize("contents", ["invalid: [", "- not\n- a mapping\n"])
def test_invalid_yaml_does_not_break_imports_or_help(tmp_path, monkeypatch, contents):
    import subprocess
    import sys

    user_dir = tmp_path / ".config" / "dftcaddie"
    user_dir.mkdir(parents=True)
    path = user_dir / "config.yaml"
    path.write_text(contents)
    script = (
        "from dftcaddie import config, utils, file_management; "
        "assert config.load_config.cache_info().currsize == 0"
    )
    env = dict(os.environ, HOME=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    for args, expected in [
        (["--help"], 0),
        (["set", "system", "--help"], 0),
        (["config", "check"], 1),
    ]:
        result = subprocess.run(
            [sys.executable, "-m", "dftcaddie.cli", *args],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        assert "Traceback" not in result.stderr


@pytest.mark.parametrize("path", ["relative/library", "~/library"])
def test_library_resolution_is_simple_and_code_independent(tmp_path, monkeypatch, path):
    from pathlib import Path

    data = {
        "pseudopotentials": {
            "libraries": {
                "custom": {
                    "path": path,
                    "format": "upf",
                    "pattern": "{element}.*",
                    "supported_codes": ["new_code"],
                }
            }
        },
        "suggested_pseudos": [{"libraries": ["custom"], "elements": {"Si": "Si.v2*"}}],
    }
    # No directory needs to exist; config check owns that validation.
    with monkeypatch.context() as patch:
        patch.setattr(config, "load_config", lambda: (data, tmp_path))
        library = config.resolve_pseudo_library("custom")
        assert library["path"] == (
            tmp_path / "library" if path.startswith("~") else tmp_path / path
        )
        assert library["suggestions"] == {"Si": "Si.v2*"}
        library["suggestions"]["Si"] = "changed"
        library["supported_codes"].append("another")
        assert data["suggested_pseudos"][0]["elements"]["Si"] == "Si.v2*"
        assert data["pseudopotentials"]["libraries"]["custom"]["supported_codes"] == [
            "new_code"
        ]


def test_config_and_library_cache_are_cleared_together(tmp_path, pseudo_settings):
    import yaml

    user_dir = tmp_path / ".config/dftcaddie"
    user_dir.mkdir(parents=True)
    path = user_dir / "config.yaml"
    path.write_text(yaml.safe_dump(pseudo_settings))
    first = config.resolve_pseudo_library("scalar")
    pseudo_settings["pseudopotentials"]["libraries"]["scalar"]["path"] = "new-root"
    path.write_text(yaml.safe_dump(pseudo_settings))
    assert config.resolve_pseudo_library("scalar") is first
    config.clear_config_cache()
    assert config.resolve_pseudo_library("scalar")["path"] == user_dir / "new-root"
