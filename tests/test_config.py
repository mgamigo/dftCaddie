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

    monkeypatch.setitem(config.CONFIG, key, str(library))
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
    monkeypatch.delitem(config.CONFIG, key, raising=False)
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
    monkeypatch.setitem(config.CONFIG, key, str(library))
    monkeypatch.delenv("PSLIBRARY", raising=False)
    resolver.cache_clear()

    try:
        with pytest.raises(RuntimeError, match=re.escape(f"{message} '{library}'")):
            resolver()
    finally:
        resolver.cache_clear()


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.setattr(config, "CONFIG", {})
    monkeypatch.delenv("PSLIBRARY", raising=False)
    for resolver in (
        config._load_config,
        config.resolve_pslibrary,
        config.resolve_potcar_library,
    ):
        resolver.cache_clear()
    yield
    for resolver in (
        config._load_config,
        config.resolve_pslibrary,
        config.resolve_potcar_library,
    ):
        resolver.cache_clear()


def test_load_config_uses_bundled_defaults(tmp_path, monkeypatch):
    from pathlib import Path
    import yaml

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    data, source = config._load_config()
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
    assert config._load_config() == ({"default_kppra": 42}, user_dir)


def test_pslibrary_environment_takes_precedence(tmp_path, monkeypatch):
    library = tmp_path / "environment-library"
    library.mkdir()
    monkeypatch.setenv("PSLIBRARY", str(library))
    monkeypatch.setitem(config.CONFIG, "qe_pslibrary", str(tmp_path / "missing"))
    assert config.resolve_pslibrary() == library


def test_pslibrary_invalid_environment_does_not_fall_back(tmp_path, monkeypatch):
    library = tmp_path / "missing"
    monkeypatch.setenv("PSLIBRARY", str(library))
    monkeypatch.setitem(config.CONFIG, "qe_pslibrary", str(tmp_path))
    with pytest.raises(RuntimeError) as error:
        config.resolve_pslibrary()
    assert str(error.value) == (
        f"$PSLIBRARY is set but directory does not exist: '{library}'"
    )
