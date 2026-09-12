import os
import re
import pytest

from dftcaddie import config


@pytest.mark.parametrize(
    ("key", "resolver"),
    [
        ("qe_pslibrary", config.resolve_pslibrary),
        ("vasp_pseudopotentials", config.resolve_potcar_library),
    ],
)
def test_pseudo_library_configured(tmp_path, monkeypatch, key, resolver):
    library = tmp_path / "pseudo-library"
    library.mkdir()

    monkeypatch.setitem(config.load_config()[0], key, str(library))
    monkeypatch.delenv("PSLIBRARY", raising=False)
    resolver.cache_clear()

    try:
        assert resolver() == library
    finally:
        resolver.cache_clear()


@pytest.mark.parametrize(
    ("key", "resolver", "missing_message"),
    [
        (
            "qe_pslibrary",
            config.resolve_pslibrary,
            "QE PSLibrary not defined. Set the $PSLIBRARY environment variable or "
            "define 'qe_pslibrary' in config.yaml.",
        ),
        (
            "vasp_pseudopotentials",
            config.resolve_potcar_library,
            "VASP POTCAR library not defined. Set 'vasp_pseudopotentials' in "
            "config.yaml.",
        ),
    ],
)
def test_pseudo_library_missing(monkeypatch, key, resolver, missing_message):
    monkeypatch.delitem(config.load_config()[0], key, raising=False)
    monkeypatch.delenv("PSLIBRARY", raising=False)
    resolver.cache_clear()

    try:
        with pytest.raises(RuntimeError, match=re.escape(missing_message)):
            resolver()
    finally:
        resolver.cache_clear()


@pytest.mark.parametrize(
    ("key", "resolver", "message"),
    [
        (
            "qe_pslibrary",
            config.resolve_pslibrary,
            "QE PSLibrary not found at",
        ),
        (
            "vasp_pseudopotentials",
            config.resolve_potcar_library,
            "VASP POTCAR library not found at",
        ),
    ],
)
def test_pseudo_library_path_missing(tmp_path, monkeypatch, key, resolver, message):
    library = tmp_path / "missing-pseudo-library"
    monkeypatch.setitem(config.load_config()[0], key, str(library))
    monkeypatch.delenv("PSLIBRARY", raising=False)
    resolver.cache_clear()

    try:
        with pytest.raises(RuntimeError, match=re.escape(f"{message} '{library}'")):
            resolver()
    finally:
        resolver.cache_clear()


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("PSLIBRARY", raising=False)
    for resolver in (
        config.load_config,
        config.resolve_pslibrary,
        config.resolve_potcar_library,
    ):
        resolver.cache_clear()
    yield
    for resolver in (
        config.load_config,
        config.resolve_pslibrary,
        config.resolve_potcar_library,
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


def test_pslibrary_environment_takes_precedence(tmp_path, monkeypatch):
    library = tmp_path / "environment-library"
    library.mkdir()
    monkeypatch.setenv("PSLIBRARY", str(library))
    monkeypatch.setitem(
        config.load_config()[0], "qe_pslibrary", str(tmp_path / "missing")
    )
    assert config.resolve_pslibrary() == library


def test_pslibrary_invalid_environment_does_not_fall_back(tmp_path, monkeypatch):
    library = tmp_path / "missing"
    monkeypatch.setenv("PSLIBRARY", str(library))
    monkeypatch.setitem(config.load_config()[0], "qe_pslibrary", str(tmp_path))
    with pytest.raises(RuntimeError) as error:
        config.resolve_pslibrary()
    assert str(error.value) == (
        f"$PSLIBRARY is set but directory does not exist: '{library}'"
    )


def test_config_is_cached_until_explicitly_cleared(tmp_path, monkeypatch):
    import yaml

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    user_dir = tmp_path / ".config" / "dftcaddie"
    user_dir.mkdir(parents=True)
    path = user_dir / "config.yaml"
    path.write_text(yaml.safe_dump({"qe_pslibrary": str(first)}))
    initial = config.load_config()
    assert config.resolve_pslibrary() == first
    path.write_text(yaml.safe_dump({"qe_pslibrary": str(second)}))
    assert config.load_config() is initial
    assert config.resolve_pslibrary() == first
    config.clear_config_cache()
    assert config.load_config()[0]["qe_pslibrary"] == str(second)
    assert config.resolve_pslibrary() == second


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
